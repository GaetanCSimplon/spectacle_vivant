from decimal import Decimal

import pytest

from apps.finance.services import estimated_employer_cost
from apps.tenants.factories import TenantFactory
from apps.tenants.forms import TenantProfileForm
from apps.tenants.models import Tenant


@pytest.mark.parametrize(
    ("gross", "rate", "expected"),
    [
        ("100.00", "0.45", "145.00"),
        ("123.45", "0.45", "179.0025"),  # rounded below
        ("100.00", "0.50", "150.00"),
        ("0", "0.45", "0.00"),
    ],
)
def test_the_estimate_is_gross_plus_the_rate_to_the_cent(gross, rate, expected):
    result = estimated_employer_cost(Decimal(gross), Decimal(rate))

    assert result == Decimal(expected).quantize(Decimal("0.01"))


def test_no_gross_means_no_estimate():
    assert estimated_employer_cost(None, Decimal("0.45")) is None


@pytest.mark.django_db
def test_the_default_rate_is_45_percent():
    assert Tenant.objects.create(name="X").employer_cost_rate == Decimal("0.45")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("rate", "valid"), [("0.50", True), ("0", True), ("-0.1", False), ("1.5", False)]
)
def test_the_rate_is_bounded(rate, valid):
    data = {
        "name": "C",
        "vat_regime": "franchise",
        "quote_validity_days": 30,
        "payment_term_days": 30,
        "employer_cost_rate": rate,
    }
    form = TenantProfileForm(data, instance=Tenant(name="C"))

    assert ("employer_cost_rate" not in form.errors) is valid


@pytest.mark.django_db
def test_changing_one_tenant_rate_leaves_the_others_alone():
    a, b = TenantFactory(), TenantFactory()
    a.employer_cost_rate = Decimal("0.60")
    a.save()

    b.refresh_from_db()
    assert b.employer_cost_rate == Decimal("0.45")
