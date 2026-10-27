"""Contacts of a lodging or a meal: edited by the owner, shown on the public page and the PDF."""

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

from ..factories import LodgingFactory, MealFactory, PlaceContactFactory, RoadmapFactory
from ..models import PlaceContact
from ..services import get_or_create_roadmap, public_context, publish, render_roadmap_pdf

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def tenant(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


@pytest.fixture
def roadmap(tenant):
    return get_or_create_roadmap(GigFactory(tenant=tenant))


def _add(client, roadmap, section, place, **data):
    url = reverse("roadmaps:contact-add", args=[roadmap.gig.pk, section, place.pk])
    return client.post(
        url, {"name": "Accueil", "role": "Réception", "phone": "04 67 11 22 33", **data}
    )


# --- the owner ------------------------------------------------------------------------------


def test_a_contact_is_added_to_a_lodging(client, roadmap):
    lodging = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant)

    response = _add(client, roadmap, "hebergements", lodging)

    assert response.status_code == 302
    contact = PlaceContact.objects.get()
    assert contact.lodging == lodging and contact.meal is None and contact.tenant == roadmap.tenant
    assert (contact.name, contact.role, contact.phone) == ("Accueil", "Réception", "04 67 11 22 33")


def test_a_contact_is_added_to_a_meal_and_several_to_the_same_place(client, roadmap):
    meal = MealFactory(roadmap=roadmap, tenant=roadmap.tenant)

    _add(client, roadmap, "repas", meal, name="Traiteur")
    _add(client, roadmap, "repas", meal, name="Cuisine")

    assert [c.name for c in meal.contacts.all()] == ["Traiteur", "Cuisine"]


def test_the_name_is_required(client, roadmap):
    lodging = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant)

    _add(client, roadmap, "hebergements", lodging, name="")

    assert not PlaceContact.objects.exists()


def test_a_contact_is_removed(client, roadmap):
    lodging = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant)
    contact = PlaceContactFactory(lodging=lodging)

    client.post(
        reverse(
            "roadmaps:contact-delete", args=[roadmap.gig.pk, "hebergements", lodging.pk, contact.pk]
        )
    )

    assert not PlaceContact.objects.exists()


def test_the_editor_shows_the_contacts_and_the_add_form(client, roadmap):
    lodging = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant)
    PlaceContactFactory(lodging=lodging, name="Mme Garcia")

    page = client.get(reverse("roadmaps:editor", args=[roadmap.gig.pk])).content.decode()

    assert "Mme Garcia" in page and "Ajouter un contact" in page
    assert f'id="contact-hebergements-{lodging.pk}-name"' in page


def test_a_change_of_contact_bumps_the_version_of_a_shared_roadmap(client, roadmap):
    lodging = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant)
    publish(roadmap)
    roadmap.refresh_from_db()
    before = roadmap.version

    _add(client, roadmap, "hebergements", lodging)

    roadmap.refresh_from_db()
    assert roadmap.version == before + 1


def test_a_section_without_contacts_is_refused(client, roadmap):
    url = reverse("roadmaps:contact-add", args=[roadmap.gig.pk, "hebergements", 1])
    assert client.post(url.replace("hebergements", "creneaux")).status_code == 404


# --- isolation ------------------------------------------------------------------------------


def test_another_structure_cannot_add_or_remove_a_contact(client, roadmap):
    lodging = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant)
    contact = PlaceContactFactory(lodging=lodging)
    other = MembershipFactory()
    client.force_login(other.user)

    added = _add(client, roadmap, "hebergements", lodging)
    removed = client.post(
        reverse(
            "roadmaps:contact-delete", args=[roadmap.gig.pk, "hebergements", lodging.pk, contact.pk]
        )
    )

    assert added.status_code == 404 and removed.status_code == 404
    assert PlaceContact.objects.count() == 1


def test_a_contact_of_another_lodging_cannot_be_removed_through_this_one(client, roadmap):
    mine = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant)
    other_lodging = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant)
    contact = PlaceContactFactory(lodging=other_lodging)

    response = client.post(
        reverse(
            "roadmaps:contact-delete", args=[roadmap.gig.pk, "hebergements", mine.pk, contact.pk]
        )
    )

    assert response.status_code == 404 and PlaceContact.objects.exists()


def test_a_contact_belongs_to_exactly_one_place():
    roadmap = RoadmapFactory()
    lodging = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant)
    meal = MealFactory(roadmap=roadmap, tenant=roadmap.tenant)

    with pytest.raises(IntegrityError), transaction.atomic():
        PlaceContact.objects.create(tenant=roadmap.tenant, name="X", lodging=lodging, meal=meal)
    with pytest.raises(IntegrityError), transaction.atomic():
        PlaceContact.objects.create(tenant=roadmap.tenant, name="X")


# --- what the reader sees -------------------------------------------------------------------


def test_the_public_page_shows_the_contacts_with_a_call_button(client, roadmap):
    lodging = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant, name="Hôtel Mistral")
    meal = MealFactory(roadmap=roadmap, tenant=roadmap.tenant)
    PlaceContactFactory(
        lodging=lodging, name="Mme Garcia", role="Réception", phone="04 67 11 22 33"
    )
    PlaceContactFactory(lodging=None, meal=meal, tenant=roadmap.tenant, name="Traiteur Dupont")
    publish(roadmap)
    roadmap.refresh_from_db()
    client.logout()

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()

    assert "Mme Garcia" in page and "Réception" in page and 'href="tel:0467112233"' in page
    assert "Traiteur Dupont" in page


def test_the_public_page_of_another_roadmap_never_shows_them(client, roadmap):
    PlaceContactFactory(
        lodging=LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant), name="Secret Garcia"
    )
    other = get_or_create_roadmap(GigFactory())
    publish(other)
    other.refresh_from_db()

    page = client.get(reverse("roadmap-public", args=[other.token])).content.decode()

    assert "Secret Garcia" not in page


def test_the_pdf_carries_the_contacts(roadmap):
    lodging = LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant)
    PlaceContactFactory(lodging=lodging, name="Mme Garcia")

    assert render_roadmap_pdf(roadmap).startswith(b"%PDF")
    assert [c.name for c in public_context(roadmap)["lodgings"][0].contacts.all()] == ["Mme Garcia"]
