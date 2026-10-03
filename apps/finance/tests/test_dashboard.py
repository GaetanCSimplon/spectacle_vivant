import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.documents import invoicing
from apps.documents.factories import ContractFactory
from apps.documents.models import ContractVersion, Invoice
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

from .. import dashboard, services
from ..models import Payment
from .helpers import TENANT_FIELDS, issued_invoice, make_gig

pytestmark = pytest.mark.django_db

D = Decimal
TODAY = datetime.date(2026, 10, 3)
CASH = Payment.Method.CASH


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _issue_on(invoice, date):
    """Issue dates are frozen by the model: move one with a queryset update (tests only)."""
    Invoice.objects.filter(pk=invoice.pk).update(issue_date=date)
    invoice.refresh_from_db()


def _due(invoice, date):
    Invoice.objects.filter(pk=invoice.pk).update(due_date=date)
    invoice.refresh_from_db()


# --- year totals ----------------------------------------------------------------


def test_year_totals_count_only_that_year():
    gig = make_gig(price="1000.00")
    this_year = issued_invoice(gig, Invoice.Kind.DEPOSIT)  # 300
    _issue_on(this_year, datetime.date(2026, 3, 1))
    old = issued_invoice(make_gig(tenant=gig.tenant, price="500.00"))
    _issue_on(old, datetime.date(2025, 12, 31))
    services.record_payment(this_year, "100.00", datetime.date(2026, 5, 1), CASH)
    services.record_payment(old, "500.00", datetime.date(2025, 12, 31), CASH)

    invoiced, received = dashboard.year_totals(gig.tenant, 2026)

    assert (invoiced, received) == (D("300.00"), D("100.00"))


def test_year_totals_subtract_credit_notes():
    gig = make_gig(price="1000.00")
    invoice = issued_invoice(gig)
    note = invoicing.issue_invoice(invoicing.create_credit_note(invoice))
    for document in (invoice, note):
        _issue_on(document, datetime.date(2026, 4, 1))

    assert dashboard.year_totals(gig.tenant, 2026)[0] == 0


def test_year_totals_ignore_drafts_and_other_tenants():
    gig = make_gig()
    invoicing.create_invoice(gig, Invoice.Kind.FULL)
    other = issued_invoice(make_gig())
    _issue_on(other, datetime.date(2026, 4, 1))

    assert dashboard.year_totals(gig.tenant, 2026) == (0, 0)


def test_year_totals_are_exact_to_the_cent():
    gig = make_gig(price="100.10")
    invoice = issued_invoice(gig)
    _issue_on(invoice, datetime.date(2026, 1, 2))
    services.record_payment(invoice, "33.37", datetime.date(2026, 1, 3), CASH)

    assert dashboard.year_totals(gig.tenant, 2026) == (D("100.10"), D("33.37"))


# --- invoices to collect ----------------------------------------------------------


def test_an_unpaid_invoice_is_listed_with_what_is_left():
    gig = make_gig(price="1000.00")
    invoice = issued_invoice(gig)
    services.record_payment(invoice, "400.00", TODAY, CASH)
    _due(invoice, TODAY + datetime.timedelta(days=5))

    rows = dashboard.awaiting_payment(gig.tenant, TODAY)

    assert len(rows) == 1
    assert rows[0]["remaining"] == D("600.00")
    assert rows[0]["overdue"] is False
    assert rows[0]["gig"] == gig


def test_an_overdue_invoice_is_flagged_with_its_delay():
    gig = make_gig()
    _due(issued_invoice(gig), TODAY - datetime.timedelta(days=12))

    (row,) = dashboard.awaiting_payment(gig.tenant, TODAY)

    assert row["overdue"] is True
    assert row["late_days"] == 12


def test_an_invoice_due_today_is_not_late():
    gig = make_gig()
    _due(issued_invoice(gig), TODAY)

    (row,) = dashboard.awaiting_payment(gig.tenant, TODAY)

    assert row["overdue"] is False


def test_paid_drafts_credit_notes_and_cancelled_invoices_are_not_listed():
    tenant = make_gig().tenant
    paid = issued_invoice(make_gig(tenant=tenant, price="100.00"))
    services.record_payment(paid, "100.00", TODAY, CASH)
    invoicing.create_invoice(make_gig(tenant=tenant), Invoice.Kind.FULL)  # draft
    cancelled = issued_invoice(make_gig(tenant=tenant, price="100.00"))
    invoicing.issue_invoice(invoicing.create_credit_note(cancelled))

    assert dashboard.awaiting_payment(tenant, TODAY) == []


def test_the_oldest_due_date_comes_first():
    tenant = make_gig().tenant
    late = issued_invoice(make_gig(tenant=tenant))
    soon = issued_invoice(make_gig(tenant=tenant))
    _due(soon, TODAY + datetime.timedelta(days=3))
    _due(late, TODAY - datetime.timedelta(days=3))

    rows = dashboard.awaiting_payment(tenant, TODAY)

    assert [row["invoice"].pk for row in rows] == [late.pk, soon.pk]


