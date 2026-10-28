"""The "Nouveau contact" form of the address book: a person of the directory, with optional
organisers and venues."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import PromoterFactory, VenueFactory
from ..models import Contact

pytestmark = pytest.mark.django_db

URL = "addressbook:contact-create"


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def test_a_contact_can_be_created_for_an_organiser(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)

    response = client.post(
        reverse(URL), {"name": "Julien Blanc", "role": "Accueil", "promoters": [promoter.pk]}
    )

    contact = Contact.objects.get()
    assert contact.tenant == tenant and list(contact.promoters.all()) == [promoter]
    assert not contact.venues.exists()
    assert response.url == reverse("addressbook:contact-list")


def test_a_contact_can_work_for_several_organisers_and_venues(client):
    tenant = _login(client)
    first, second = PromoterFactory(tenant=tenant), PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)

    client.post(
        reverse(URL),
        {"name": "Sophie Garnier", "promoters": [first.pk, second.pk], "venues": [venue.pk]},
    )

    contact = Contact.objects.get()
    assert set(contact.promoters.all()) == {first, second} and list(contact.venues.all()) == [venue]


def test_a_contact_can_be_created_without_any_attachment(client):
    tenant = _login(client)

    response = client.post(reverse(URL), {"name": "Nouvelle rencontre"})

    assert response.status_code == 302
    contact = Contact.objects.get()
    assert contact.tenant == tenant and contact.attachments == []


def test_both_kinds_are_offered_but_only_this_tenants_objects(client):
    tenant = _login(client)
    PromoterFactory(tenant=tenant, name="Mairie A")
    VenueFactory(tenant=tenant, name="Salle B")
    PromoterFactory(name="Mairie étrangère")
    VenueFactory(name="Salle étrangère")

    content = client.get(reverse(URL)).content.decode()

    assert "Mairie A" in content and "Salle B" in content
    assert "étrangère" not in content


def test_another_tenants_organiser_or_venue_cannot_be_chosen(client):
    _login(client)
    foreign_promoter, foreign_venue = PromoterFactory(), VenueFactory()

    by_promoter = client.post(reverse(URL), {"name": "Pirate", "promoters": [foreign_promoter.pk]})
    by_venue = client.post(reverse(URL), {"name": "Pirate", "venues": [foreign_venue.pk]})

    assert by_promoter.status_code == 200 and by_venue.status_code == 200
    assert not Contact.objects.exists()


@pytest.mark.parametrize("value", ["abc", "999999", "-1"])
def test_a_made_up_choice_is_refused(client, value):
    tenant = _login(client)
    PromoterFactory(tenant=tenant)

    response = client.post(reverse(URL), {"name": "X", "promoters": [value]})

    assert response.status_code == 200
    assert not Contact.objects.exists()


def test_the_form_needs_a_login_and_the_contact_list_links_to_it(client):
    assert client.get(reverse(URL)).url.startswith(reverse("account_login"))
    _login(client)
    assert reverse(URL) in client.get(reverse("addressbook:contact-list")).content.decode()
