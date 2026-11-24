from decimal import Decimal

import pytest
from django.urls import reverse

from apps.gigs.factories import GigMemberFactory
from apps.tenants.factories import MembershipFactory

from .. import services
from ..factories import ExpenseFactory
from ..models import Expense
from .helpers import make_gig

pytestmark = pytest.mark.django_db

D = Decimal


def test_fees_are_added_to_what_was_spent_to_the_cent():
    gig = make_gig()
    ExpenseFactory(gig=gig, amount="50.10")
    GigMemberFactory(gig=gig, cachet_amount="120.55")
    GigMemberFactory(gig=gig, cachet_amount="80.00")
    GigMemberFactory(gig=gig, cachet_amount=None)

    balance = services.gig_balance(gig)

    assert balance.fees == D("200.55")
    assert balance.entered == D("50.10")
    assert balance.spent == D("250.65")
    assert balance.result == D("-250.65")
    assert not balance.fees_double_count


def test_a_gig_without_team_has_no_fees():
    balance = services.gig_balance(make_gig())

    assert balance.fees == 0
    assert balance.spent == 0


def test_a_cancelled_gig_has_no_fees():
    gig = make_gig(gig_fields={"status": "cancelled"})
    GigMemberFactory(gig=gig, cachet_amount="100.00")

    assert services.gig_balance(gig).fees == 0


def test_a_fees_expense_next_to_team_fees_is_flagged():
    gig = make_gig()
    GigMemberFactory(gig=gig, cachet_amount="100.00")
    ExpenseFactory(gig=gig, category=Expense.Category.FEES, amount="100.00")

    balance = services.gig_balance(gig)

    assert balance.fees_double_count
    assert balance.spent == D("200.00")  # warned, never blocked or corrected


def test_a_fees_expense_without_team_fees_is_not_flagged():
    gig = make_gig()
    ExpenseFactory(gig=gig, category=Expense.Category.FEES, amount="100.00")

    assert not services.gig_balance(gig).fees_double_count


def test_other_tenants_members_are_not_counted():
    gig = make_gig()
    GigMemberFactory(cachet_amount="999.00")  # another tenant's gig

    assert services.gig_balance(gig).fees == 0


def test_the_pages_show_the_two_lines_and_the_warning(client):
    gig = make_gig()
    client.force_login(MembershipFactory(tenant=gig.tenant).user)
    GigMemberFactory(gig=gig, cachet_amount="100.00")
    ExpenseFactory(gig=gig, category=Expense.Category.FEES, amount="30.00")

    for url in (reverse("gigs:detail", args=[gig.pk]), reverse("finance:page", args=[gig.pk])):
        text = client.get(url).content.decode()
        assert "Cachets (depuis Social, estimé)" in text
        assert "Coût employeur estimé" in text
        assert "dont dépenses saisies" in text
        assert "comptés deux fois" in text


def test_another_tenant_gets_404_on_the_pages(client):
    gig = make_gig()
    client.force_login(MembershipFactory().user)

    for url in (reverse("gigs:detail", args=[gig.pk]), reverse("finance:page", args=[gig.pk])):
        assert client.get(url).status_code == 404


def test_a_plain_member_never_sees_the_fees(client):
    gig = make_gig()
    client.force_login(MembershipFactory(tenant=gig.tenant, role="member").user)
    GigMemberFactory(gig=gig, cachet_amount="777.00")

    for url in (reverse("gigs:detail", args=[gig.pk]), reverse("finance:page", args=[gig.pk])):
        text = client.get(url).content.decode()
        assert "777" not in text
        assert "Cachets (depuis Social" not in text
        assert "Coût employeur" not in text
        assert "145" not in text


def test_remaining_planned_and_real_come_from_the_same_two_functions():
    gig = make_gig(price="1000.00")
    ExpenseFactory(gig=gig, amount="50.10")

    balance = services.gig_balance(gig)

    assert balance.remaining_planned == services.remaining_planned(D("1000.00"), D("50.10"))
    assert balance.remaining_planned == D("949.90")  # price excl. tax, not incl. tax
    assert balance.result == services.remaining_real(balance.received, balance.spent)
    assert balance.result == D("-50.10")


def test_employer_cost_is_an_estimation_to_the_cent_and_not_spent():
    gig = make_gig()  # default reference rate: 45 %
    GigMemberFactory(gig=gig, cachet_amount="100.55")

    balance = services.gig_balance(gig)

    assert balance.fees_employer_cost == D("145.80")  # 100.55 x 1.45 = 145.7975
    assert balance.spent == D("100.55")  # information only


def test_a_plain_member_gets_no_employer_cost():
    gig = make_gig()
    GigMemberFactory(gig=gig, cachet_amount="100.00")

    balance = services.gig_balance(gig, with_fees=False)

    assert balance.fees == 0
    assert balance.fees_employer_cost == 0


def test_the_expense_form_no_longer_offers_fees_for_a_new_expense():
    from ..forms import ExpenseForm

    gig = make_gig()
    form = ExpenseForm(tenant=gig.tenant)

    assert Expense.Category.FEES not in [value for value, _ in form.fields["category"].choices]


def test_an_old_fees_expense_stays_editable_and_flagged():
    from ..forms import ExpenseForm

    gig = make_gig()
    old = ExpenseFactory(gig=gig, category=Expense.Category.FEES, amount="100.00")
    GigMemberFactory(gig=gig, cachet_amount="100.00")

    form = ExpenseForm(instance=old, tenant=gig.tenant)

    assert Expense.Category.FEES in [value for value, _ in form.fields["category"].choices]
    assert services.gig_balance(gig).fees_double_count
    old.refresh_from_db()
    assert old.amount == D("100.00")  # kept, never deleted


def test_posting_a_new_fees_expense_is_refused(client):
    gig = make_gig()
    client.force_login(MembershipFactory(tenant=gig.tenant).user)

    client.post(
        reverse("finance:expense-add", args=[gig.pk]),
        {"category": "fees", "label": "Cachet", "amount": "50.00", "date": "2026-11-01"},
    )

    assert not Expense.objects.filter(gig=gig).exists()
