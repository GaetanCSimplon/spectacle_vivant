"""Quick edit of the price from the card in "Mes dates", and where the history shows."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.documents.services import generate_contract_pdf, mark_contract_signed
from apps.finance.tests.helpers import TENANT_FIELDS, issued_invoice, make_gig
from apps.tenants.factories import MembershipFactory, TenantFactory

from .. import services
from ..factories import GigFactory
from ..models import Gig, PriceChange

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def tenant(client):
    membership = MembershipFactory(
        **{f"tenant__{key}": value for key, value in TENANT_FIELDS.items()}
    )
    client.force_login(membership.user)
    return membership.tenant


def _url(gig):
    return reverse("gigs:price", args=[gig.pk])


def test_price_page_requires_login(client):
    gig = GigFactory()

    response = client.get(_url(gig))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_the_list_offers_a_pencil_next_to_the_price(client, tenant):
    gig = GigFactory(tenant=tenant, price="1200.50")

    content = client.get(reverse("gigs:list")).content.decode()

    assert "1\xa0200,50 € HT" in content
    assert f'hx-get="{_url(gig)}"' in content
    assert "Modifier le prix" in content


def test_the_list_says_when_the_price_is_locked(client, tenant):
    open_gig = GigFactory(tenant=tenant)
    cancelled = GigFactory(tenant=tenant, status=Gig.Status.CANCELLED)
    invoiced = make_gig(tenant=tenant)
    issued_invoice(invoiced)

    content = client.get(reverse("gigs:list")).content.decode()

    assert f'hx-get="{_url(open_gig)}"' in content
    assert f'hx-get="{_url(cancelled)}"' not in content
    assert f'hx-get="{_url(invoiced)}"' not in content
    assert content.count("Prix verrouillé") == 2


def test_the_other_pages_keep_their_cards_without_price_buttons(client, tenant):
    gig = GigFactory(tenant=tenant)

    content = client.get(reverse("catalog:show-detail", args=[gig.show.pk])).content.decode()

    assert reverse("gigs:detail", args=[gig.pk]) in content
    assert f'hx-get="{_url(gig)}"' not in content


def test_htmx_get_returns_the_form_only(client, tenant):
    gig = GigFactory(tenant=tenant)

    response = client.get(_url(gig), **HTMX)

    content = response.content.decode()
    assert response.status_code == 200
    assert 'name="price"' in content and 'name="note"' in content
    assert "<html" not in content


def test_cancel_button_returns_the_display(client, tenant):
    gig = GigFactory(tenant=tenant)

    content = client.get(_url(gig) + "?vue=affichage", **HTMX).content.decode()

    assert 'name="price"' not in content
    assert "Modifier le prix" in content


def test_htmx_post_saves_and_returns_the_display(client, tenant):
    gig = GigFactory(tenant=tenant, price="500.00")

    response = client.post(_url(gig), {"price": "650,00", "note": "négocié"}, **HTMX)

    gig.refresh_from_db()
    content = response.content.decode()
    assert response.status_code == 200
    assert gig.price == Decimal("650.00")
    assert "650 € HT" in content and "Enregistré" in content
    assert 'name="price"' not in content
    change = PriceChange.objects.get(gig=gig)
    assert (change.old_price, change.new_price, change.note) == (
        Decimal("500.00"),
        Decimal("650.00"),
        "négocié",
    )


@pytest.mark.parametrize("value", ["", "abc", "0", "-3", "10.999"])
def test_htmx_post_with_a_bad_price_shows_the_error_and_changes_nothing(client, tenant, value):
    gig = GigFactory(tenant=tenant, price="500.00")

    response = client.post(_url(gig), {"price": value}, **HTMX)

    gig.refresh_from_db()
    assert response.status_code == 200
    assert 'name="price"' in response.content.decode()
    assert "errorlist" in response.content.decode()
    assert gig.price == Decimal("500.00")
    assert not PriceChange.objects.exists()


def test_locked_gig_cannot_be_changed_by_a_post(client, tenant):
    gig = make_gig(tenant=tenant, gig_fields={"status": Gig.Status.CONFIRMED})
    generate_contract_pdf(gig)
    mark_contract_signed(gig)

    response = client.post(_url(gig), {"price": "1"}, **HTMX)

    gig.refresh_from_db()
    assert "contrat" in response.content.decode()
    assert gig.price == Decimal("1000.00")


def test_locked_gig_page_explains_why(client, tenant):
    gig = make_gig(tenant=tenant)
    issued_invoice(gig)

    content = client.get(_url(gig)).content.decode()

    assert "ne peut plus changer" in content
    assert "facture" in content
    assert 'name="price"' not in content


def test_page_without_javascript_saves_and_goes_back_to_the_date(client, tenant):
    gig = GigFactory(tenant=tenant, price="500.00")

    page = client.get(_url(gig))
    response = client.post(_url(gig), {"price": "800"})

    gig.refresh_from_db()
    assert 'name="price"' in page.content.decode()
    assert response.status_code == 302
    assert response.url == reverse("gigs:detail", args=[gig.pk])
    assert gig.price == Decimal("800.00")


def test_page_without_javascript_shows_the_error(client, tenant):
    gig = GigFactory(tenant=tenant, price="500.00")

    response = client.post(_url(gig), {"price": "oups"})

    assert response.status_code == 200
    assert "errorlist" in response.content.decode()


def test_the_history_shows_on_the_price_page_and_on_the_gig(client, tenant):
    gig = GigFactory(tenant=tenant, price="500.00")
    services.change_price(gig, "600", None, note="première offre")
    services.change_price(gig, "700", None)

    page = client.get(_url(gig)).content.decode()
    detail = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    for content in (page, detail):
        assert "500 € → <strong>600 € HT" in content
        assert "600 € → <strong>700 € HT" in content
    assert "première offre" in page


def test_the_show_page_lists_the_granted_prices(client, tenant):
    gig = GigFactory(tenant=tenant, price="1500.00")
    GigFactory(tenant=tenant, show=gig.show, price="900.00", promoter__name="Mairie de Sète")

    content = client.get(reverse("catalog:show-detail", args=[gig.show.pk])).content.decode()

    assert "Prix accordés" in content
    assert "1\xa0500 € HT" in content
    assert "Mairie de Sète" in content


def test_another_tenants_gig_is_a_404_and_stays_unchanged(client, tenant):
    other = GigFactory(tenant=TenantFactory(), price="500.00")

    assert client.get(_url(other)).status_code == 404
    assert client.get(_url(other), **HTMX).status_code == 404
    assert client.post(_url(other), {"price": "1"}, **HTMX).status_code == 404

    other.refresh_from_db()
    assert other.price == Decimal("500.00")
    assert not PriceChange.objects.exists()


def test_the_list_never_shows_another_tenants_price_buttons(client, tenant):
    other = GigFactory(tenant=TenantFactory())

    content = client.get(reverse("gigs:list")).content.decode()

    assert f'hx-get="{_url(other)}"' not in content
