"""The contact page is a directory: every contact, with where it works, or "Sans rattachement"."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import ContactFactory, PromoterFactory, VenueFactory
from ..models import Contact
from .helpers import list_get

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _page(client, **params):
    return list_get(client, "contact", params).content.decode()


def test_a_contact_of_two_organisers_is_listed_once_with_both(client, tenant):
    first = PromoterFactory(tenant=tenant, name="Festival A")
    second = PromoterFactory(tenant=tenant, name="Mairie B")
    contact = ContactFactory(tenant=tenant, promoter=first, name="Julie Garnier")
    contact.promoters.add(second)

    response = list_get(client, "contact")
    page = response.content.decode()

    assert len(response.context["object_list"]) == 1
    assert "Festival A" in page and "Mairie B" in page


def test_a_contact_without_attachment_says_so(client, tenant):
    ContactFactory(tenant=tenant, promoter=None, venue=None, name="Rencontre de salon")

    page = _page(client)

    assert "Rencontre de salon" in page and "Sans rattachement" in page


@pytest.mark.parametrize(
    ("link", "visible", "hidden"),
    [
        ("promoters", {"Pour organisateur"}, {"Pour lieu", "Libre"}),
        ("venues", {"Pour lieu"}, {"Pour organisateur", "Libre"}),
        ("none", {"Libre"}, {"Pour organisateur", "Pour lieu"}),
        ("", {"Pour organisateur", "Pour lieu", "Libre"}, set()),
    ],
)
def test_the_directory_can_be_filtered_by_attachment(client, tenant, link, visible, hidden):
    ContactFactory(tenant=tenant, promoter=PromoterFactory(tenant=tenant), name="Pour organisateur")
    ContactFactory(
        tenant=tenant, promoter=None, venue=VenueFactory(tenant=tenant), name="Pour lieu"
    )
    ContactFactory(tenant=tenant, promoter=None, venue=None, name="Libre")

    page = _page(client, link=link)

    assert all(name in page for name in visible)
    assert not any(name in page for name in hidden)


def test_an_unknown_filter_value_shows_everybody(client, tenant):
    ContactFactory(tenant=tenant, promoter=None, venue=None, name="Libre")

    assert "Libre" in _page(client, link="nope")


def test_the_search_finds_a_contact_by_its_organiser_or_venue_name(client, tenant):
    contact = ContactFactory(
        tenant=tenant, promoter=PromoterFactory(tenant=tenant, name="Festival des Lunes")
    )
    contact.venues.add(VenueFactory(tenant=tenant, name="Salle du Port"))
    ContactFactory(tenant=tenant, promoter=PromoterFactory(tenant=tenant), name="Autre")

    by_promoter = list_get(client, "contact", {"q": "Lunes"}).context["object_list"]
    by_venue = list_get(client, "contact", {"q": "Port"}).context["object_list"]

    assert list(by_promoter) == [contact] and list(by_venue) == [contact]


def test_a_search_matching_two_attachments_does_not_duplicate_the_contact(client, tenant):
    contact = ContactFactory(tenant=tenant, promoter=PromoterFactory(tenant=tenant, name="Ab 1"))
    contact.promoters.add(PromoterFactory(tenant=tenant, name="Ab 2"))

    results = list_get(client, "contact", {"q": "Ab"}).context["object_list"]

    assert list(results) == [contact]


def test_another_structures_contacts_never_appear(client, tenant):
    ContactFactory(name="Secret étranger")

    assert "Secret étranger" not in _page(client)
    assert "Secret étranger" not in _page(client, link="none")
    assert "Secret étranger" not in list_get(client, "contact", {"q": "Secret"}).content.decode()


def test_the_empty_directory_invites_to_add_a_first_contact(client, tenant):
    page = _page(client)

    assert "annuaire est vide" in page and reverse("addressbook:contact-create") in page


def test_an_empty_filter_result_is_not_the_empty_directory_message(client, tenant):
    ContactFactory(tenant=tenant, promoter=PromoterFactory(tenant=tenant))

    page = _page(client, link="none")

    assert "Aucun contact ne correspond" in page and "annuaire est vide" not in page


# --- the pages of an organiser and of a venue ----------------------------------------------


def test_the_organiser_page_lists_its_contacts_and_its_venues(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant, name="Salle des Fêtes")
    venue.promoters.add(promoter)
    ContactFactory(tenant=tenant, promoter=promoter, name="Contact liée")

    page = client.get(reverse("addressbook:promoter-detail", args=[promoter.pk])).content.decode()

    assert "Contact liée" in page and "Salle des Fêtes" in page
    assert reverse("addressbook:venue-detail", args=[venue.pk]) in page


def test_the_venue_page_lists_its_organisers_and_its_contacts(client, tenant):
    venue = VenueFactory(tenant=tenant)
    promoter = PromoterFactory(tenant=tenant, name="Festival des Lunes")
    venue.promoters.add(promoter)
    ContactFactory(tenant=tenant, promoter=None, venue=venue, name="Régisseur Paul")

    page = client.get(reverse("addressbook:venue-detail", args=[venue.pk])).content.decode()

    assert "Festival des Lunes" in page and "Régisseur Paul" in page


def test_a_contact_row_on_a_page_links_to_its_other_attachments(client, tenant):
    promoter = PromoterFactory(tenant=tenant, name="Festival A")
    other = PromoterFactory(tenant=tenant, name="Mairie B")
    contact = ContactFactory(tenant=tenant, promoter=promoter)
    contact.promoters.add(other)

    page = _page(client)

    assert reverse("addressbook:promoter-detail", args=[other.pk]) in page


# --- venues and organisers -------------------------------------------------------------------


def test_a_venue_is_linked_to_organisers_from_its_form(client, tenant):
    mine = PromoterFactory(tenant=tenant)
    other = PromoterFactory(tenant=tenant)

    client.post(
        reverse("addressbook:venue-create"), {"name": "Halle", "promoters": [mine.pk, other.pk]}
    )

    venue = tenant.venue_set.get()
    assert set(venue.promoters.all()) == {mine, other}


def test_a_venue_form_only_offers_and_accepts_this_structures_organisers(client, tenant):
    PromoterFactory(tenant=tenant, name="Mon organisateur")
    foreign = PromoterFactory(name="Organisateur étranger")

    page = client.get(reverse("addressbook:venue-create")).content.decode()
    response = client.post(
        reverse("addressbook:venue-create"), {"name": "Halle", "promoters": [foreign.pk]}
    )

    assert "Mon organisateur" in page and "Organisateur étranger" not in page
    assert response.status_code == 200 and not tenant.venue_set.exists()


def test_editing_a_venue_keeps_and_changes_its_organisers(client, tenant):
    venue = VenueFactory(tenant=tenant)
    first = PromoterFactory(tenant=tenant)
    second = PromoterFactory(tenant=tenant)
    venue.promoters.add(first)

    client.post(
        reverse("addressbook:venue-update", args=[venue.pk]),
        {"name": venue.name, "promoters": [second.pk]},
    )

    assert list(venue.promoters.all()) == [second]


def test_exports_carry_the_attachments(client, tenant):
    from apps.tenants.data_export import contacts_rows, venues_rows

    promoter = PromoterFactory(tenant=tenant, name="Festival A")
    venue = VenueFactory(tenant=tenant, name="Salle B")
    venue.promoters.add(promoter)
    contact = ContactFactory(tenant=tenant, promoter=promoter, name="Julie")
    contact.venues.add(venue)
    ContactFactory(tenant=tenant, promoter=None, venue=None, name="Libre")

    header, rows = contacts_rows(tenant)
    venue_header, venue_rows = venues_rows(tenant)

    by_name = {row[0]: dict(zip(header, row, strict=True)) for row in rows}
    assert (
        by_name["Julie"]["Organisateurs"] == "Festival A" and by_name["Julie"]["Lieux"] == "Salle B"
    )
    assert by_name["Libre"]["Organisateurs"] == "" and by_name["Libre"]["Lieux"] == ""
    assert dict(zip(venue_header, venue_rows[0], strict=True))["Organisateurs"] == "Festival A"


def test_a_contact_is_still_isolated_by_tenant(client, tenant):
    foreign = ContactFactory()

    assert client.get(reverse("addressbook:contact-update", args=[foreign.pk])).status_code == 404
    assert client.post(reverse("addressbook:contact-delete", args=[foreign.pk])).status_code == 404
    assert Contact.objects.filter(pk=foreign.pk).exists()
