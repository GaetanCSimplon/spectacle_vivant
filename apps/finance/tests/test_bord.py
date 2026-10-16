"""The Bòrd figures: every definition of docs/cadrage/12-bord-indicateurs.md."""

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.documents import invoicing
from apps.finance import bord, services
from apps.finance.factories import ExpenseFactory
from apps.finance.models import Expense
from apps.finance.tests.helpers import TENANT_FIELDS, issued_invoice, make_gig
from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.gigs.models import Gig
from apps.tenants.factories import PersonFactory, TenantFactory
from apps.tenants.models import Tenant

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()
D = Decimal


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def tenant():
    return TenantFactory(**TENANT_FIELDS)


def _filters(**kwargs):
    start = TODAY - datetime.timedelta(days=60)
    end = TODAY + datetime.timedelta(days=60)
    return bord.Filters(**{"start": start, "end": end, **kwargs})


def _gig(tenant, days=10, price="1000.00", status=Gig.Status.CONFIRMED, **fields):
    return make_gig(
        tenant=tenant,
        price=price,
        gig_fields={"status": status, "date": TODAY + datetime.timedelta(days=days), **fields},
    )


def _pay(invoice, amount, days_ago=0):
    return services.record_payment(
        invoice, amount, TODAY - datetime.timedelta(days=days_ago), "transfer"
    )


# --- periods ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("preset", "today", "expected"),
    [
        (
            "mois",
            datetime.date(2026, 10, 16),
            (datetime.date(2026, 10, 1), datetime.date(2026, 10, 31)),
        ),
        (
            "mois",
            datetime.date(2026, 12, 5),
            (datetime.date(2026, 12, 1), datetime.date(2026, 12, 31)),
        ),
        (
            "mois",
            datetime.date(2028, 2, 10),
            (datetime.date(2028, 2, 1), datetime.date(2028, 2, 29)),
        ),
        (
            "trimestre",
            datetime.date(2026, 10, 16),
            (datetime.date(2026, 10, 1), datetime.date(2026, 12, 31)),
        ),
        (
            "trimestre",
            datetime.date(2026, 5, 2),
            (datetime.date(2026, 4, 1), datetime.date(2026, 6, 30)),
        ),
        (
            "annee",
            datetime.date(2026, 10, 16),
            (datetime.date(2026, 1, 1), datetime.date(2026, 12, 31)),
        ),
        (
            "inconnu",
            datetime.date(2026, 3, 9),
            (datetime.date(2026, 3, 1), datetime.date(2026, 3, 31)),
        ),
    ],
)
def test_period_bounds(preset, today, expected):
    assert bord.period_bounds(preset, today) == expected


# --- dates -----------------------------------------------------------------


def test_options_confirmed_and_cancelled_dates_are_counted_apart(tenant):
    _gig(tenant, status=Gig.Status.CONFIRMED)
    _gig(tenant, status=Gig.Status.SIGNED)
    _gig(tenant, status=Gig.Status.OPTION)
    _gig(tenant, status=Gig.Status.CANCELLED)

    assert bord.date_counts(tenant, _filters()) == {"confirmed": 2, "options": 1, "cancelled": 1}


def test_a_date_outside_the_period_is_not_counted(tenant):
    _gig(tenant, days=200)
    _gig(tenant, days=-200)

    assert bord.date_counts(tenant, _filters())["confirmed"] == 0


def test_the_period_includes_both_bounds(tenant):
    first = _gig(tenant, days=0)
    filters = bord.Filters(start=first.date, end=first.date)

    assert bord.date_counts(tenant, filters)["confirmed"] == 1


# --- revenue ---------------------------------------------------------------


def test_planned_revenue_leaves_out_options_and_cancelled_gigs(tenant):
    _gig(tenant, price="1000.00")
    _gig(tenant, price="500.50", status=Gig.Status.SIGNED)
    _gig(tenant, price="300.00", status=Gig.Status.OPTION)
    _gig(tenant, price="900.00", status=Gig.Status.CANCELLED)

    totals = bord.revenue(tenant, _filters())

    assert totals["planned"] == D("1500.50")
    assert totals["options_planned"] == D("300.00")


def test_invoiced_follows_the_issue_date_and_counts_credit_notes_negative(tenant):
    gig = _gig(tenant, price="1000.00")
    invoice = issued_invoice(gig)
    note = invoicing.create_credit_note(invoice)
    invoicing.issue_invoice(note)

    assert bord.revenue(tenant, _filters())["invoiced"] == D("0.00")
    elsewhere = bord.Filters(
        start=TODAY + datetime.timedelta(days=1), end=TODAY + datetime.timedelta(days=30)
    )
    assert bord.revenue(tenant, elsewhere)["invoiced"] == D("0.00")
    only_invoice = issued_invoice(_gig(tenant, price="250.00"))
    assert only_invoice.status == "issued"
    assert bord.revenue(tenant, _filters())["invoiced"] == D("250.00")


