"""A contact works for any number of organisers and venues, or for none (the directory)."""

import pytest

from ..factories import ContactFactory, PromoterFactory, VenueFactory
from ..models import Contact

pytestmark = pytest.mark.django_db


def test_a_contact_can_work_for_a_promoter():
    contact = ContactFactory(venue=None)

    assert contact.promoters.count() == 1 and contact.venues.count() == 0


def test_a_contact_can_work_for_a_venue():
    contact = ContactFactory(promoter=None, venue=VenueFactory())

    assert contact.venues.count() == 1 and contact.promoters.count() == 0


def test_a_contact_can_work_for_several_promoters_and_several_venues_at_once():
    first = PromoterFactory()
    contact = ContactFactory(promoter=first, tenant=first.tenant)

    contact.promoters.add(PromoterFactory(tenant=first.tenant))
    contact.venues.add(VenueFactory(tenant=first.tenant), VenueFactory(tenant=first.tenant))

    assert contact.promoters.count() == 2 and contact.venues.count() == 2
    assert len(contact.attachments) == 4


def test_a_contact_can_have_no_attachment_at_all():
    """The address book is a directory: a person is kept even before any organiser or venue."""
    contact = ContactFactory(promoter=None, venue=None, tenant=PromoterFactory().tenant)

    contact.refresh_from_db()
    assert contact.attachments == []


def test_the_same_promoter_can_have_several_contacts_and_the_reverse_link_works():
    promoter = PromoterFactory()
    first = ContactFactory(promoter=promoter, tenant=promoter.tenant, name="A")
    second = ContactFactory(promoter=promoter, tenant=promoter.tenant, name="B")

    assert list(promoter.contacts.order_by("name")) == [first, second]


def test_deleting_a_promoter_keeps_its_contacts():
    promoter = PromoterFactory()
    contact = ContactFactory(promoter=promoter, tenant=promoter.tenant)

    promoter.delete()

    assert Contact.objects.filter(pk=contact.pk).exists()
    assert contact.promoters.count() == 0


def test_deleting_a_venue_keeps_its_contacts():
    venue = VenueFactory()
    contact = ContactFactory(promoter=None, venue=venue, tenant=venue.tenant)

    venue.delete()

    assert Contact.objects.filter(pk=contact.pk).exists()
    assert contact.venues.count() == 0


def test_a_venue_can_work_with_several_promoters_and_the_reverse_link_works():
    venue = VenueFactory()
    first = PromoterFactory(tenant=venue.tenant)
    second = PromoterFactory(tenant=venue.tenant)

    venue.promoters.add(first, second)

    assert set(venue.promoters.all()) == {first, second}
    assert list(first.venues.all()) == [venue] and list(second.venues.all()) == [venue]
