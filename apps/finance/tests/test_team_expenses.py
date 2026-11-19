"""Expenses advanced by a member of the team: what the structure still owes them."""

import datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.finance import bord, services
from apps.gigs.factories import GigMemberFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory, PersonFactory, TenantFactory
from apps.tenants.models import Person

from ..factories import ExpenseFactory
from ..models import Expense
from .helpers import TENANT_FIELDS, make_gig

pytestmark = pytest.mark.django_db

D = Decimal
TODAY = timezone.localdate()


@pytest.fixture
def tenant(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    return membership.tenant


@pytest.fixture
def gig(tenant):
    return make_gig(tenant=tenant, price="1000.00")


def _data(**extra):
    return {
        "category": "transport",
        "label": "Essence",
        "amount": "40.00",
        "date": "2026-10-03",
        **extra,
    }


def _filters(**kwargs):
    start = TODAY - datetime.timedelta(days=60)
    end = TODAY + datetime.timedelta(days=60)
    return bord.Filters(**{"start": start, "end": end, **kwargs})


# --- recording ----------------------------------------------------------------------------


def test_an_expense_is_the_structures_unless_a_member_is_chosen(client, gig, tenant):
    lea = PersonFactory(tenant=tenant)

    client.post(reverse("finance:expense-add", args=[gig.pk]), _data())
    client.post(reverse("finance:expense-add", args=[gig.pk]), _data(label="Train", person=lea.pk))

    own, advanced = Expense.objects.order_by("id")
    assert own.person is None and not own.to_reimburse
    assert advanced.person == lea and advanced.to_reimburse and advanced.reimbursed_on is None


def test_the_form_offers_the_team_of_the_structure_only(client, gig, tenant):
    PersonFactory(tenant=tenant, first_name="Léa", last_name="Durand")
    PersonFactory(first_name="Intrus", last_name="Etranger")

    page = client.get(reverse("finance:page", args=[gig.pk])).content.decode()

    assert "Léa Durand" in page and "Etranger" not in page and "La structure" in page


def test_a_person_of_another_structure_cannot_be_posted(client, gig, tenant):
    foreign = PersonFactory()

    response = client.post(reverse("finance:expense-add", args=[gig.pk]), _data(person=foreign.pk))

    assert response.status_code == 200
    assert not Expense.objects.exists()


# --- reimbursing --------------------------------------------------------------------------


def test_marking_an_expense_reimbursed_and_undoing_it(client, gig, tenant):
    expense = ExpenseFactory(gig=gig, person=PersonFactory(tenant=tenant))
    url = reverse("finance:expense-reimburse", args=[gig.pk, expense.pk])

    client.post(url, {"state": "done"})
    expense.refresh_from_db()
    assert expense.reimbursed_on == TODAY and not expense.to_reimburse

    client.post(url, {"state": "undo"})
    expense.refresh_from_db()
    assert expense.reimbursed_on is None and expense.to_reimburse


def test_an_expense_of_the_structure_cannot_be_reimbursed(client, gig):
    expense = ExpenseFactory(gig=gig)

    client.post(reverse("finance:expense-reimburse", args=[gig.pk, expense.pk]), {"state": "done"})

    expense.refresh_from_db()
    assert expense.reimbursed_on is None


def test_taking_the_member_off_clears_the_reimbursement_date(gig, tenant):
    expense = ExpenseFactory(
        gig=gig, person=PersonFactory(tenant=tenant), reimbursed_on=datetime.date(2026, 10, 9)
    )

    expense.person = None
    expense.save()

    expense.refresh_from_db()
    assert expense.reimbursed_on is None


def test_another_structure_cannot_reimburse_my_expense(client, gig, tenant):
    expense = ExpenseFactory(gig=gig, person=PersonFactory(tenant=tenant))
    other = MembershipFactory()
    client.force_login(other.user)

    response = client.post(
        reverse("finance:expense-reimburse", args=[gig.pk, expense.pk]), {"state": "done"}
    )

    assert response.status_code == 404
    expense.refresh_from_db()
    assert expense.reimbursed_on is None


def test_the_date_page_shows_the_status_and_the_split(client, gig, tenant):
    lea = PersonFactory(tenant=tenant, first_name="Léa", last_name="Durand")
    ExpenseFactory(gig=gig, amount="100.00")
    ExpenseFactory(gig=gig, amount="30.00", person=lea)
    ExpenseFactory(gig=gig, amount="20.00", person=lea, reimbursed_on=TODAY)

    page = client.get(reverse("finance:page", args=[gig.pk])).content.decode()

    assert "Avancée par Léa Durand" in page and "À rembourser" in page
    assert "Remboursée le" in page
    split = services.expense_split(Expense.objects.filter(gig=gig))
    assert split == {"structure": D("100.00"), "members": D("50.00"), "to_reimburse": D("30.00")}


# --- Bòrd ---------------------------------------------------------------------------------


def test_bord_splits_the_period_and_totals_what_is_owed_whatever_the_period():
    tenant = TenantFactory(**TENANT_FIELDS)
    lea = PersonFactory(tenant=tenant, first_name="Léa", last_name="Durand")
    gig = make_gig(tenant=tenant)
    ExpenseFactory(gig=gig, amount="100.00", date=TODAY)
    ExpenseFactory(gig=gig, amount="30.00", person=lea, date=TODAY)
    ExpenseFactory(gig=gig, amount="12.00", person=lea, date=TODAY - datetime.timedelta(days=400))
    ExpenseFactory(gig=gig, amount="9.00", person=lea, date=TODAY, reimbursed_on=TODAY)

    totals = bord.expenses(tenant, _filters(view="cash"))  # cash: by the date of the expense
    activity = bord.expenses(tenant, _filters())  # activity: by the date of the show
    owed = bord.to_reimburse(tenant)

    assert activity["total"] == D("151.00")
    assert totals["total"] == D("139.00")
    assert totals["split"]["structure"] == D("100.00") and totals["split"]["members"] == D("39.00")
    assert owed["total"] == D("42.00")  # the old one counts too
    assert [(row["name"], row["total"]) for row in owed["people"]] == [("Léa Durand", D("42.00"))]


def test_the_spender_filter_keeps_the_structure_or_one_member():
    tenant = TenantFactory(**TENANT_FIELDS)
    lea = PersonFactory(tenant=tenant)
    marc = PersonFactory(tenant=tenant)
    gig = make_gig(tenant=tenant)
    ExpenseFactory(gig=gig, amount="100.00", date=TODAY)
    ExpenseFactory(gig=gig, amount="30.00", person=lea, date=TODAY)
    ExpenseFactory(gig=gig, amount="7.00", person=marc, date=TODAY)

    assert bord.expenses(tenant, _filters(spender="structure"))["total"] == D("100.00")
    assert bord.expenses(tenant, _filters(spender=str(lea.pk)))["total"] == D("30.00")
    assert bord.expenses(tenant, _filters())["total"] == D("137.00")
    series = bord.monthly_series(tenant, _filters(spender=str(marc.pk)))
    assert sum(row["expenses"] for row in series) == D("7.00")


def test_the_bord_page_shows_the_amount_to_reimburse_and_the_filter(client, tenant, gig):
    lea = PersonFactory(tenant=tenant, first_name="Léa", last_name="Durand")
    ExpenseFactory(gig=gig, amount="30.00", person=lea, date=TODAY)

    page = client.get(reverse("tenants:profile")).content.decode()

    assert "À rembourser aux membres" in page and "Léa Durand" in page
    assert 'name="spender"' in page


def test_the_spender_filter_ignores_a_person_of_another_structure(client, tenant, gig):
    foreign = PersonFactory()
    ExpenseFactory(gig=gig, amount="30.00", date=TODAY)

    response = client.get(reverse("tenants:profile"), {"spender": str(foreign.pk)})

    assert response.status_code == 200  # invalid value: the default (everyone) is used
    assert "30" in response.content.decode()


# --- the member's card, deletion and export ----------------------------------------------


def test_the_card_lists_the_expenses_and_what_is_owed(client, tenant, gig):
    lea = PersonFactory(tenant=tenant)
    ExpenseFactory(gig=gig, label="Péage A7", amount="30.00", person=lea)
    ExpenseFactory(gig=gig, label="Hôtel", amount="20.00", person=lea, reimbursed_on=TODAY)

    page = client.get(reverse("tenants:person-detail", args=[lea.pk])).content.decode()

    assert "Péage A7" in page and "Hôtel" in page and "Reste à lui rembourser" in page
    assert "30.00 €" in page.replace(",", ".") or "30 €" in page


def test_a_member_with_expenses_cannot_be_deleted(client, tenant, gig):
    lea = PersonFactory(tenant=tenant)
    ExpenseFactory(gig=gig, person=lea)

    response = client.post(reverse("tenants:person-delete", args=[lea.pk]))

    assert response.status_code == 302
    assert Person.objects.filter(pk=lea.pk).exists()
    assert Expense.objects.filter(person=lea).exists()


def test_a_member_without_expenses_can_still_be_deleted(client, tenant):
    lea = PersonFactory(tenant=tenant)

    client.post(reverse("tenants:person-delete", args=[lea.pk]))

    assert not Person.objects.filter(pk=lea.pk).exists()


def test_the_export_says_who_paid_and_when_it_was_paid_back(client, tenant, gig):
    lea = PersonFactory(tenant=tenant, first_name="Léa", last_name="Durand")
    ExpenseFactory(gig=gig, label="Seule", date=datetime.date(2026, 3, 1))
    ExpenseFactory(
        gig=gig,
        label="Avance",
        person=lea,
        date=datetime.date(2026, 3, 2),
        reimbursed_on=datetime.date(2026, 4, 1),
    )

    from .test_exports import _download, _table

    rows = _table(_download(client, "depenses"))

    assert rows[0][-3:] == ["Dépensé par", "Remboursée le", "Code analytique"]
    assert rows[1][-3:-1] == ["La structure", ""]
    assert rows[2][-3:-1] == ["Léa Durand", "01/04/2026"]


# --- the operations table: debit and credit ------------------------------------------------


def test_each_operation_has_a_debit_and_a_credit():
    tenant = TenantFactory(**TENANT_FIELDS)
    lea = PersonFactory(tenant=tenant)
    gig = make_gig(tenant=tenant, price="1000.00")
    ExpenseFactory(gig=gig, amount="100.00")
    ExpenseFactory(gig=gig, amount="30.00", person=lea)
    quiet = make_gig(tenant=tenant, price="500.00")

    rows = {row["gig"].pk: row for row in bord.operations(tenant, _filters())}

    assert rows[gig.pk]["debit"] == D("130.00") and rows[gig.pk]["amount"] == D("1000.00")
    assert rows[quiet.pk]["debit"] == D("0")


def test_the_debit_follows_the_spender_filter():
    tenant = TenantFactory(**TENANT_FIELDS)
    lea = PersonFactory(tenant=tenant)
    gig = make_gig(tenant=tenant)
    ExpenseFactory(gig=gig, amount="100.00")
    ExpenseFactory(gig=gig, amount="30.00", person=lea)

    only_structure = bord.operations(tenant, _filters(spender="structure"))[0]["debit"]
    only_lea = bord.operations(tenant, _filters(spender=str(lea.pk)))[0]["debit"]

    assert (only_structure, only_lea) == (D("100.00"), D("30.00"))


def test_the_table_has_a_debit_and_a_credit_column(client, tenant, gig):
    ExpenseFactory(gig=gig, amount="130.00")

    page = client.get(reverse("tenants:profile")).content.decode()
    table = page.split('id="operations"')[1].split("</table>")[0]

    assert ">Débit<" in table and ">Crédit<" in table and ">Montant<" not in table
    assert "130 €" in table


# --- Bord: team pay in the debit and the "Total" line (PR 3) ---


def _fee(gig, amount):
    GigMemberFactory(gig=gig, tenant=gig.tenant, cachet_amount=amount)


def test_the_bord_debit_adds_the_team_pay_for_the_owner_only():
    tenant = TenantFactory(**TENANT_FIELDS)
    gig = make_gig(tenant=tenant, price="1000.00")
    ExpenseFactory(gig=gig, amount="100.00")
    _fee(gig, "250.50")
    cancelled = make_gig(tenant=tenant, gig_fields={"status": Gig.Status.CANCELLED})
    _fee(cancelled, "999.00")

    owner = {r["gig"].pk: r for r in bord.operations(tenant, _filters(), with_fees=True)}
    member = {r["gig"].pk: r for r in bord.operations(tenant, _filters())}

    assert owner[gig.pk]["debit"] == D("350.50")
    assert owner[cancelled.pk]["debit"] == D("0")
    assert member[gig.pk]["debit"] == D("100.00")


def test_the_team_pay_is_left_out_when_spent_by_is_filtered():
    tenant = TenantFactory(**TENANT_FIELDS)
    gig = make_gig(tenant=tenant)
    ExpenseFactory(gig=gig, amount="100.00")
    _fee(gig, "250.00")

    row = bord.operations(tenant, _filters(spender="structure"), with_fees=True)[0]

    assert row["debit"] == D("100.00")


def test_the_team_pay_of_another_tenant_is_never_counted():
    tenant, other = TenantFactory(**TENANT_FIELDS), TenantFactory(**TENANT_FIELDS)
    gig = make_gig(tenant=tenant)
    GigMemberFactory(gig=gig, tenant=other, cachet_amount="500.00")

    assert bord.operations(tenant, _filters(), with_fees=True)[0]["debit"] == D("0")


def test_the_total_covers_every_date_and_gives_the_balance():
    tenant = TenantFactory(**TENANT_FIELDS)
    for _i in range(23):  # more than the 20 rows shown
        gig = make_gig(tenant=tenant, price="100.00")
        ExpenseFactory(gig=gig, amount="30.10")

    total = bord.operations_total(bord.operations(tenant, _filters()))

    assert total["credit"] == D("2300.00") and total["debit"] == D("692.30")
    assert total["balance"] == D("1607.70")
    assert bord.operations_total([]) == {"debit": D("0"), "credit": D("0"), "balance": D("0")}


def test_the_total_line_names_the_balance(client, tenant, gig):
    page = client.get(reverse("tenants:profile")).content.decode()
    table = page.split('id="operations"')[1].split("</table>")[0]
    assert "<tfoot>" in table and "Excédent" in table

    ExpenseFactory(gig=gig, amount="5000.00")
    table = client.get(reverse("tenants:profile")).content.decode().split('id="operations"')[1]
    assert "Déficit" in table.split("</table>")[0]
