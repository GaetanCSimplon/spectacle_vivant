"""The directory tells organisers, venues and contacts apart: coloured tags with their details."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import ContactFactory, PromoterFactory, VenueFactory
from ..models import Contact

pytestmark = pytest.mark.django_db

LIST = "addressbook:contact-list"


@pytest.fixture
def tenant(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _page(client):
    return client.get(reverse(LIST)).content.decode()


def test_initials_come_from_the_first_and_last_words():
    assert Contact(name="anna costa").initials == "AC"
    assert Contact(name="Jean de la Fontaine").initials == "JF"
    assert Contact(name="Madonna").initials == "MA"
    assert Contact(name="  ").initials == "?"


def test_an_organiser_and_a_venue_get_their_own_tag_class_and_a_word_for_screen_readers(
    client, tenant
):
    promoter = PromoterFactory(tenant=tenant, name="Mairie de Sète")
    venue = VenueFactory(tenant=tenant, name="Salle des Arènes")
    contact = ContactFactory(tenant=tenant, promoter=promoter, venue=venue)

    page = _page(client)

    assert contact.name in page
    assert "entity-promoter" in page and "entity-venue" in page
    assert "Organisateur :" in page and "Lieu :" in page
    assert 'role="tooltip"' in page


def test_the_tooltip_shows_the_address_and_the_contacts(client, tenant):
    promoter = PromoterFactory(
        tenant=tenant,
        name="Mairie",
        billing_address="1 rue des Lilas",
        postal_code="34200",
        city="Sète",
    )
    ContactFactory(tenant=tenant, promoter=promoter, name="Julie Garnier")

    page = _page(client)

    assert "1 rue des Lilas" in page and "Sète" in page
    assert "Contacts : Julie Garnier" in page


def test_a_tooltip_without_address_or_contact_says_so(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant, address="", postal_code="", city="")
    venue.promoters.add(promoter)

    page = client.get(reverse("addressbook:promoter-detail", args=[promoter.pk])).content.decode()

    assert "Adresse non renseignée" in page and "Aucun contact" in page


def test_a_long_list_of_contacts_is_cut_after_four(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    for number in range(6):
        ContactFactory(tenant=tenant, promoter=promoter, name=f"Personne {number}")

    page = _page(client)

    assert "et 2 autre(s)" in page


def test_names_are_escaped_in_the_tag_and_the_tooltip(client, tenant):
    promoter = PromoterFactory(tenant=tenant, name="<script>alert(1)</script>")
    ContactFactory(tenant=tenant, promoter=promoter, name="<b>Pirate</b>")

    page = _page(client)

    assert "<script>alert(1)" not in page and "<b>Pirate</b>" not in page
    assert "&lt;script&gt;" in page


def test_the_legend_explains_the_colours(client, tenant):
    page = _page(client)

    assert 'aria-label="Légende des couleurs"' in page
    assert "Passez la souris sur une étiquette" in page


def test_another_tenants_details_never_appear_in_a_tooltip(client, tenant):
    foreign = PromoterFactory(name="Mairie étrangère", billing_address="9 rue secrète")
    ContactFactory(tenant=foreign.tenant, promoter=foreign, name="Espion")
    mine = PromoterFactory(tenant=tenant)
    ContactFactory(tenant=tenant, promoter=mine)

    page = _page(client)

    assert "étrangère" not in page and "secrète" not in page and "Espion" not in page


def test_the_organiser_and_venue_pages_use_the_same_tags(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant, name="Salle liée")
    venue.promoters.add(promoter)

    page = client.get(reverse("addressbook:promoter-detail", args=[promoter.pk])).content.decode()

    assert "entity-venue" in page and "Salle liée" in page
