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
from ..factories import ExpenseFactory
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
    assert "contrat à générer" not in text


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
    assert "Date du" in text and "contrat à générer" in text  # alert for the pending gig
    assert "Facture " in text and "en retard de 4 jour(s)" in text  # alert for the late invoice
    assert "Prochaines dates" in text
    assert pending.pk  # created above: it feeds the alerts


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


# --- deposit and balance lines of a gig (F-76) ----------------------------------------


def _lines(gig):
    return {line["label"]: line for line in dashboard.gig_payment_lines(gig)}


def test_a_gig_with_no_invoice_shows_the_planned_deposit_and_balance():
    gig = make_gig(price="1000.00")  # 30 % deposit, franchise: no VAT

    lines = _lines(gig)

    assert lines["Acompte"] == {"label": "Acompte", "state": "to_invoice", "amount": D("300.00")}
    assert lines["Solde"]["amount"] == D("700.00")
    assert lines["Solde"]["state"] == "to_invoice"


def test_planned_amounts_include_vat_for_a_taxable_tenant():
    gig = make_gig(price="1000.00", vat_regime="taxable", vat_rate="20.00")

    lines = _lines(gig)

    assert lines["Acompte"]["amount"] == D("360.00")
    assert lines["Solde"]["amount"] == D("840.00")


def test_an_issued_deposit_is_to_collect_then_paid():
    gig = make_gig(price="1000.00")
    deposit = issued_invoice(gig, Invoice.Kind.DEPOSIT)

    assert _lines(gig)["Acompte"]["state"] == "to_collect"
    assert _lines(gig)["Acompte"]["amount"] == D("300.00")

    services.record_payment(deposit, "100.00", TODAY, CASH)
    assert _lines(gig)["Acompte"]["amount"] == D("200.00")  # what is left to collect

    services.record_payment(deposit, "200.00", TODAY, CASH)
    assert _lines(gig)["Acompte"] == {"label": "Acompte", "state": "paid", "amount": D("300.00")}
    assert _lines(gig)["Solde"]["state"] == "to_invoice"


def test_a_full_invoice_replaces_deposit_and_balance_by_one_line():
    gig = make_gig(price="1000.00")
    issued_invoice(gig, Invoice.Kind.FULL)

    lines = dashboard.gig_payment_lines(gig)

    assert [line["label"] for line in lines] == ["Facture totale"]
    assert lines[0]["state"] == "to_collect"
    assert lines[0]["amount"] == D("1000.00")


def test_a_draft_invoice_does_not_count_as_invoiced():
    gig = make_gig(price="1000.00")
    invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT)

    assert _lines(gig)["Acompte"]["state"] == "to_invoice"


def test_home_cards_show_the_lines_of_upcoming_gigs(client):
    membership = MembershipFactory(
        **{f"tenant__{k}": v for k, v in TENANT_FIELDS.items() if k != "name"}
    )
    client.force_login(membership.user)
    GigFactory(
        tenant=membership.tenant,
        price="1000.00",
        date=datetime.date.today() + datetime.timedelta(days=5),
    )

    content = client.get(reverse("home")).content.decode()

    assert "Acompte" in content
    assert "300 € ·" in content
    assert "à facturer" in content


# --- year overview: planned against real (F-76) ---------------------------------------


def test_overview_compares_planned_invoiced_received_and_spent():
    gig = make_gig(price="1000.00", gig_fields={"date": datetime.date(2026, 11, 5)})
    invoice = issued_invoice(gig, Invoice.Kind.DEPOSIT)
    services.record_payment(invoice, "100.00", TODAY, CASH)
    ExpenseFactory(gig=gig, amount="40.00")

    overview = dashboard.year_overview(gig.tenant, 2026)

    assert overview["gig_count"] == 1
    assert overview["planned"] == D("1000.00")
    assert overview["invoiced"] == D("300.00")
    assert overview["to_invoice"] == D("700.00")
    assert overview["received"] == D("100.00")
    assert overview["to_collect"] == D("200.00")
    assert overview["spent"] == D("40.00")
    assert overview["result"] == D("60.00")


def test_overview_ignores_other_years_cancelled_gigs_and_other_tenants():
    gig = make_gig(price="1000.00", gig_fields={"date": datetime.date(2026, 11, 5)})
    tenant = gig.tenant
    make_gig(tenant=tenant, price="500.00", gig_fields={"date": datetime.date(2027, 1, 5)})
    cancelled = make_gig(
        tenant=tenant,
        price="700.00",
        gig_fields={"date": datetime.date(2026, 12, 5), "status": Gig.Status.CANCELLED},
    )
    ExpenseFactory(gig=cancelled, amount="90.00")
    other = make_gig(price="9999.00", gig_fields={"date": datetime.date(2026, 11, 6)})
    ExpenseFactory(gig=other, amount="500.00")

    overview = dashboard.year_overview(tenant, 2026)

    assert overview["gig_count"] == 1
    assert overview["planned"] == D("1000.00")
    assert overview["spent"] == D("0.00")


def test_overview_of_an_empty_year_is_all_zero():
    overview = dashboard.year_overview(make_gig().tenant, 1999)
    assert overview["gig_count"] == 0
    assert overview["planned"] == overview["result"] == D("0.00")


def test_overview_is_shown_on_the_home_page(client):
    membership = MembershipFactory(
        **{f"tenant__{k}": v for k, v in TENANT_FIELDS.items() if k != "name"}
    )
    client.force_login(membership.user)
    GigFactory(tenant=membership.tenant, price="1000.00", date=datetime.date.today())

    content = client.get(reverse("home")).content.decode()

    assert "Solde de l&#x27;année" in content or "Solde de l'année" in content
    assert "Reste à facturer" in content
