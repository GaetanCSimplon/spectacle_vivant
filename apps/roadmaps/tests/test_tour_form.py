"""The "Régie de tournée" screens (F-90): the organiser's public form and the owner's review."""

import datetime

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.addressbook.models import Contact
from apps.finance import dashboard
from apps.gigs.factories import GigFactory
from apps.roadmaps import tour_requests as tr
from apps.roadmaps.factories import RoadmapFactory
from apps.roadmaps.models import Lodging, Meal, RoadmapRequest
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db

SECRETS = ["7777.77", "CONDITIONS-SECRETES", "FACTURATION-SECRETE", "ORGANISATEUR-SECRET"]


def _gig(**kwargs):
    return GigFactory(
        price="7777.77",
        conditions="CONDITIONS-SECRETES",
        promoter__name="ORGANISATEUR-SECRET",
        promoter__billing_address="FACTURATION-SECRETE",
        show__title="Les Nocturnes",
        venue__name="Salle Polyvalente",
        date=datetime.date(2026, 12, 5),
        **kwargs,
    )


def _public(request):
    return reverse("tour-form-public", args=[request.token])


def _login(client, tenant=None, role="owner"):
    membership = MembershipFactory(role=role, **({"tenant": tenant} if tenant else {}))
    client.force_login(membership.user)
    return membership.tenant


# --- the organiser's page -----------------------------------------------------------------------


def test_the_page_opens_without_an_account_and_shows_only_what_the_organiser_knows(client):
    gig = _gig()
    request = tr.create_request(gig, None)

    response = client.get(_public(request))
    page = response.content.decode()

    assert response.status_code == 200
    assert gig.tenant.name in page
    assert "Les Nocturnes" in page and "Salle Polyvalente" in page
    assert "samedi 5 décembre 2026" in page
    for secret in SECRETS:
        assert secret not in page, secret
    assert 'type="file"' not in page


def test_the_page_is_kept_out_of_caches_search_engines_and_other_sites(client):
    request = tr.create_request(_gig(), None)

    response = client.get(_public(request))

    assert response["Cache-Control"] == "no-store"
    assert "noindex" in response["X-Robots-Tag"]
    assert response["Referrer-Policy"] == "same-origin"


def test_an_unknown_token_is_a_404(client):
    tr.create_request(_gig(), None)

    assert client.get(reverse("tour-form-public", args=["nope"])).status_code == 404
    assert (
        client.post(reverse("tour-form-public", args=["nope"]), {"remarks": "x"}).status_code == 404
    )


@pytest.mark.parametrize("how", ["expired", "revoked", "answered"])
def test_a_closed_link_says_so_and_takes_nothing(client, how):
    gig = _gig()
    request = tr.create_request(gig, None)
    if how == "expired":
        RoadmapRequest.objects.filter(pk=request.pk).update(
            expires_at=timezone.now() - datetime.timedelta(minutes=1)
        )
    elif how == "revoked":
        tr.revoke_request(gig)
    else:
        tr.submit_response(request, {"remarks": "déjà"})

    page = client.get(_public(request))
    posted = client.post(_public(request), {"remarks": "trop tard"})

    assert page.status_code == posted.status_code == 410
    assert gig.tenant.name in page.content.decode()
    request.refresh_from_db()
    assert request.response.get("remarks") != "trop tard"


def test_a_valid_answer_is_stored_and_the_link_is_used_up(client):
    gig = _gig(performance_time=datetime.time(20, 0))
    request = tr.create_request(gig, None)

    response = client.post(
        _public(request),
        {"get_in_time": "14:30", "meal_place": "Brasserie", "remarks": "Bonjour"},
    )

    assert response.status_code == 302
    assert response.url == reverse("tour-form-thanks")
    request.refresh_from_db()
    assert request.status == RoadmapRequest.Status.ANSWERED
    assert request.response == {
        "get_in_time": "14:30",
        "meal_place": "Brasserie",
        "remarks": "Bonjour",
    }
    assert client.post(_public(request), {"remarks": "second"}).status_code == 410
    assert "Merci" in client.get(response.url).content.decode()


