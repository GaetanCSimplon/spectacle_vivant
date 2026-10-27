import datetime

import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.tenants.factories import TenantFactory

from .. import services
from ..factories import ExpenseClaimFactory, ExpenseFactory
from ..models import Expense, ExpenseClaim, Payment
from .helpers import issued_invoice, make_gig

mark_isolation_tested(Payment)
mark_isolation_tested(Expense)
mark_isolation_tested(ExpenseClaim)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def test_expenses_do_not_mix_between_tenants():
    tenant_a, tenant_b = TenantFactory(), TenantFactory()
    expense_a = ExpenseFactory(gig__tenant=tenant_a)
    ExpenseFactory(gig__tenant=tenant_b)

    assert list(Expense.objects.filter(tenant=tenant_a)) == [expense_a]
    assert expense_a.tenant == expense_a.gig.tenant


def test_expense_claims_do_not_mix_between_tenants():
    tenant_a, tenant_b = TenantFactory(), TenantFactory()
    claim_a = ExpenseClaimFactory(gig__tenant=tenant_a)
    ExpenseClaimFactory(gig__tenant=tenant_b)

    assert list(ExpenseClaim.objects.filter(tenant=tenant_a)) == [claim_a]
    assert claim_a.tenant == claim_a.gig.tenant == claim_a.person.tenant


def test_payments_do_not_mix_between_tenants():
    invoice_a = issued_invoice(make_gig(price="100.00"))
    invoice_b = issued_invoice(make_gig(price="100.00"))
    payment_a = services.record_payment(
        invoice_a, "10.00", datetime.date.today(), Payment.Method.CASH
    )
    services.record_payment(invoice_b, "10.00", datetime.date.today(), Payment.Method.CASH)

    assert list(Payment.objects.filter(tenant=invoice_a.tenant)) == [payment_a]
    assert payment_a.tenant == payment_a.invoice.tenant


def test_balance_ignores_other_tenants_money():
    gig_a = make_gig(price="100.00")
    invoice_a = issued_invoice(gig_a)
    invoice_b = issued_invoice(make_gig(price="100.00"))
    today = datetime.date.today()
    services.record_payment(invoice_a, "30.00", today, Payment.Method.CASH)
    services.record_payment(invoice_b, "100.00", today, Payment.Method.CASH)
    ExpenseFactory(amount="5.00")

    balance = services.gig_balance(gig_a)

    assert balance.received == 30
    assert balance.spent == 0
