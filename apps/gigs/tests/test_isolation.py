import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.organizations.factories import OrganizationFactory

from ..factories import GigFactory
from ..models import Gig

mark_isolation_tested(Gig)

pytestmark = pytest.mark.django_db


def test_gigs_do_not_mix_between_organizations():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    gig_a = GigFactory(organization=org_a)
    GigFactory(organization=org_b)

    assert list(Gig.objects.filter(organization=org_a)) == [gig_a]


def test_gig_related_objects_belong_to_the_same_organization():
    gig = GigFactory()

    assert gig.show.organization == gig.organization
    assert gig.promoter.organization == gig.organization
    assert gig.venue.organization == gig.organization