def test_an_answer_changes_nothing_on_the_date_by_itself(client):
    gig = _gig(performance_time=datetime.time(20, 0))
    roadmap = RoadmapFactory(gig=gig, notes="Mes notes")
    request = tr.create_request(gig, None)

    client.post(
        _public(request), {"performance_time": "22:00", "remarks": "Hop", "meal_place": "X"}
    )

    gig.refresh_from_db()
    roadmap.refresh_from_db()
    assert gig.performance_time == datetime.time(20, 0)
    assert roadmap.notes == "Mes notes"
    assert not Meal.objects.exists() and not Lodging.objects.exists()


@pytest.mark.parametrize(
    "data, field",
    [
        ({}, None),
        ({"remarks": "   "}, None),
        ({"get_in_time": "25:99"}, "get_in_time"),
        ({"remarks": "x" * 2001}, "remarks"),
        ({"meal_place": "x" * 256}, "meal_place"),
        ({"contact_phone": "06 11 22 33 44"}, "contact_name"),
        ({"contact_role": "Technique"}, "contact_name"),
    ],
)
def test_a_wrong_answer_is_refused_and_the_link_stays_usable(client, data, field):
    request = tr.create_request(_gig(), None)

    response = client.post(_public(request), data)

    assert response.status_code == 200
    if field:
        assert field in response.context["form"].errors
    request.refresh_from_db()
    assert request.status == RoadmapRequest.Status.ACTIVE and request.response == {}


def test_the_form_cannot_choose_a_structure_or_a_date(client):
    gig = _gig()
    other = GigFactory()
    request = tr.create_request(gig, None)

    client.post(
        _public(request),
        {"remarks": "ok", "tenant": other.tenant_id, "gig": other.pk, "token": "x", "id": "1"},
    )

    request.refresh_from_db()
    assert request.response == {"remarks": "ok"}
    assert request.gig == gig and request.tenant == gig.tenant


def test_a_post_without_the_csrf_token_is_refused():
    request = tr.create_request(_gig(), None)
    strict = Client(enforce_csrf_checks=True)

    assert strict.post(_public(request), {"remarks": "x"}).status_code == 403


# --- the owner: the block in the editor ---------------------------------------------------------


def _editor(client, gig):
    return client.get(reverse("roadmaps:editor", args=[gig.pk])).content.decode()


