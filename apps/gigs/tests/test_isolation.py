import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.tenants.factories import TenantFactory

from .. import services
from ..factories import GigFactory
from ..models import Gig, GigChecklist, PriceChange

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


mark_isolation_tested(PriceChange)
mark_isolation_tested(GigChecklist)


def test_price_changes_do_not_mix_between_tenants():
    gig_a = GigFactory(tenant=TenantFactory())
    gig_b = GigFactory(tenant=TenantFactory())
    change_a = services.change_price(gig_a, "900", None)
    services.change_price(gig_b, "800", None)

    assert list(PriceChange.objects.filter(tenant=gig_a.tenant)) == [change_a]
    assert list(PriceChange.objects.filter(gig=gig_b, tenant=gig_a.tenant)) == []


def test_changing_the_price_of_another_tenants_gig_finds_nothing():
    gig_b = GigFactory(tenant=TenantFactory())
    gig_b.tenant = TenantFactory()  # a caller holding a gig with the wrong tenant

    with pytest.raises(Gig.DoesNotExist):
        services.change_price(gig_b, "900", None)

    assert not PriceChange.objects.exists()
