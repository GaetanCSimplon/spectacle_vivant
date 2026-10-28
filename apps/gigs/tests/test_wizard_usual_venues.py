"""The date wizard proposes the usual venues of the chosen organiser first."""

import pytest
from django.urls import reverse

from apps.addressbook.factories import PromoterFactory, VenueFactory
from apps.catalog.factories import ShowFactory
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _until_venue_step(client, tenant, promoter):
    show = ShowFactory(tenant=tenant)
    client.post(reverse("gigs:wizard-show"), {"mode": "existing", "show": show.pk})
    client.post(reverse("gigs:wizard-promoter"), {"mode": "existing", "promoter": promoter.pk})


def test_the_organisers_venues_come_first_and_are_marked(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    VenueFactory(tenant=tenant, name="A Salle quelconque")
    usual = VenueFactory(tenant=tenant, name="Z Salle habituelle")
    usual.promoters.add(promoter)
    _until_venue_step(client, tenant, promoter)

    response = client.get(reverse("gigs:wizard-venue"))
    page = response.content.decode()

    assert page.index("Z Salle habituelle (lieu habituel)") < page.index("A Salle quelconque")


def test_without_a_usual_venue_the_order_is_alphabetical_and_nothing_is_marked(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    VenueFactory(tenant=tenant, name="B Salle")
    VenueFactory(tenant=tenant, name="A Salle")
    _until_venue_step(client, tenant, promoter)

    page = client.get(reverse("gigs:wizard-venue")).content.decode()

    assert page.index("A Salle") < page.index("B Salle") and "lieu habituel" not in page


def test_another_organisers_venue_is_not_marked(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    other = PromoterFactory(tenant=tenant)
    VenueFactory(tenant=tenant, name="Salle de l'autre").promoters.add(other)
    _until_venue_step(client, tenant, promoter)

    page = client.get(reverse("gigs:wizard-venue")).content.decode()

    assert "Salle de l&#x27;autre" in page or "Salle de l'autre" in page
    assert "lieu habituel" not in page


def test_a_venue_created_in_the_wizard_is_linked_to_the_chosen_organiser(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    _until_venue_step(client, tenant, promoter)

    response = client.post(
        reverse("gigs:wizard-venue"),
        {"mode": "new", "name": "Nouvelle salle", "address": "", "postal_code": "", "city": ""},
    )

    assert response.status_code == 302
    venue = tenant.venue_set.get(name="Nouvelle salle")
    assert list(venue.promoters.all()) == [promoter]


def test_choosing_an_existing_venue_does_not_change_its_links(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)
    _until_venue_step(client, tenant, promoter)

    client.post(reverse("gigs:wizard-venue"), {"mode": "existing", "venue": venue.pk})

    assert not venue.promoters.exists()


def test_the_choice_list_never_offers_another_structures_venue(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    foreign = VenueFactory(name="Salle étrangère")
    _until_venue_step(client, tenant, promoter)

    page = client.get(reverse("gigs:wizard-venue")).content.decode()
    response = client.post(reverse("gigs:wizard-venue"), {"mode": "existing", "venue": foreign.pk})

    assert "Salle étrangère" not in page and response.status_code == 200
