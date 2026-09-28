import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from ..factories import ContactFactory, PromoterFactory, VenueFactory
from ..models import Contact

pytestmark = pytest.mark.django_db


def test_contact_can_belong_to_a_promoter():
    contact = ContactFactory(venue=None)

    assert contact.promoter is not None
    assert contact.venue is None


def test_contact_can_belong_to_a_venue():
    contact = ContactFactory(promoter=None, venue=VenueFactory())

    assert contact.venue is not None
    assert contact.promoter is None


def test_contact_without_a_promoter_or_a_venue_is_rejected():
    contact = ContactFactory.build(promoter=None, venue=None)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            contact.save()


def test_contact_with_both_a_promoter_and_a_venue_is_rejected():
    promoter = PromoterFactory()
    venue = VenueFactory(tenant=promoter.tenant)
    contact = ContactFactory.build(promoter=promoter, venue=venue, tenant=promoter.tenant)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            contact.save()


def test_contact_tenant_must_match_its_promoters_tenant():
    promoter = PromoterFactory()
    other_tenant = PromoterFactory().tenant
    contact = Contact(name="Une personne", promoter=promoter, tenant=other_tenant)

    with pytest.raises(ValidationError):
        contact.full_clean()


def test_contact_tenant_must_match_its_venues_tenant():
    venue = VenueFactory()
    contact = Contact(name="Une personne", venue=venue, tenant=PromoterFactory().tenant)

    with pytest.raises(ValidationError):
        contact.full_clean()
