import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.documents.models import Invoice
from apps.finance import services as finance_services
from apps.finance.factories import ExpenseFactory
from apps.finance.tests.helpers import TENANT_FIELDS, issued_invoice, make_gig
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import TenantFactory

from ..factories import MembershipFactory

pytestmark = pytest.mark.django_db

URL = reverse("tenants:profile")


def test_bord_requires_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


@pytest.mark.parametrize("role", ["owner", "member"])
def test_bord_links_to_the_settings_and_the_team(client, role):
    client.force_login(MembershipFactory(role=role).user)

    response = client.get(URL)

    content = response.content.decode()
    assert response.status_code == 200
    assert reverse("tenants:settings") in content
    assert reverse("tenants:person-list") in content
    assert reverse("export") in content


def test_bord_sends_a_user_without_a_tenant_to_onboarding(client, django_user_model):
    client.force_login(django_user_model.objects.create_user(email="seul@example.org"))

    response = client.get(URL)

    assert response.status_code == 302
    assert response.url == reverse("tenants-onboarding")


def test_old_profile_wording_is_gone(client):
    client.force_login(MembershipFactory().user)

    for url in (URL, reverse("tenants:settings"), reverse("tenants:person-list")):
        assert "Ma structure" not in client.get(url).content.decode()


# --- the page itself -------------------------------------------------------


TODAY = timezone.localdate()
HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _membership(client, role="owner"):
    membership = MembershipFactory(
        role=role, **{f"tenant__{key}": value for key, value in TENANT_FIELDS.items()}
    )
    client.force_login(membership.user)
    return membership


def _gig(tenant, days=10, price="1000.00", status=Gig.Status.SIGNED, **fields):
    return make_gig(
        tenant=tenant,
        price=price,
        gig_fields={"status": status, "date": TODAY + datetime.timedelta(days=days), **fields},
    )


def _status_url(gig):
    return reverse("tenants:bord-status", args=[gig.pk])


def test_the_page_shows_the_blocks_to_every_member(client):
    membership = _membership(client, role="member")
    gig = _gig(membership.tenant, price="1500.00")
    ExpenseFactory(gig=gig, amount="200.00", date=TODAY)

    content = client.get(URL).content.decode()

    for block in (
        "Dates",
        "Recette",
        "Dépenses",
        "Solde",
        "Reste à encaisser",
        "À traiter maintenant",
    ):
        assert block in content
    assert "Prochaines dates" in content and "Opérations récentes" in content
    assert gig.show.title in content
    assert "1\xa0500 €" in content and "200 €" in content


def test_the_default_period_is_the_year_and_the_default_figure_is_the_planned_one(client):
    membership = _membership(client)
    _gig(membership.tenant, price="800.00")

    context = client.get(URL).context

    assert context["filters"].start == datetime.date(TODAY.year, 1, 1)
    assert context["filters"].figure == "planned"
    assert context["revenue"]["planned"] == 800 or context["dates"]["confirmed"] == 0


def test_nothing_to_report_is_said_with_care(client):
    _membership(client)

    content = client.get(URL).content.decode()

    assert "Rien à signaler sur les points contrôlés" in content
    assert "tout est à jour" not in content.lower()
    assert "Aucune date sur cette période" in content


def test_something_to_do_is_listed_with_its_reason(client):
    membership = _membership(client)
    _gig(membership.tenant, days=5)  # signed, no payment terms

    content = client.get(URL).content.decode()

    assert "Échéances de paiement à renseigner" in content
    assert "aucune échéance" in content
    assert "Renseigner les échéances" in content


def test_filters_narrow_the_page(client):
    membership = _membership(client)
    kept = _gig(membership.tenant, price="1000.00")
    other = _gig(membership.tenant, price="700.00")

    response = client.get(URL, {"period": "annee", "show": kept.show.pk, "figure": "planned"})

    context = response.context
    assert context["filters"].show == kept.show
    assert [row["gig"] for row in context["operations"]] == [kept]
    assert other.show.title not in response.content.decode().split("Opérations récentes")[1]