def test_received_follows_the_payment_date(tenant):
    invoice = issued_invoice(_gig(tenant, price="1000.00"))
    _pay(invoice, "400.00", days_ago=2)
    _pay(invoice, "100.00", days_ago=90)

    assert bord.revenue(tenant, _filters())["received"] == D("400.00")


def test_invoiced_is_excl_tax_and_received_is_incl_tax():
    taxable = TenantFactory(
        **{
            **TENANT_FIELDS,
            "vat_regime": Tenant.VatRegime.TAXABLE,
            "vat_rate": D("20.00"),
            "vat_number": "FR12345678901",
        }
    )
    gig = _gig(taxable, price="1000.00")
    invoice = issued_invoice(gig)
    _pay(invoice, "1200.00")

    totals = bord.revenue(taxable, _filters())

    assert (totals["planned"], totals["invoiced"], totals["received"]) == (
        D("1000.00"),
        D("1000.00"),
        D("1200.00"),
    )


def test_the_show_filter_narrows_every_figure(tenant):
    kept = _gig(tenant, price="1000.00")
    other = _gig(tenant, price="700.00")
    for gig in (kept, other):
        invoice = issued_invoice(gig)
        _pay(invoice, "100.00")
        ExpenseFactory(gig=gig, amount="10.00", date=TODAY)

    filters = _filters(show=kept.show)

    assert bord.revenue(tenant, filters) == {
        "planned": D("1000.00"),
        "options_planned": D("0"),
        "invoiced": D("1000.00"),
        "received": D("100.00"),
    }
    assert bord.expenses(tenant, filters)["total"] == D("10.00")
    assert bord.date_counts(tenant, filters)["confirmed"] == 1


# --- expenses and balance --------------------------------------------------


def test_expenses_are_totalled_by_category_inside_the_period(tenant):
    gig = _gig(tenant)
    ExpenseFactory(gig=gig, category=Expense.Category.TRANSPORT, amount="40.00", date=TODAY)
    ExpenseFactory(gig=gig, category=Expense.Category.TRANSPORT, amount="10.50", date=TODAY)
    ExpenseFactory(gig=gig, category=Expense.Category.LODGING, amount="80.00", date=TODAY)
    ExpenseFactory(
        gig=gig, amount="999.00", date=TODAY - datetime.timedelta(days=400)
    )  # outside the period

    result = bord.expenses(tenant, _filters())

    assert result["total"] == D("130.50")
    assert [(r["category"], r["total"]) for r in result["by_category"]] == [
        ("Hébergement", D("80.00")),
        ("Transport", D("50.50")),
    ]


def test_expenses_of_a_cancelled_gig_still_count(tenant):
    gig = _gig(tenant, status=Gig.Status.CANCELLED)
    ExpenseFactory(gig=gig, amount="60.00", date=TODAY)

    assert bord.expenses(tenant, _filters())["total"] == D("60.00")


def test_balance_uses_the_chosen_kind_of_revenue(tenant):
    invoice = issued_invoice(_gig(tenant, price="1000.00"))
    _pay(invoice, "300.00")
    ExpenseFactory(gig=invoice.gig, amount="100.00", date=TODAY)
    revenue = bord.revenue(tenant, _filters())
    spent = bord.expenses(tenant, _filters())

    assert bord.balance(revenue, spent, "planned") == D("900.00")
    assert bord.balance(revenue, spent, "invoiced") == D("900.00")
    assert bord.balance(revenue, spent, "received") == D("200.00")


# --- receivables -----------------------------------------------------------


def test_a_partial_payment_reduces_what_is_still_to_collect(tenant):
    invoice = issued_invoice(_gig(tenant, price="1000.00"))
    _pay(invoice, "400.00")

    result = bord.receivables(tenant, TODAY)

    assert result["remaining"] == D("600.00")
    assert len(result["rows"]) == 1


def test_late_is_the_part_past_its_due_date(tenant):
    late = issued_invoice(_gig(tenant, price="1000.00"))
    on_time = issued_invoice(_gig(tenant, price="500.00"))
    type(late).objects.filter(pk=late.pk).update(due_date=TODAY - datetime.timedelta(days=3))
    type(on_time).objects.filter(pk=on_time.pk).update(due_date=TODAY)

    result = bord.receivables(tenant, TODAY)

    assert result["remaining"] == D("1500.00")
    assert result["late"] == D("1000.00")


