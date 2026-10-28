"""The address book can be exported as CSV, with the search and filters of the screen."""

import csv
import io

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import ContactFactory, PromoterFactory, VenueFactory

pytestmark = pytest.mark.django_db

ROUTES = ["promoter-export", "venue-export", "contact-export"]


@pytest.fixture
def tenant(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _rows(response):
    text = response.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text), delimiter=";"))


def test_the_contacts_file_lists_the_links_and_is_an_excel_friendly_attachment(client, tenant):
    promoter = PromoterFactory(tenant=tenant, name="Mairie de Sète")
    venue = VenueFactory(tenant=tenant, name="Salle des Arènes")
    contact = ContactFactory(
        tenant=tenant, promoter=promoter, venue=venue, name="Léa Durand", role="Accueil"
    )
    contact.promoters.add(PromoterFactory(tenant=tenant, name="Festival Été"))

    response = client.get(reverse("addressbook:contact-export"))

    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]
    assert response.content.startswith("﻿".encode())
    header, row = _rows(response)
    assert header == ["Nom", "Fonction", "E-mail", "Téléphone", "Organisateurs", "Lieux"]
    assert row[0] == "Léa Durand" and row[1] == "Accueil"
    assert set(row[4].split(" | ")) == {"Mairie de Sète", "Festival Été"}
    assert row[5] == "Salle des Arènes"


def test_the_venues_and_organisers_files(client, tenant):
    promoter = PromoterFactory(tenant=tenant, name="Mairie", city="Sète", follow_up="active")
    venue = VenueFactory(tenant=tenant, name="Halle", city="Sète", capacity=300)
    venue.promoters.add(promoter)
    ContactFactory(tenant=tenant, promoter=promoter, name="Paul Roux")

    venues = _rows(client.get(reverse("addressbook:venue-export")))
    promoters = _rows(client.get(reverse("addressbook:promoter-export")))

    assert venues[1][0] == "Halle" and venues[1][4] == "300" and venues[1][6] == "Mairie"
    assert promoters[1][0] == "Mairie" and promoters[1][6] == "Sète"
    assert promoters[1][1] == "Client actif" and promoters[1][9] == "Paul Roux"


def test_the_search_and_the_filters_of_the_screen_apply(client, tenant):
    ContactFactory(tenant=tenant, promoter=None, venue=None, name="Alice Martin")
    ContactFactory(tenant=tenant, promoter=None, venue=None, name="Bob Leroy")
    attached = ContactFactory(tenant=tenant, venue=None, name="Carla Petit")

    searched = _rows(client.get(reverse("addressbook:contact-export"), {"q": "alice"}))
    unattached = _rows(client.get(reverse("addressbook:contact-export"), {"link": "none"}))
    attached_only = _rows(client.get(reverse("addressbook:contact-export"), {"link": "promoters"}))

    assert [row[0] for row in searched[1:]] == ["Alice Martin"]
    assert {row[0] for row in unattached[1:]} == {"Alice Martin", "Bob Leroy"}
    assert [row[0] for row in attached_only[1:]] == [attached.name]


def test_a_cell_starting_like_a_formula_is_neutralised(client, tenant):
    ContactFactory(tenant=tenant, promoter=None, venue=None, name="=HYPERLINK(1)")

    rows = _rows(client.get(reverse("addressbook:contact-export")))

    assert rows[1][0] == "'=HYPERLINK(1)"


def test_an_empty_address_book_gives_only_the_header(client, tenant):
    for name in ROUTES:
        assert len(_rows(client.get(reverse(f"addressbook:{name}")))) == 1


@pytest.mark.parametrize("name", ROUTES)
def test_another_structures_data_is_never_exported(client, tenant, name):
    PromoterFactory(name="Mairie étrangère")
    VenueFactory(name="Salle étrangère")
    ContactFactory(name="Espion")

    content = client.get(reverse(f"addressbook:{name}")).content.decode()

    assert "étrangère" not in content and "Espion" not in content


@pytest.mark.parametrize("name", ROUTES)
def test_the_export_needs_a_login(client, name):
    response = client.get(reverse(f"addressbook:{name}"))

    assert response.status_code == 302 and response.url.startswith(reverse("account_login"))


def test_each_list_offers_the_export_with_its_current_filters(client, tenant):
    ContactFactory(tenant=tenant, promoter=None, venue=None)
    PromoterFactory(tenant=tenant)
    VenueFactory(tenant=tenant)

    contacts = client.get(reverse("addressbook:contact-list"), {"q": "a"}).content.decode()
    promoters = client.get(reverse("addressbook:promoter-list")).content.decode()
    venues = client.get(reverse("addressbook:venue-list")).content.decode()

    assert f"{reverse('addressbook:contact-export')}?q=a" in contacts
    assert reverse("addressbook:promoter-export") in promoters
    assert reverse("addressbook:venue-export") in venues
    assert "Exporter (CSV)" in contacts