def test_other_tenants_invoices_are_never_listed():
    issued_invoice(make_gig())

    assert dashboard.awaiting_payment(make_gig().tenant, TODAY) == []


# --- gigs without contract ----------------------------------------------------------


def _gig(tenant, status=Gig.Status.CONFIRMED, days=10):
    return GigFactory(tenant=tenant, status=status, date=TODAY + datetime.timedelta(days=days))


def test_a_confirmed_upcoming_gig_without_contract_is_listed():
    gig = _gig(make_gig().tenant)

    assert list(dashboard.gigs_without_contract(gig.tenant, TODAY)) == [gig]


def test_a_gig_with_a_generated_contract_is_not_listed():
    gig = _gig(make_gig().tenant)
    contract = ContractFactory(gig=gig)
    ContractVersion.objects.create(
        contract=contract, tenant=gig.tenant, number=1, pdf_file="contracts/x/c.pdf"
    )

    assert list(dashboard.gigs_without_contract(gig.tenant, TODAY)) == []


def test_a_contract_row_without_version_still_counts_as_missing():
    gig = _gig(make_gig().tenant)
    ContractFactory(gig=gig)

    assert list(dashboard.gigs_without_contract(gig.tenant, TODAY)) == [gig]


@pytest.mark.parametrize("status", [Gig.Status.OPTION, Gig.Status.SIGNED, Gig.Status.CANCELLED])
def test_only_confirmed_gigs_need_a_contract(status):
    tenant = make_gig().tenant
    _gig(tenant, status=status)

    assert list(dashboard.gigs_without_contract(tenant, TODAY)) == []


def test_past_gigs_are_not_listed_without_contract():
    tenant = make_gig().tenant
    _gig(tenant, days=-1)

    assert list(dashboard.gigs_without_contract(tenant, TODAY)) == []


# --- next gigs ------------------------------------------------------------------------


def test_next_gigs_are_sorted_limited_and_without_cancelled_or_past():
    tenant = make_gig().tenant
    gigs = [_gig(tenant, days=d) for d in (30, 5, 20, 1, 40, 10, 15)]
    _gig(tenant, status=Gig.Status.CANCELLED, days=2)
    _gig(tenant, days=-3)
    GigFactory(date=TODAY + datetime.timedelta(days=1))  # another tenant

    result = dashboard.next_gigs(tenant, TODAY)

    assert [g.date for g in result] == sorted(g.date for g in gigs)[:5]


# --- the home page ----------------------------------------------------------------------


@pytest.fixture
def tenant(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    return membership.tenant


def test_a_new_tenant_sees_a_call_to_create_a_date(client, tenant):
    text = client.get(reverse("home")).content.decode()

    assert "pas encore de date" in text
    assert "Factures à encaisser" not in text
    assert "Dates sans contrat" not in text


def test_home_shows_the_dashboard(client, tenant):
    gig = make_gig(tenant=tenant, price="1000.60")
    invoice = issued_invoice(gig)
    services.record_payment(invoice, "300.20", datetime.date.today(), CASH)
    Invoice.objects.filter(pk=invoice.pk).update(
        due_date=datetime.date.today() - datetime.timedelta(days=4)
    )
    pending = GigFactory(
        tenant=tenant,
        status=Gig.Status.CONFIRMED,
        date=datetime.date.today() + datetime.timedelta(days=9),
        show__title="Concert sans contrat",
    )

    text = client.get(reverse("home")).content.decode()

    assert "Factures à encaisser" in text
    assert "1 en retard" in text
    assert "En retard de 4 j" in text
    assert "700 €" in text  # 1000.60 - 300.20 = 700.40, shown in whole euros
    assert reverse("finance:page", args=[gig.pk]) in text
    assert "Dates sans contrat" in text
    assert pending.show.title in text
    assert "Prochaines dates" in text


def test_home_amounts_are_whole_euros_in_the_summary(client, tenant):
    gig = make_gig(tenant=tenant, price="1000.60")
    invoice = issued_invoice(gig)
    services.record_payment(invoice, "300.20", datetime.date.today(), CASH)

    text = client.get(reverse("home")).content.decode()

    assert "1 001 €" in text.replace(" ", " ").replace("\xa0", " ") or "1001 €" in text
    assert "300 €" in text


def test_home_never_shows_another_tenants_data(client, tenant):
    make_gig(tenant=tenant)
    other = make_gig()
    issued_invoice(other)
    GigFactory(
        tenant=other.tenant,
        status=Gig.Status.CONFIRMED,
        date=datetime.date.today() + datetime.timedelta(days=3),
        show__title="Secret d'un autre",
    )

    text = client.get(reverse("home")).content.decode()

    assert "Secret d'un autre" not in text
    assert "Factures à encaisser" not in text