def test_a_settled_invoice_is_no_longer_to_collect(tenant):
    invoice = issued_invoice(_gig(tenant, price="1000.00"))
    _pay(invoice, "1000.00")

    assert bord.receivables(tenant, TODAY)["remaining"] == D("0")


def test_receivables_follow_the_show_and_ignore_the_period(tenant):
    old = _gig(tenant, days=-300, price="800.00")
    issued_invoice(old)
    issued_invoice(_gig(tenant, price="200.00"))

    assert bord.receivables(tenant, TODAY)["remaining"] == D("1000.00")
    assert bord.receivables(tenant, TODAY, show=old.show)["remaining"] == D("800.00")


# --- team ------------------------------------------------------------------


def test_a_person_on_several_dates_is_counted_once(tenant):
    person = PersonFactory(tenant=tenant)
    for days in (5, 12):
        gig = _gig(tenant, days=days)
        GigMemberFactory(gig=gig, tenant=tenant, person=person, name="Léa Martin")
    GigMemberFactory(gig=_gig(tenant, days=20), tenant=tenant, person=None, name="Invité")

    assert bord.people_mobilised(tenant, _filters()) == 2


def test_a_typed_name_equal_to_a_team_member_is_not_counted_twice(tenant):
    person = PersonFactory(tenant=tenant)
    gig = _gig(tenant)
    GigMemberFactory(gig=gig, tenant=tenant, person=person, name="Léa Martin")
    GigMemberFactory(gig=_gig(tenant, days=6), tenant=tenant, person=None, name=" léa martin ")

    assert bord.people_mobilised(tenant, _filters()) == 1


def test_options_and_cancelled_dates_do_not_mobilise_anyone(tenant):
    for status in (Gig.Status.OPTION, Gig.Status.CANCELLED):
        GigMemberFactory(gig=_gig(tenant, status=status), tenant=tenant, name="Zoé")

    assert bord.people_mobilised(tenant, _filters()) == 0


# --- operations ------------------------------------------------------------


def test_operations_give_a_status_an_amount_and_the_documents(tenant):
    pending = _gig(tenant, days=3, price="1000.00")
    paid = _gig(tenant, days=2, price="500.00")
    cancelled = _gig(tenant, days=1, status=Gig.Status.CANCELLED)
    invoice = issued_invoice(paid)
    _pay(invoice, "500.00")
    issued_invoice(pending)

    rows = {row["gig"].pk: row for row in bord.operations(tenant, _filters())}

    assert rows[pending.pk]["status"] == "pending"
    assert rows[paid.pk]["status"] == "paid"
    assert rows[cancelled.pk]["status"] == "cancelled"
    assert rows[paid.pk]["label"] == paid.show.title
    assert [d["label"] for d in rows[paid.pk]["documents"]][0].startswith("Facture")
    assert rows[paid.pk]["amount"] == D("500.00")


def test_a_partly_invoiced_date_is_not_paid_even_if_its_invoice_is(tenant):
    gig = _gig(tenant, price="1000.00")
    deposit = invoicing.create_invoice(gig, invoicing.Invoice.Kind.DEPOSIT)
    invoicing.issue_invoice(deposit)
    _pay(deposit, deposit.total_incl_tax)

    [row] = bord.operations(tenant, _filters())

    assert row["status"] == "pending"


def test_operations_amount_follows_the_chosen_figure(tenant):
    gig = _gig(tenant, price="1000.00")
    invoice = issued_invoice(gig)
    _pay(invoice, "250.00")

    amounts = {
        figure: bord.operations(tenant, _filters(figure=figure))[0]["amount"]
        for figure in bord.FIGURES
    }

    assert amounts == {"planned": D("1000.00"), "invoiced": D("1000.00"), "received": D("250.00")}


def test_operations_can_be_filtered_by_status_and_limited(tenant):
    paid = _gig(tenant, days=1)
    _pay(issued_invoice(paid), "1000.00")
    _gig(tenant, days=2)
    _gig(tenant, days=3)

    assert len(bord.operations(tenant, _filters(status="paid"))) == 1
    assert len(bord.operations(tenant, _filters(status="pending"))) == 2
    assert len(bord.operations(tenant, _filters(), limit=2)) == 2


def test_operations_are_newest_first(tenant):
    _gig(tenant, days=1)
    last = _gig(tenant, days=9)

    assert bord.operations(tenant, _filters())[0]["gig"] == last


# --- attention -------------------------------------------------------------


def _terms(**kwargs):
    day = TODAY + datetime.timedelta(days=5)
    return {"deposit_due_on": day, "balance_due_on": day, **kwargs}


