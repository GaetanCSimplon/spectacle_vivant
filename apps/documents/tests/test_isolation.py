import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.tenants.factories import TenantFactory

from ..factories import ContractFactory
from ..models import Contract, ContractShareLink

mark_isolation_tested(Contract)
mark_isolation_tested(ContractShareLink)

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


def test_share_links_do_not_mix_between_tenants():
    from ..services import create_share_link, generate_contract_pdf

    tenant_a, tenant_b = TenantFactory(), TenantFactory()
    contract_a = ContractFactory(tenant=tenant_a, gig__tenant=tenant_a)
    ContractFactory(tenant=tenant_b, gig__tenant=tenant_b)
    generate_contract_pdf(contract_a.gig)
    link = create_share_link(contract_a, None)

    assert list(ContractShareLink.objects.filter(tenant=tenant_a)) == [link]
    assert not ContractShareLink.objects.filter(tenant=tenant_b).exists()
