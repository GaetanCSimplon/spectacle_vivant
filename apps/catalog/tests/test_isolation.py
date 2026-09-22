import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.organizations.factories import OrganizationFactory

from ..factories import ShowFactory
from ..models import Show

mark_isolation_tested(Show)

pytestmark = pytest.mark.django_db


def test_shows_do_not_mix_between_organizations():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    show_a = ShowFactory(organization=org_a)
    ShowFactory(organization=org_b)

    shows_of_a = Show.objects.filter(organization=org_a)

    assert list(shows_of_a) == [show_a]
