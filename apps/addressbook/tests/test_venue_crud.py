import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

from ..factories import ContactFactory, VenueFactory
from ..models import Venue
from .helpers import directory_url

pytestmark = pytest.mark.django_db


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {
        "name": "La Grande Salle",
        "address": "1 rue de la Musique\n69001 Lyon",
        "capacity": "300",
    }
    data.update(overrides)
    return data


def test_venue_list_requires_login(client):
    response = client.get(directory_url("venue"))

    assert response.status_code == 302


def test_venue_list_only_shows_the_current_tenants_venues(client):
    tenant = _login(client)
    VenueFactory(tenant=tenant, name="La mienne")
    VenueFactory(name="Une autre")

    content = client.get(directory_url("venue")).content.decode()

    assert "La mienne" in content
    assert "Une autre" not in content


def test_create_a_venue(client):
    tenant = _login(client)

    response = client.post(reverse("addressbook:venue-create"), _payload())

    assert response.status_code == 302
    venue = Venue.objects.get(name="La Grande Salle")
    assert venue.tenant == tenant
    assert response.url == reverse("addressbook:venue-detail", args=[venue.pk])


def test_name_is_required_to_create_a_venue(client):
    _login(client)

    response = client.post(reverse("addressbook:venue-create"), _payload(name=""))

    assert response.status_code == 200
    assert not Venue.objects.exists()


def test_venue_detail_shows_contacts_and_gigs(client):
    tenant = _login(client)
    venue = VenueFactory(tenant=tenant)
    ContactFactory(tenant=tenant, promoter=None, venue=venue, name="Julie Martin")
    gig = GigFactory(tenant=tenant, venue=venue)

    url = reverse("addressbook:venue-detail", args=[venue.pk])
    content = client.get(url).content.decode()

    assert "Julie Martin" in content
    assert gig.show.title in content


def test_venue_detail_of_another_tenant_returns_404(client):
    _login(client)
    other = VenueFactory()

    response = client.get(reverse("addressbook:venue-detail", args=[other.pk]))

    assert response.status_code == 404


def test_update_a_venue(client):
    tenant = _login(client)
    venue = VenueFactory(tenant=tenant, name="Ancien nom")

    response = client.post(
        reverse("addressbook:venue-update", args=[venue.pk]),
        _payload(name="Nouveau nom"),
    )

    assert response.status_code == 302
    assert response.url == reverse("addressbook:venue-detail", args=[venue.pk])
    venue.refresh_from_db()
    assert venue.name == "Nouveau nom"


def test_cannot_update_another_tenants_venue(client):
    _login(client)
    other = VenueFactory(name="Ancien nom")

    response = client.post(
        reverse("addressbook:venue-update", args=[other.pk]),
        _payload(name="Nouveau nom"),
    )

    assert response.status_code == 404
    other.refresh_from_db()
    assert other.name == "Ancien nom"


def test_delete_a_venue_without_gigs(client):
    tenant = _login(client)
    venue = VenueFactory(tenant=tenant)

    response = client.post(reverse("addressbook:venue-delete", args=[venue.pk]))

    assert response.status_code == 302
    assert not Venue.objects.filter(pk=venue.pk).exists()


def test_cannot_delete_a_venue_used_by_a_gig(client):
    tenant = _login(client)
    venue = VenueFactory(tenant=tenant)
    GigFactory(tenant=tenant, venue=venue)

    response = client.post(reverse("addressbook:venue-delete", args=[venue.pk]))

    assert response.status_code == 302
    assert Venue.objects.filter(pk=venue.pk).exists()
