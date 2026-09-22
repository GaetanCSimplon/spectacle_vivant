import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.organizations.factories import OrganizationFactory

from ..factories import PromoterFactory, VenueFactory
from ..models import Promoter, Venue

mark_isolation_tested(Promoter)
mark_isolation_tested(Venue)

pytestmark = pytest.mark.django_db


def test_promoters_do_not_mix_between_organizations():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    promoter_a = PromoterFactory(organization=org_a)
    PromoterFactory(organization=org_b)

    assert list(Promoter.objects.filter(organization=org_a)) == [promoter_a]


def test_venues_do_not_mix_between_organizations():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    venue_a = VenueFactory(organization=org_a)
    VenueFactory(organization=org_b)

    assert list(Venue.objects.filter(organization=org_a)) == [venue_a]