def test_the_editor_offers_to_create_the_link_then_shows_it(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    assert "Envoyer une demande de régie" in _editor(client, gig)

    response = client.post(reverse("roadmaps:tour-request-create", args=[gig.pk]))

    assert response.status_code == 302
    request = tr.latest_request(gig)
    assert request.created_by is not None
    page = _editor(client, gig)
    assert f"http://testserver{_public(request)}" in page
    assert "Un lien est actif jusqu'au" in page


def test_a_new_link_replaces_the_one_waiting_and_a_link_can_be_cancelled(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    client.post(reverse("roadmaps:tour-request-create", args=[gig.pk]))
    first = tr.latest_request(gig)

    client.post(reverse("roadmaps:tour-request-create", args=[gig.pk]))
    first.refresh_from_db()
    assert first.status == RoadmapRequest.Status.REVOKED

    client.post(reverse("roadmaps:tour-request-revoke", args=[gig.pk]))
    assert "Le dernier lien a été annulé" in _editor(client, gig)


def test_the_editor_points_to_the_review_once_the_organiser_answered(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    tr.submit_response(tr.create_request(gig, None), {"remarks": "Hop"})

    page = _editor(client, gig)

    assert "L'organisateur a répondu le" in page
    assert reverse("roadmaps:tour-request-review", args=[gig.pk]) in page


@pytest.mark.parametrize("name", ["create", "revoke"])
def test_the_link_actions_only_accept_post(client, name):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    assert client.get(reverse(f"roadmaps:tour-request-{name}", args=[gig.pk])).status_code == 405


@pytest.mark.parametrize("name", ["create", "revoke", "review"])
def test_another_structure_gets_a_404(client, name):
    _login(client)
    foreign = GigFactory()
    tr.submit_response(tr.create_request(foreign, None), {"remarks": "secret"})
    url = reverse(f"roadmaps:tour-request-{name}", args=[foreign.pk])

    assert client.post(url).status_code == 404
    if name == "review":
        assert client.get(url).status_code == 404
    assert tr.latest_request(foreign).status == RoadmapRequest.Status.ANSWERED


def test_a_visitor_is_sent_to_login(client):
    gig = GigFactory()

    for name in ("create", "revoke", "review"):
        response = client.post(reverse(f"roadmaps:tour-request-{name}", args=[gig.pk]))
        assert response.status_code == 302 and "login" in response.url


# --- the owner: the review ----------------------------------------------------------------------


def _answered(client, **answer):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, performance_time=datetime.time(20, 0))
    tr.submit_response(tr.create_request(gig, None), answer)
    return gig


def _review(gig):
    return reverse("roadmaps:tour-request-review", args=[gig.pk])


def test_the_review_shows_what_was_answered_and_the_current_time(client):
    gig = _answered(client, performance_time="21:15", meal_place="Brasserie", remarks="Hop")

    page = client.get(_review(gig)).content.decode()

    assert "21:15" in page and "actuellement 20:00" in page
    assert "Brasserie" in page and "Hop" in page
    assert 'value="times"' in page and 'value="meal"' in page and 'value="remarks"' in page
    assert 'value="lodging"' not in page


def test_the_review_applies_only_what_is_ticked(client):
    gig = _answered(client, performance_time="21:15", meal_place="Brasserie", remarks="Hop")

    response = client.post(_review(gig), {"groups": ["meal"]})

    assert response.status_code == 302
    gig.refresh_from_db()
    assert gig.performance_time == datetime.time(20, 0)
    assert Meal.objects.get().place == "Brasserie"
    assert tr.latest_request(gig).status == RoadmapRequest.Status.REVIEWED
    assert "1 élément(s) appliqué(s)" in client.get(response.url).content.decode()


def test_ticking_nothing_keeps_the_answer_waiting(client):
    gig = _answered(client, remarks="Hop")

    response = client.post(_review(gig), {})

    assert response.status_code == 302 and response.url == _review(gig)
    assert tr.latest_request(gig).status == RoadmapRequest.Status.ANSWERED
    assert "Cochez au moins un élément" in client.get(response.url).content.decode()


def test_ignoring_changes_nothing(client):
    gig = _answered(client, performance_time="21:15", meal_place="X")

    client.post(_review(gig), {"ignore": "1", "groups": ["times", "meal"]})

    gig.refresh_from_db()
    assert gig.performance_time == datetime.time(20, 0)
    assert not Meal.objects.exists()
    assert tr.latest_request(gig).status == RoadmapRequest.Status.REVIEWED


def test_nothing_to_review_goes_back_to_the_editor(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    for method in (client.get, client.post):
        response = method(_review(gig))
        assert response.status_code == 302
        assert response.url == reverse("roadmaps:editor", args=[gig.pk])


def test_an_answer_already_reviewed_cannot_be_applied_twice(client):
    gig = _answered(client, meal_place="Brasserie")
    client.post(_review(gig), {"groups": ["meal"]})

    client.post(_review(gig), {"groups": ["meal"]})

    assert Meal.objects.count() == 1


def test_what_the_organiser_typed_is_escaped_on_the_review(client):
    gig = _answered(client, remarks="<script>alert(1)</script>", contact_name="<b>Eve</b>")

    page = client.get(_review(gig)).content.decode()

    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page and "&lt;b&gt;Eve&lt;/b&gt;" in page


def test_the_contact_goes_to_the_venue_of_this_date_only(client):
    gig = _answered(client, contact_name="Régisseur Rémi", contact_phone="06 11 22 33 44")

    client.post(_review(gig), {"groups": ["contact"]})

    contact = Contact.objects.get()
    assert contact.tenant == gig.tenant and list(contact.venues.all()) == [gig.venue]


# --- the Home reminder --------------------------------------------------------------------------


def test_a_waiting_answer_shows_on_the_home_alerts_until_it_is_reviewed(client):
    gig = _answered(client, remarks="Hop")

    alerts = dashboard.alerts(gig.tenant, datetime.date.today())

    assert any(
        reverse("roadmaps:tour-request-review", args=[gig.pk]) == a["url"] for a in alerts["items"]
    )
    client.post(_review(gig), {"ignore": "1"})
    assert not any(
        "régie de tournée" in a["text"]
        for a in dashboard.alerts(gig.tenant, datetime.date.today())["items"]
    )
