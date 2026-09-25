import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.tenants.factories import TenantFactory

from ..factories import GigFactory
from ..models import Gig

mark_isolation_tested(Gig)

pytestmark = pytest.mark.django_db


def test_gigs_do_not_mix_between_tenants():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    gig_a = GigFactory(tenant=tenant_a)
    GigFactory(tenant=tenant_b)

    assert list(Gig.objects.filter(tenant=tenant_a)) == [gig_a]


def test_gig_related_objects_belong_to_the_same_tenant():
    gig = GigFactory()

    assert gig.show.tenant == gig.tenant
    assert gig.promoter.tenant == gig.tenant
    assert gig.venue.tenant == gig.tenant