def test_nothing_to_report_when_everything_is_in_order(tenant):
    _gig(tenant, status=Gig.Status.SIGNED, **_terms())

    assert bord.attention(tenant, TODAY) == ([], 0)


def test_an_overdue_invoice_is_reported_with_its_reason_and_amount(tenant):
    invoice = issued_invoice(_gig(tenant, days=-20, price="1000.00"))
    type(invoice).objects.filter(pk=invoice.pk).update(due_date=TODAY - datetime.timedelta(days=4))

    [item], total = bord.attention(tenant, TODAY)

    assert total == 1
    assert item["amount"] == D("1000.00")
    assert "4 jour" in str(item["reason"])
    assert invoice.number in str(item["text"])


def test_a_confirmed_date_within_30_days_needs_a_signed_contract(tenant):
    _gig(tenant, days=29, status=Gig.Status.CONFIRMED, **_terms())
    _gig(tenant, days=45, status=Gig.Status.CONFIRMED, **_terms())  # too far
    _gig(tenant, days=10, status=Gig.Status.SIGNED, **_terms())  # signed

    items, total = bord.attention(tenant, TODAY)

    assert total == 1
    assert "Contrat" in str(items[0]["text"])


def test_a_confirmed_date_within_30_days_needs_payment_terms(tenant):
    _gig(tenant, days=10, status=Gig.Status.SIGNED)
    _gig(tenant, days=10, status=Gig.Status.SIGNED, deposit_due_on=TODAY)  # one term is enough

    items, total = bord.attention(tenant, TODAY)

    assert total == 1
    assert "Échéances" in str(items[0]["text"])


def test_options_expiring_soon_or_expired_are_reported(tenant):
    _gig(tenant, status=Gig.Status.OPTION, option_expires_on=TODAY + datetime.timedelta(days=7))
    _gig(tenant, status=Gig.Status.OPTION, option_expires_on=TODAY - datetime.timedelta(days=2))
    _gig(tenant, status=Gig.Status.OPTION, option_expires_on=TODAY + datetime.timedelta(days=8))
    _gig(tenant, status=Gig.Status.OPTION)

    items, total = bord.attention(tenant, TODAY)

    assert total == 2
    assert "expirée" in str(items[0]["reason"])


def test_at_most_five_items_are_shown_and_the_total_is_kept(tenant):
    for days in range(1, 8):
        _gig(tenant, days=days, status=Gig.Status.SIGNED)  # no payment terms

    items, total = bord.attention(tenant, TODAY)

    assert (len(items), total) == (5, 7)
    assert [i["due"] for i in items] == sorted(i["due"] for i in items)


def test_overdue_invoices_come_before_everything_else(tenant):
    _gig(tenant, days=1, status=Gig.Status.SIGNED)
    invoice = issued_invoice(_gig(tenant, days=-30))
    type(invoice).objects.filter(pk=invoice.pk).update(due_date=TODAY - datetime.timedelta(days=1))

    items, _total = bord.attention(tenant, TODAY)

    assert "Facture" in str(items[0]["text"])


def test_incomplete_dates_counts_missing_contracts_and_terms(tenant):
    _gig(tenant, status=Gig.Status.CONFIRMED, **_terms())  # contract not signed
    _gig(tenant, status=Gig.Status.SIGNED)  # no terms
    _gig(tenant, status=Gig.Status.SIGNED, **_terms())  # complete
    _gig(tenant, status=Gig.Status.OPTION)  # not confirmed: not counted

    assert bord.incomplete_dates(tenant, _filters()) == 2


# --- the whole summary and isolation ---------------------------------------


def test_summary_assembles_every_block(tenant):
    gig = _gig(tenant, price="1000.00", status=Gig.Status.SIGNED, **_terms())
    invoice = issued_invoice(gig)
    _pay(invoice, "400.00")
    ExpenseFactory(gig=gig, amount="100.00", date=TODAY)

    result = bord.summary(tenant, _filters(figure="received"), TODAY)

    assert result["dates"]["confirmed"] == 1
    assert result["balance"] == D("300.00")
    assert result["receivables"]["remaining"] == D("600.00")
    assert result["attention"] == [] and result["attention_total"] == 0
    assert len(result["operations"]) == 1


