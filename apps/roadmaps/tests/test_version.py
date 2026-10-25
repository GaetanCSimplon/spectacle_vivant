"""Version and last update of a shared roadmap: +1 at each saved change while sharing is on."""

import datetime

import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.tenants.factories import MembershipFactory, PersonFactory

from ..factories import MealFactory
from ..services import get_or_create_roadmap, publish

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def gig(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return GigFactory(tenant=membership.tenant, performance_time=datetime.time(21, 0))


def _url(name, gig, *args):
    return reverse(f"roadmaps:{name}", args=[gig.pk, *args])


def _version(gig):
    roadmap = get_or_create_roadmap(gig)
    roadmap.refresh_from_db()
    return roadmap.version


def test_a_new_roadmap_starts_at_version_one_without_an_update_date(gig):
    roadmap = get_or_create_roadmap(gig)

    assert roadmap.version == 1 and roadmap.updated_at is None


def test_the_first_sharing_shows_version_one_with_its_date(gig):
    roadmap = get_or_create_roadmap(gig)

    publish(roadmap)

    roadmap.refresh_from_db()
    assert roadmap.version == 1 and roadmap.updated_at is not None


def test_changes_before_the_first_sharing_do_not_count(client, gig):
    client.post(_url("item-add", gig, "repas"), {"place": "Brasserie"})
    client.post(_url("notes", gig), {"notes": "Parking derrière"})

    assert _version(gig) == 1
    assert get_or_create_roadmap(gig).updated_at is None


def test_each_saved_change_while_shared_adds_one(client, gig):
    publish(get_or_create_roadmap(gig))
    meal = MealFactory(roadmap=get_or_create_roadmap(gig), tenant=gig.tenant)
    member = GigMemberFactory(gig=gig)
    person = PersonFactory(tenant=gig.tenant)

    client.post(_url("item-add", gig, "repas"), {"place": "Brasserie"}, **HTMX)
    assert _version(gig) == 2
    client.post(_url("item-edit", gig, "repas", meal.pk), {"place": "Chez Paul"}, **HTMX)
    assert _version(gig) == 3
    client.post(_url("item-delete", gig, "equipe", member.pk), **HTMX)
    assert _version(gig) == 4
    client.post(_url("notes", gig), {"notes": "Parking derrière"}, **HTMX)
    assert _version(gig) == 5
    client.post(_url("team-add", gig), {"person": person.pk}, **HTMX)
    assert _version(gig) == 6
    assert get_or_create_roadmap(gig).updated_at is not None


def test_a_refused_form_does_not_change_the_version(client, gig):
    publish(get_or_create_roadmap(gig))

    client.post(_url("item-add", gig, "creneaux"), {"kind": "meal"}, **HTMX)  # no time

    assert _version(gig) == 1


def test_sharing_on_and_off_does_not_add_a_version(client, gig):
    client.post(_url("share", gig, "activer"))
    client.post(_url("share", gig, "arreter"))

    assert _version(gig) == 1


def test_the_public_page_shows_the_version_and_the_update_time(client, gig):
    roadmap = get_or_create_roadmap(gig)
    publish(roadmap)
    client.post(_url("notes", gig), {"notes": "Nouveau"}, **HTMX)
    roadmap.refresh_from_db()

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()

    assert "Version 2" in page and "mise à jour le" in page
