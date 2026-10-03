import datetime

import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.gigs.models import GigMember
from apps.tenants.factories import MembershipFactory

from ..factories import LodgingFactory, MealFactory, RoadmapFactory, RoadmapSlotFactory
from ..models import Lodging, Meal, Roadmap, RoadmapSlot
from ..services import get_or_create_roadmap, publish

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def tenant(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


@pytest.fixture
def gig(tenant):
    return GigFactory(tenant=tenant, performance_time=datetime.time(21, 0))


def _url(name, gig, *args):
    return reverse(f"roadmaps:{name}", args=[gig.pk, *args])


# --- editor page -------------------------------------------------------------


def test_editor_creates_and_prefills_the_roadmap(client, gig):
    response = client.get(_url("editor", gig))

    assert response.status_code == 200
    assert gig.roadmap.slots.count() == 1
    assert "21:00" in response.content.decode()


def test_editor_lists_slots_sorted_by_time(client, gig):
    roadmap = get_or_create_roadmap(gig)
    RoadmapSlotFactory(roadmap=roadmap, time=datetime.time(8, 0), label="Très tôt")

    content = client.get(_url("editor", gig)).content.decode()

    assert content.index("Très tôt") < content.index("21:00")


def test_editor_shows_the_page_inside_the_gig_detail(client, gig):
    response = client.get(reverse("gigs:detail", args=[gig.pk]))

    assert _url("editor", gig) in response.content.decode()


# --- adding, editing, deleting ------------------------------------------------

ADD_CASES = [
    ("creneaux", {"kind": "meal", "time": "19:30", "label": "Dîner"}, RoadmapSlot),
    ("hebergements", {"name": "Hôtel du Lac", "address": "3 quai"}, Lodging),
    ("repas", {"place": "Brasserie", "time": "13:00"}, Meal),
    ("equipe", {"name": "Léa", "role": "Chant", "phone": "0601020304"}, GigMember),
]


@pytest.mark.parametrize(("section", "data", "model"), ADD_CASES)
def test_add_item_without_javascript_redirects(client, gig, tenant, section, data, model):
    response = client.post(_url("item-add", gig, section), data)

    assert response.status_code == 302
    assert response.url == _url("editor", gig)
    item = model.objects.get(**{k: v for k, v in data.items() if k != "time"})
    assert item.tenant == tenant


@pytest.mark.parametrize(("section", "data", "model"), ADD_CASES)
def test_add_item_with_htmx_returns_the_body_fragment(client, gig, section, data, model):
    response = client.post(_url("item-add", gig, section), data, **HTMX)

    assert response.status_code == 200
    assert 'id="roadmap-body"' in response.content.decode()
    assert "<html" not in response.content.decode()
    assert model.objects.exists()


def test_add_slot_needs_a_time(client, gig):
    get_or_create_roadmap(gig)
    count = RoadmapSlot.objects.count()

    response = client.post(_url("item-add", gig, "creneaux"), {"kind": "meal", "label": "x"})

    assert response.status_code == 200
    assert RoadmapSlot.objects.count() == count
    assert "errorlist" in response.content.decode()


def test_add_member_needs_a_name(client, gig):
    response = client.post(_url("item-add", gig, "equipe"), {"role": "Chant"}, **HTMX)

    assert response.status_code == 200
    assert not GigMember.objects.exists()
    assert "errorlist" in response.content.decode()


def test_form_cannot_choose_the_tenant_or_the_roadmap(client, gig, tenant):
    other = RoadmapFactory()

    client.post(
        _url("item-add", gig, "repas"),
        {"place": "Bistro", "tenant": other.tenant.pk, "roadmap": other.pk},
    )

    meal = Meal.objects.get()
    assert meal.tenant == tenant
    assert meal.roadmap == gig.roadmap


def test_edit_form_is_shown_with_the_values(client, gig):
    meal = MealFactory(roadmap=get_or_create_roadmap(gig), place="Chez Paul")

    response = client.get(_url("item-edit", gig, "repas", meal.pk), **HTMX)

    assert response.status_code == 200
    assert "Chez Paul" in response.content.decode()
    assert 'id="roadmap-body"' in response.content.decode()


def test_edit_item(client, gig):
    meal = MealFactory(roadmap=get_or_create_roadmap(gig), place="Chez Paul")

    response = client.post(_url("item-edit", gig, "repas", meal.pk), {"place": "Chez Marie"})

    assert response.status_code == 302
    meal.refresh_from_db()
    assert meal.place == "Chez Marie"


def test_edit_with_invalid_data_keeps_the_item(client, gig):
    meal = MealFactory(roadmap=get_or_create_roadmap(gig), place="Chez Paul")

    response = client.post(_url("item-edit", gig, "repas", meal.pk), {"place": ""}, **HTMX)

    assert response.status_code == 200
    assert "errorlist" in response.content.decode()
    meal.refresh_from_db()
    assert meal.place == "Chez Paul"


def test_delete_item(client, gig):
    member = GigMemberFactory(gig=gig)

    response = client.post(_url("item-delete", gig, "equipe", member.pk), **HTMX)

    assert response.status_code == 200
    assert not GigMember.objects.exists()


def test_delete_requires_post(client, gig):
    member = GigMemberFactory(gig=gig)

    assert client.get(_url("item-delete", gig, "equipe", member.pk)).status_code == 405
    assert GigMember.objects.exists()


def test_save_notes(client, gig):
    client.post(_url("notes", gig), {"notes": "Parking derrière la salle"})

    assert gig.roadmap.notes == "Parking derrière la salle"


# --- sharing -----------------------------------------------------------------


def test_activate_then_stop_sharing(client, gig):
    client.post(_url("share", gig, "activer"))
    roadmap = Roadmap.objects.get(gig=gig)
    assert roadmap.is_published
    token = roadmap.token

    page = client.get(_url("editor", gig)).content.decode()
    assert token in page
    assert "Arrêter le partage" in page

    client.post(_url("share", gig, "arreter"))
    roadmap.refresh_from_db()
    assert not roadmap.is_published
    assert roadmap.token == ""
    assert token not in client.get(_url("editor", gig)).content.decode()


def test_reactivating_gives_a_new_link(client, gig):
    client.post(_url("share", gig, "activer"))
    first = Roadmap.objects.get(gig=gig).token
    client.post(_url("share", gig, "arreter"))
    client.post(_url("share", gig, "activer"))

    assert Roadmap.objects.get(gig=gig).token != first


def test_share_requires_post(client, gig):
    assert client.get(_url("share", gig, "activer")).status_code == 405


def test_unknown_section_or_action_is_404(client, gig):
    assert client.get(f"/dates/{gig.pk}/feuille-de-route/inconnu/ajouter/").status_code == 404
    assert client.post(f"/dates/{gig.pk}/feuille-de-route/partage/detruire/").status_code == 404


# --- login and isolation ------------------------------------------------------


def _all_routes(gig, item_ids):
    routes = [("get", _url("editor", gig)), ("post", _url("notes", gig))]
    routes += [("post", _url("share", gig, a)) for a in ("activer", "arreter")]
    for section, pk in item_ids.items():
        routes += [
            ("post", _url("item-add", gig, section)),
            ("get", _url("item-edit", gig, section, pk)),
            ("post", _url("item-edit", gig, section, pk)),
            ("post", _url("item-delete", gig, section, pk)),
        ]
    return routes


def _items_of(gig):
    roadmap = get_or_create_roadmap(gig)
    return {
        "creneaux": RoadmapSlotFactory(roadmap=roadmap).pk,
        "hebergements": LodgingFactory(roadmap=roadmap).pk,
        "repas": MealFactory(roadmap=roadmap).pk,
        "equipe": GigMemberFactory(gig=gig).pk,
    }


def test_login_is_required_everywhere(client):
    gig = GigFactory()
    for method, url in _all_routes(gig, _items_of(gig)):
        response = getattr(client, method)(url)
        assert response.status_code == 302, url
        assert "/accounts/login/" in response.url, url


def test_other_tenant_gets_404_on_every_route(client, tenant):
    foreign_gig = GigFactory()  # belongs to another tenant
    items = _items_of(foreign_gig)
    publish(foreign_gig.roadmap)
    token = foreign_gig.roadmap.token

    for method, url in _all_routes(foreign_gig, items):
        assert getattr(client, method)(url, {"place": "x"}).status_code == 404, url

    foreign_gig.roadmap.refresh_from_db()
    assert foreign_gig.roadmap.token == token
    assert Meal.objects.count() == 1
    assert GigMember.objects.count() == 1


def test_an_item_is_only_reachable_through_its_own_gig(client, tenant, gig):
    other_gig = GigFactory(tenant=tenant)
    other_items = _items_of(other_gig)

    for section, pk in other_items.items():
        assert client.get(_url("item-edit", gig, section, pk)).status_code == 404
        assert client.post(_url("item-delete", gig, section, pk)).status_code == 404
    assert Meal.objects.count() == 1
    assert GigMember.objects.count() == 1
    assert RoadmapSlot.objects.filter(roadmap__gig=other_gig).exists()
