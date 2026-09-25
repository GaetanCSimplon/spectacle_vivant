import pytest

from ..factories import TenantFactory
from ..models import Tenant

pytestmark = pytest.mark.django_db


def test_contract_party_label_defaults_to_artist():
    tenant = TenantFactory()
    tenant.refresh_from_db()

    assert tenant.contract_party_label == Tenant.ContractPartyLabel.ARTIST
    assert tenant.contract_party_label == "artiste"


def test_contract_party_label_only_accepts_known_values():
    tenant = TenantFactory.build(contract_party_label="cedant")

    with pytest.raises(Exception, match="contract_party_label"):
        tenant.full_clean()
