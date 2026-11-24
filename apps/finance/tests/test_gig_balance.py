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
        assert "dont cachets (équipe)" in text
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
        assert "cachets (équipe)" not in text


def test_remaining_planned_and_real_come_from_the_same_two_functions():
    gig = make_gig(price="1000.00")
    ExpenseFactory(gig=gig, amount="50.10")

    balance = services.gig_balance(gig)

    assert balance.remaining_planned == services.remaining_planned(D("1000.00"), D("50.10"))
    assert balance.remaining_planned == D("949.90")  # price excl. tax, not incl. tax
    assert balance.result == services.remaining_real(balance.received, balance.spent)
    assert balance.result == D("-50.10")
