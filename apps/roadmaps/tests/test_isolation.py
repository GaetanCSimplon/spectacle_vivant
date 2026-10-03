import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.gigs.models import GigMember
from apps.tenants.factories import TenantFactory

from ..factories import LodgingFactory, MealFactory, RoadmapFactory, RoadmapSlotFactory
from ..models import Lodging, Meal, Roadmap, RoadmapSlot

pytestmark = pytest.mark.django_db

CASES = [
    (Roadmap, RoadmapFactory),
    (RoadmapSlot, RoadmapSlotFactory),
    (Lodging, LodgingFactory),
    (Meal, MealFactory),
    (GigMember, GigMemberFactory),
]

for _model, _factory in CASES:
    mark_isolation_tested(_model)


@pytest.mark.parametrize(("model", "factory"), CASES)
def test_objects_do_not_mix_between_tenants(model, factory):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    obj_a = factory(**_parent_kwargs(model, tenant_a))
    factory(**_parent_kwargs(model, tenant_b))

    assert list(model.objects.filter(tenant=tenant_a)) == [obj_a]
    assert obj_a.tenant == tenant_a


def _parent_kwargs(model, tenant):
    gig = GigFactory(tenant=tenant)
    if model in (Roadmap, GigMember):
        return {"gig": gig}
    return {"roadmap": RoadmapFactory(gig=gig)}
