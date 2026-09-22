import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.organizations.factories import OrganizationFactory

from ..factories import ContractFactory
from ..models import Contract

mark_isolation_tested(Contract)

pytestmark = pytest.mark.django_db


def test_contracts_do_not_mix_between_organizations():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    contract_a = ContractFactory(organization=org_a, gig__organization=org_a)
    ContractFactory(organization=org_b, gig__organization=org_b)

    assert list(Contract.objects.filter(organization=org_a)) == [contract_a]


def test_contract_organization_matches_its_gig():
    contract = ContractFactory()

    assert contract.organization == contract.gig.organization
