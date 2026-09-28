import pytest

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.tenants.factories import TenantFactory

from ..factories import ContactFactory, PromoterFactory, VenueFactory
from ..models import Contact, Promoter, Venue

mark_isolation_tested(Promoter)
mark_isolation_tested(Venue)
mark_isolation_tested(Contact)

pytestmark = pytest.mark.django_db


def test_promoters_do_not_mix_between_tenants():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    promoter_a = PromoterFactory(tenant=tenant_a)
    PromoterFactory(tenant=tenant_b)

    assert list(Promoter.objects.filter(tenant=tenant_a)) == [promoter_a]


def test_venues_do_not_mix_between_tenants():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    venue_a = VenueFactory(tenant=tenant_a)
    VenueFactory(tenant=tenant_b)

    assert list(Venue.objects.filter(tenant=tenant_a)) == [venue_a]


def test_contacts_do_not_mix_between_tenants():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    promoter_a = PromoterFactory(tenant=tenant_a)
    promoter_b = PromoterFactory(tenant=tenant_b)
    contact_a = ContactFactory(tenant=tenant_a, promoter=promoter_a)
    ContactFactory(tenant=tenant_b, promoter=promoter_b)

    assert list(Contact.objects.filter(tenant=tenant_a)) == [contact_a]