def test_a_custom_period_is_used_and_a_bad_one_falls_back_to_the_year(client):
    _membership(client)

    custom = client.get(URL, {"period": "perso", "start": "2026-03-01", "end": "2026-03-31"})
    reversed_dates = client.get(
        URL, {"period": "perso", "start": "2026-03-31", "end": "2026-03-01"}
    )
    garbage = client.get(URL, {"period": "perso", "start": "n'importe", "end": "quoi"})

    assert (custom.context["filters"].start, custom.context["filters"].end) == (
        datetime.date(2026, 3, 1),
        datetime.date(2026, 3, 31),
    )
    for response in (reversed_dates, garbage):
        assert response.status_code == 200
        assert response.context["filters"].start == datetime.date(TODAY.year, 1, 1)


def test_an_unknown_value_in_a_filter_is_ignored(client):
    _membership(client)

    response = client.get(
        URL, {"period": "siecle", "figure": "magic", "status": "??", "show": "999999"}
    )

    assert response.status_code == 200
    filters = response.context["filters"]
    assert filters.figure == "planned" and filters.status == "" and filters.show is None


def test_another_tenants_show_cannot_be_used_as_a_filter(client):
    _membership(client)
    foreign = GigFactory(tenant=TenantFactory())

    response = client.get(URL, {"show": foreign.show.pk})

    assert response.context["filters"].show is None


def test_htmx_returns_only_the_results(client):
    membership = _membership(client)
    _gig(membership.tenant)

    content = client.get(URL, {"period": "mois"}, **HTMX).content.decode()

    assert "<html" not in content and "Opérations récentes" in content
    assert 'name="period"' not in content


def test_the_figure_choice_changes_the_amounts_of_the_table(client):
    membership = _membership(client)
    gig = _gig(membership.tenant, price="1000.00")
    invoice = issued_invoice(gig)
    finance_services.record_payment(invoice, "250.00", TODAY, "transfer")

    rows = {
        figure: client.get(URL, {"figure": figure}).context["operations"][0]["amount"]
        for figure in ("planned", "invoiced", "received")
    }

    assert rows == {"planned": 1000, "invoiced": 1000, "received": 250}


def test_the_page_never_shows_another_tenants_data(client):
    _membership(client)
    foreign = _gig(TenantFactory(**TENANT_FIELDS), price="98765.00")
    ExpenseFactory(gig=foreign, amount="4321.00", date=TODAY)

    content = client.get(URL).content.decode()

    assert foreign.show.title not in content
    assert "98\xa0765" not in content and "4\xa0321" not in content


# --- cancel / restore from the table ---------------------------------------


def test_only_the_owner_sees_the_status_buttons(client):
    owner = _membership(client)
    _gig(owner.tenant)
    assert "Annuler la date" in client.get(URL).content.decode()

    member = MembershipFactory(role="member", tenant=owner.tenant)
    client.force_login(member.user)

    content = client.get(URL).content.decode()
    assert "Annuler la date" not in content and "Rétablir" not in content


def test_the_owner_cancels_then_restores_a_date(client):
    owner = _membership(client)
    gig = _gig(owner.tenant, status=Gig.Status.CONFIRMED)

    cancel = client.post(
        _status_url(gig), {"action": "cancel", "qs": "period=mois&figure=received"}
    )
    gig.refresh_from_db()
    assert gig.status == Gig.Status.CANCELLED
    assert cancel.status_code == 302
    assert cancel.url == f"{URL}?period=mois&figure=received"

    client.post(_status_url(gig), {"action": "reactivate"})
    gig.refresh_from_db()
    assert gig.status == Gig.Status.OPTION


def test_a_member_cannot_change_a_status_even_by_posting(client):
    owner = _membership(client)
    gig = _gig(owner.tenant, status=Gig.Status.CONFIRMED)
    client.force_login(MembershipFactory(role="member", tenant=owner.tenant).user)

    response = client.post(_status_url(gig), {"action": "cancel"})

    gig.refresh_from_db()
    assert response.status_code == 403
    assert gig.status == Gig.Status.CONFIRMED


