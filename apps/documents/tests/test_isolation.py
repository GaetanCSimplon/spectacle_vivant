import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.tenants.factories import TenantFactory

from ..factories import ContractFactory
from ..models import Contract

mark_isolation_tested(Contract)

pytestmark = pytest.mark.django_db


def test_contracts_do_not_mix_between_tenants():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    contract_a = ContractFactory(tenant=tenant_a, gig__tenant=tenant_a)
    ContractFactory(tenant=tenant_b, gig__tenant=tenant_b)

    assert list(Contract.objects.filter(tenant=tenant_a)) == [contract_a]


def test_contract_tenant_matches_its_gig():
    contract = ContractFactory()

    assert contract.tenant == contract.gig.tenant
