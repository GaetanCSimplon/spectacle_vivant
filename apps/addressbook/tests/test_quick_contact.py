"""The "Nouveau contact" form of the home page: the user picks the organiser or venue."""

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
        reverse(URL),
        {"parent": f"promoter:{promoter.pk}", "name": "Julien Blanc", "role": "Accueil"},
    )

    contact = Contact.objects.get()
    assert (contact.promoter, contact.venue, contact.tenant) == (promoter, None, tenant)
    assert response.url == promoter.get_absolute_url()


def test_a_contact_can_be_created_for_a_venue(client):
    tenant = _login(client)
    venue = VenueFactory(tenant=tenant)

    client.post(reverse(URL), {"parent": f"venue:{venue.pk}", "name": "Sophie Garnier"})

    contact = Contact.objects.get()
    assert (contact.venue, contact.promoter) == (venue, None)


def test_both_kinds_are_offered_but_only_this_tenants_objects(client):
    tenant = _login(client)
    PromoterFactory(tenant=tenant, name="Mairie A")
    VenueFactory(tenant=tenant, name="Salle B")
    PromoterFactory(name="Mairie étrangère")
    VenueFactory(name="Salle étrangère")

    content = client.get(reverse(URL)).content.decode()

    assert "Mairie A" in content and "Salle B" in content
    assert "étrangère" not in content


def test_another_tenants_organiser_cannot_be_chosen(client):
    _login(client)
    foreign = PromoterFactory()

    response = client.post(reverse(URL), {"parent": f"promoter:{foreign.pk}", "name": "Pirate"})

    assert response.status_code == 200
    assert not Contact.objects.exists()


@pytest.mark.parametrize("value", ["", "promoter:", "venue:abc", "other:1", "promoter:999999"])
def test_a_missing_or_made_up_parent_is_refused(client, value):
    tenant = _login(client)
    PromoterFactory(tenant=tenant)

    response = client.post(reverse(URL), {"parent": value, "name": "X"})

    assert response.status_code == 200
    assert not Contact.objects.exists()


def test_without_organiser_or_venue_the_page_explains_what_to_create_first(client):
    _login(client)
    content = client.get(reverse(URL)).content.decode()
    assert "Créez d" in content
    assert reverse("addressbook:promoter-create") in content
    assert reverse("addressbook:venue-create") in content


def test_the_form_needs_a_login_and_the_contact_list_links_to_it(client):
    assert client.get(reverse(URL)).url.startswith(reverse("account_login"))
    _login(client)
    assert reverse(URL) in client.get(reverse("addressbook:contact-list")).content.decode()