def test_nothing_of_another_tenant_is_ever_counted(tenant):
    other = TenantFactory(**TENANT_FIELDS)
    gig = _gig(other, price="5000.00")
    invoice = issued_invoice(gig)
    _pay(invoice, "100.00")
    ExpenseFactory(gig=gig, amount="50.00", date=TODAY)
    GigMemberFactory(gig=gig, tenant=other, name="Autre")
    GigFactory(tenant=other, status=Gig.Status.OPTION, option_expires_on=TODAY)

    result = bord.summary(tenant, _filters(), TODAY)

    assert result["dates"] == {"confirmed": 0, "options": 0, "cancelled": 0}
    assert result["revenue"]["planned"] == 0 and result["revenue"]["received"] == 0
    assert result["expenses"]["total"] == 0
    assert result["receivables"]["remaining"] == 0
    assert result["people"] == 0
    assert result["operations"] == [] and result["attention"] == []


# --- charts ----------------------------------------------------------------


def _month(offset):
    """First day of the month `offset` months after the current one."""
    index = TODAY.year * 12 + TODAY.month - 1 + offset
    return datetime.date(index // 12, index % 12 + 1, 1)


def test_the_series_has_one_entry_per_month_even_when_empty(tenant):
    filters = bord.Filters(start=_month(-2), end=_month(1) + datetime.timedelta(days=5))

    series = bord.monthly_series(tenant, filters)

    assert [row["month"] for row in series] == [_month(-2), _month(-1), _month(0), _month(1)]
    assert all(row["revenue"] == 0 and row["expenses"] == 0 for row in series)


def test_each_figure_is_put_in_the_month_of_its_own_date(tenant):
    last = _month(-1) + datetime.timedelta(days=4)
    gig = _gig(tenant, days=(last - TODAY).days, price="1000.00")
    invoice = issued_invoice(gig)  # issued today
    _pay(invoice, "300.00", days_ago=(TODAY - last).days)
    ExpenseFactory(gig=gig, amount="40.00", date=TODAY)
    filters = bord.Filters(start=_month(-1), end=_month(0) + datetime.timedelta(days=27))

    def by_month(figure):
        rows = bord.monthly_series(tenant, bord.Filters(**{**filters.__dict__, "figure": figure}))
        return {row["month"]: row["revenue"] for row in rows}

    assert by_month("planned") == {_month(-1): D("1000.00"), _month(0): D("0")}
    assert by_month("invoiced") == {_month(-1): D("0"), _month(0): D("1000.00")}
    assert by_month("received") == {_month(-1): D("300.00"), _month(0): D("0")}
    assert bord.monthly_series(tenant, filters)[1]["expenses"] == D("40.00")


def test_the_series_follows_the_show_and_never_mixes_tenants(tenant):
    kept = _gig(tenant, days=1, price="1000.00")
    _gig(tenant, days=1, price="700.00")
    _gig(TenantFactory(**TENANT_FIELDS), days=1, price="5000.00")
    filters = _filters(show=kept.show)

    total = sum(row["revenue"] for row in bord.monthly_series(tenant, filters))

    assert total == D("1000.00")


def test_a_very_long_period_keeps_the_last_36_months(tenant):
    filters = bord.Filters(start=datetime.date(2015, 1, 1), end=TODAY)

    series = bord.monthly_series(tenant, filters)

    assert len(series) == 36
    assert series[-1]["month"] == TODAY.replace(day=1)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 1), (1, 1), (7, 10), (120, 200), (1500, 2000), (5000, 5000), (5001, 10000)],
)
def test_the_chart_scale_is_a_round_number(value, expected):
    assert bord._nice_ceiling(D(value)) == expected


def test_chart_bars_are_proportional_and_never_negative(tenant):
    series = [
        {"month": TODAY, "label": "10/26", "revenue": D("1000"), "expenses": D("500")},
        {"month": TODAY, "label": "11/26", "revenue": D("-200"), "expenses": D("0")},
    ]

    chart = bord.monthly_chart(series)

    first, second = chart["groups"]
    assert first["revenue"]["h"] == pytest.approx(2 * first["expenses"]["h"], rel=0.01)
    assert second["revenue"]["h"] == 0
    assert chart["ticks"][-1]["label"] == "1 000 €"
    assert chart["has_data"] is True


def test_an_empty_series_gives_a_chart_without_data(tenant):
    chart = bord.monthly_chart(bord.monthly_series(tenant, _filters()))

    assert chart["has_data"] is False
    assert all(group["revenue"]["h"] == 0 for group in chart["groups"])


def test_category_bars_are_relative_to_the_largest(tenant):
    gig = _gig(tenant)
    ExpenseFactory(gig=gig, category=Expense.Category.LODGING, amount="200.00", date=TODAY)
    ExpenseFactory(gig=gig, category=Expense.Category.TRANSPORT, amount="50.00", date=TODAY)

    rows = bord.expenses(tenant, _filters())["by_category"]

    assert [row["percent"] for row in rows] == [100, 25]