def test_cancelling_a_date_with_an_open_invoice_warns(client):
    owner = _membership(client)
    gig = _gig(owner.tenant, status=Gig.Status.CONFIRMED)
    issued_invoice(gig)

    response = client.post(_status_url(gig), {"action": "cancel"}, follow=True)

    assert "créez un avoir" in response.content.decode()
    assert Invoice.objects.filter(gig=gig).exists()


def test_the_status_view_is_post_only_and_login_only(client):
    gig = GigFactory()
    assert client.post(_status_url(gig), {"action": "cancel"}).status_code == 302

    owner = _membership(client)
    own = _gig(owner.tenant)
    assert client.get(_status_url(own)).status_code == 405


def test_another_tenants_date_is_a_404(client):
    _membership(client)
    foreign = GigFactory(tenant=TenantFactory(), status=Gig.Status.CONFIRMED)

    response = client.post(_status_url(foreign), {"action": "cancel"})

    foreign.refresh_from_db()
    assert response.status_code == 404
    assert foreign.status == Gig.Status.CONFIRMED


def test_the_redirect_never_leaves_the_site(client):
    owner = _membership(client)
    gig = _gig(owner.tenant, status=Gig.Status.CONFIRMED)

    response = client.post(
        _status_url(gig), {"action": "cancel", "qs": "next=https://evil.example/&x=1"}
    )

    assert response.url.startswith(URL + "?")
    assert "evil.example" not in response.url.split("?")[0]


def test_the_page_draws_the_chart_with_a_text_alternative(client):
    membership = _membership(client)
    gig = _gig(membership.tenant, price="1200.00")
    ExpenseFactory(gig=gig, amount="300.00", date=TODAY)

    content = client.get(URL).content.decode()

    assert "Évolution mensuelle" in content
    assert "<svg" in content and 'role="img"' in content
    assert "<title" in content and "Voir les chiffres du graphique" in content
    assert "Dépenses par catégorie" in content and "width: 100%" in content


def test_the_page_says_so_when_there_is_nothing_to_draw(client):
    _membership(client)

    content = client.get(URL).content.decode()

    assert "Pas encore de chiffres sur cette période" in content
    assert "<svg" not in content.split("Évolution mensuelle")[1].split("Prochaines dates")[0]


def test_the_operations_come_as_a_table_and_as_phone_cards(client):
    membership = _membership(client)
    gig = _gig(membership.tenant, price="1200.00")
    issued_invoice(gig)

    content = client.get(URL).content.decode()
    operations = content.split('id="operations"')[1].split('id="depenses"')[0]

    table, cards = operations.split('<ul class="mt-3 divide-y divide-page-line md:hidden">')
    assert "hidden overflow-x-auto md:block" in table and "<table" in table
    assert "<table" not in cards
    # the same row, with its amount, status and documents, appears in both layouts
    for part in (table, cards):
        assert gig.show.title in part
        assert "1\xa0200 €" in part
        assert "En attente" in part
        assert "Facture" in part
        assert "Annuler la date" in part


def test_a_member_sees_no_button_in_either_layout(client):
    owner = _membership(client)
    _gig(owner.tenant)
    client.force_login(MembershipFactory(role="member", tenant=owner.tenant).user)

    content = client.get(URL).content.decode()

    assert "Annuler la date" not in content and "Rétablir" not in content


def test_the_chart_svg_numbers_use_a_dot_not_the_french_comma(client):
    """`width="20,5"` is not a valid SVG number: the bars vanished under the French locale."""
    import re

    membership = _membership(client)
    gig = _gig(membership.tenant, price="1234.00")
    ExpenseFactory(gig=gig, amount="321.00", date=TODAY)

    content = client.get(URL).content.decode()
    svg = content.split('role="img"')[1].split("</svg>")[0]

    assert "<rect" in svg
    assert not re.search(r'\b(x|y|x1|x2|y1|y2|width|height)="[^"]*,[^"]*"', svg)
    heights = [float(h) for h in re.findall(r'<rect[^>]*height="([0-9.]+)"', svg)]
    assert max(heights) > 0  # at least one bar is really drawn
