import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.tenants.factories import TenantFactory

from ..factories import ShowFactory
from ..models import Show

mark_isolation_tested(Show)

pytestmark = pytest.mark.django_db


def test_shows_do_not_mix_between_tenants():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    show_a = ShowFactory(tenant=tenant_a)
    ShowFactory(tenant=tenant_b)

    shows_of_a = Show.objects.filter(tenant=tenant_a)

    assert list(shows_of_a) == [show_a]
