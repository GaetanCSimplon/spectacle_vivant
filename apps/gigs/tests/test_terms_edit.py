"""Quick edit of the payment terms of the contract from the card in "Mes dates"."""

import datetime

import pytest
from django.urls import reverse

from apps.documents.services import generate_contract_pdf, mark_contract_signed
from apps.finance.tests.helpers import TENANT_FIELDS, make_gig
from apps.tenants.factories import MembershipFactory, TenantFactory

from .. import services
from ..factories import GigFactory
from ..models import Gig

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
    return reverse("gigs:terms", args=[gig.pk])


def _signed_gig(tenant):
    gig = make_gig(tenant=tenant, gig_fields={"status": Gig.Status.CONFIRMED})
    generate_contract_pdf(gig)
    mark_contract_signed(gig)
    gig.refresh_from_db()
    return gig


def test_terms_page_requires_login(client):
    response = client.get(_url(GigFactory()))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_the_list_shows_the_terms_and_a_pencil(client, tenant):
    gig = GigFactory(
        tenant=tenant,
        deposit_due_on=datetime.date(2026, 11, 15),
        payment_method=Gig.PaymentMethod.TRANSFER,
    )

    content = client.get(reverse("gigs:list")).content.decode()

    assert f'hx-get="{_url(gig)}"' in content
    assert "15/11/2026" in content and "Virement" in content
    assert "Solde" in content and "à définir" in content


def test_a_cancelled_gig_has_no_terms_block(client, tenant):
    gig = GigFactory(tenant=tenant, status=Gig.Status.CANCELLED)

    content = client.get(reverse("gigs:list")).content.decode()

    assert f'hx-get="{_url(gig)}"' not in content


def test_a_signed_contract_locks_the_terms_in_the_list(client, tenant):
    gig = _signed_gig(tenant)

    content = client.get(reverse("gigs:list")).content.decode()

    assert f'hx-get="{_url(gig)}"' not in content
    assert "Verrouillé" in content


def test_htmx_get_returns_the_form_only(client, tenant):
    gig = GigFactory(tenant=tenant)

    response = client.get(_url(gig), **HTMX)

    content = response.content.decode()
    assert response.status_code == 200
    for field in ("deposit_due_on", "balance_due_on", "payment_method"):
        assert f'name="{field}"' in content
    assert "<html" not in content


def test_htmx_post_saves_and_returns_the_display(client, tenant):
    gig = GigFactory(tenant=tenant)

    response = client.post(
        _url(gig),
        {
            "deposit_due_on": "2026-11-15",
            "balance_due_on": "2027-01-10",
            "payment_method": "cheque",
        },
        **HTMX,
    )

    gig.refresh_from_db()
    content = response.content.decode()
    assert response.status_code == 200
    assert gig.deposit_due_on == datetime.date(2026, 11, 15)
    assert gig.balance_due_on == datetime.date(2027, 1, 10)
    assert gig.payment_method == Gig.PaymentMethod.CHEQUE
    assert "10/01/2027" in content and "Chèque" in content and "Enregistré" in content
    assert 'name="payment_method"' not in content


def test_post_can_empty_the_terms(client, tenant):
    gig = GigFactory(
        tenant=tenant,
        deposit_due_on=datetime.date(2026, 11, 15),
        payment_method=Gig.PaymentMethod.TRANSFER,
    )

    client.post(
        _url(gig), {"deposit_due_on": "", "balance_due_on": "", "payment_method": ""}, **HTMX
    )

    gig.refresh_from_db()
    assert (gig.deposit_due_on, gig.balance_due_on, gig.payment_method) == (None, None, "")


@pytest.mark.parametrize(
    "data",
    [
        {"deposit_due_on": "pas une date"},
        {"balance_due_on": "31/02/2027"},
        {"payment_method": "bitcoin"},
    ],
)
def test_a_bad_value_shows_the_error_and_changes_nothing(client, tenant, data):
    gig = GigFactory(tenant=tenant, payment_method=Gig.PaymentMethod.TRANSFER)

    response = client.post(_url(gig), data, **HTMX)

    gig.refresh_from_db()
    assert "errorlist" in response.content.decode()
    assert gig.payment_method == Gig.PaymentMethod.TRANSFER
    assert gig.deposit_due_on is None and gig.balance_due_on is None


def test_a_signed_contract_refuses_the_post(client, tenant):
    gig = _signed_gig(tenant)

    response = client.post(_url(gig), {"payment_method": "cheque"}, **HTMX)

    gig.refresh_from_db()
    assert "contrat est signé" in response.content.decode()
    assert gig.payment_method == ""


def test_service_refuses_a_signed_contract(tenant):
    gig = _signed_gig(tenant)

    with pytest.raises(services.CannotChangeTerms):
        services.update_terms(gig, None, None, "cheque")


def test_page_without_javascript_saves_and_goes_back_to_the_date(client, tenant):
    gig = GigFactory(tenant=tenant)

    page = client.get(_url(gig))
    response = client.post(
        _url(gig), {"deposit_due_on": "2026-12-01", "payment_method": "transfer"}
    )

    gig.refresh_from_db()
    assert 'name="deposit_due_on"' in page.content.decode()
    assert response.status_code == 302
    assert response.url == reverse("gigs:detail", args=[gig.pk])
    assert gig.deposit_due_on == datetime.date(2026, 12, 1)


def test_page_without_javascript_shows_the_error(client, tenant):
    gig = GigFactory(tenant=tenant)

    response = client.post(_url(gig), {"deposit_due_on": "oups"})

    assert response.status_code == 200
    assert "errorlist" in response.content.decode()


def test_the_gig_page_shows_the_terms_and_a_link(client, tenant):
    gig = GigFactory(tenant=tenant, deposit_due_on=datetime.date(2026, 11, 15))

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert "15/11/2026" in content
    assert _url(gig) in content


def test_the_terms_edit_leaves_the_price_alone(client, tenant):
    gig = GigFactory(tenant=tenant, price="777.00")

    client.post(_url(gig), {"payment_method": "transfer"}, **HTMX)

    gig.refresh_from_db()
    assert str(gig.price) == "777.00" and not gig.price_changes.exists()


def test_another_tenants_gig_is_a_404_and_stays_unchanged(client, tenant):
    other = GigFactory(tenant=TenantFactory())

    assert client.get(_url(other)).status_code == 404
    assert client.get(_url(other), **HTMX).status_code == 404
    assert client.post(_url(other), {"payment_method": "cheque"}, **HTMX).status_code == 404

    other.refresh_from_db()
    assert other.payment_method == ""


def test_the_list_never_shows_another_tenants_terms_buttons(client, tenant):
    other = GigFactory(tenant=TenantFactory())

    content = client.get(reverse("gigs:list")).content.decode()

    assert f'hx-get="{_url(other)}"' not in content
