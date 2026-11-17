import pytest
from django.urls import reverse

from apps.finance import exports as finance_exports
from apps.finance.factories import ExpenseFactory
from apps.finance.tests.helpers import issued_invoice, make_gig
from apps.gigs.factories import GigFactory
from apps.tenants import data_export
from apps.tenants.factories import MembershipFactory

from ..factories import ShowFactory
from ..models import Show

pytestmark = pytest.mark.django_db

PERIOD = ("2000-01-01", "2100-12-31")


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {"title": "Nuits d'été", "duration_minutes": "75", "default_price": "800.00"}
    data.update(overrides)
    return data


def _period():
    import datetime

    return datetime.date(2000, 1, 1), datetime.date(2100, 12, 31)


# --- the fields -------------------------------------------------------------------------


def test_the_new_show_fields_are_optional():
    show = ShowFactory()
    show.refresh_from_db()

    assert show.artists_count is None and show.technicians_count is None
    assert show.soundcheck_minutes is None and show.soundcheck_to_set_minutes is None
    assert show.analytic_code == ""


def test_the_user_fills_and_changes_them_on_the_show(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)
    url = reverse("catalog:show-update", args=[show.pk])
    data = _payload(
        artists_count="4",
        technicians_count="2",
        soundcheck_minutes="90",
        soundcheck_to_set_minutes="30",
        analytic_code="2026-TOUR-A",
    )

    assert client.post(url, data).status_code == 302
    show.refresh_from_db()
    assert (show.artists_count, show.technicians_count) == (4, 2)
    assert (show.soundcheck_minutes, show.soundcheck_to_set_minutes) == (90, 30)
    assert show.analytic_code == "2026-TOUR-A"

    client.post(url, {**data, "soundcheck_minutes": "60", "analytic_code": ""})
    show.refresh_from_db()
    assert show.soundcheck_minutes == 60 and show.analytic_code == ""


def test_the_show_can_be_created_with_them(client):
    tenant = _login(client)

    client.post(reverse("catalog:show-create"), _payload(analytic_code="X1", artists_count="3"))

    show = Show.objects.get(tenant=tenant)
    assert (show.analytic_code, show.artists_count) == ("X1", 3)


@pytest.mark.parametrize(
    "field,value",
    [
        ("artists_count", "-1"),
        ("technicians_count", "abc"),
        ("soundcheck_minutes", "-5"),
        ("soundcheck_to_set_minutes", "1.5"),
        ("analytic_code", "x" * 31),
    ],
)
def test_bad_values_are_refused(client, field, value):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)

    response = client.post(
        reverse("catalog:show-update", args=[show.pk]), _payload(**{field: value})
    )

    assert response.status_code == 200
    show.refresh_from_db()
    assert getattr(show, field) in (None, "")


def test_the_detail_page_shows_them_including_a_zero(client):
    tenant = _login(client)
    show = ShowFactory(
        tenant=tenant,
        artists_count=0,
        technicians_count=2,
        soundcheck_minutes=90,
        soundcheck_to_set_minutes=30,
        analytic_code="2026-TOUR-A",
    )

    page = client.get(reverse("catalog:show-detail", args=[show.pk])).content.decode()

    assert "Artistes : 0" in page
    assert "Techniciens : 2" in page
    assert "Balances (minimum) : 90 min" in page
    assert "Entre la fin des balances et le set (minimum) : 30 min" in page
    assert "Code analytique : 2026-TOUR-A" in page


def test_another_structure_cannot_change_the_show(client):
    _login(client)
    other = ShowFactory()

    response = client.post(
        reverse("catalog:show-update", args=[other.pk]), _payload(analytic_code="HACK")
    )

    assert response.status_code == 404
    other.refresh_from_db()
    assert other.analytic_code == ""


def test_the_complete_the_date_form_updates_the_soundcheck_times(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    client.post(
        reverse("documents:contract-complete", args=[gig.pk]),
        {"show-soundcheck_minutes": "75", "show-soundcheck_to_set_minutes": "20"},
    )

    gig.show.refresh_from_db()
    assert (gig.show.soundcheck_minutes, gig.show.soundcheck_to_set_minutes) == (75, 20)


# --- the exports ------------------------------------------------------------------------


def test_the_analytic_code_ends_every_finance_export():
    show = ShowFactory(analytic_code="2026-TOUR-A")
    gig = make_gig(gig_fields={"show": show})
    invoice = issued_invoice(gig)
    ExpenseFactory(gig=gig)
    from apps.finance.models import Payment

    Payment.objects.create(
        tenant=gig.tenant,
        invoice=invoice,
        amount="10.00",
        date=invoice.issue_date,
        method="transfer",
    )
    start, end = _period()

    for builder in (
        finance_exports.invoices_rows,
        finance_exports.payments_rows,
        finance_exports.expenses_rows,
    ):
        header, rows = builder(gig.tenant, start, end)
        assert header[-1] == "Code analytique"
        assert rows and rows[0][-1] == "2026-TOUR-A"


def test_the_dates_and_shows_exports_carry_the_new_data():
    show = ShowFactory(
        analytic_code="2026-TOUR-A",
        artists_count=4,
        technicians_count=0,
        soundcheck_minutes=90,
        soundcheck_to_set_minutes=30,
    )
    gig = GigFactory(show=show, tenant=show.tenant)

    header, rows = data_export.shows_rows(show.tenant)
    row = dict(zip(header, rows[0], strict=True))
    assert row["Artistes"] == 4 and row["Techniciens"] == 0
    assert row["Balances minimum (min)"] == 90
    assert row["Entre balances et set minimum (min)"] == 30
    assert row["Code analytique"] == "2026-TOUR-A"

    header, rows = data_export.gigs_rows(gig.tenant)
    assert header[-1] == "Code analytique" and rows[0][-1] == "2026-TOUR-A"


def test_a_formula_in_the_analytic_code_is_neutralised():
    show = ShowFactory(analytic_code="=1+1")
    gig = GigFactory(show=show, tenant=show.tenant)

    _header, rows = data_export.gigs_rows(gig.tenant)

    assert rows[0][-1] == "'=1+1"
