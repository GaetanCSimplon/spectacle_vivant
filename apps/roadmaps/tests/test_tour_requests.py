"""The "Régie de tournée" form sent to an organiser (F-90): link life cycle and what applying an
answer does. The answer never reaches the date or its roadmap before the owner applies it."""

import datetime

import pytest
from django.utils import timezone

from apps.addressbook.models import Contact
from apps.gigs.factories import GigFactory
from apps.roadmaps import tour_requests as tr
from apps.roadmaps.factories import RoadmapFactory, RoadmapRequestFactory, RoadmapSlotFactory
from apps.roadmaps.models import Lodging, Meal, RoadmapRequest, RoadmapSlot
from apps.roadmaps.services import publish
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db

FULL = {
    "get_in_time": "14:30",
    "soundcheck_time": "17:00",
    "performance_time": "21:15",
    "access_notes": "Camion par le quai arrière, parking gratuit.",
    "meal_place": "Brasserie du coin",
    "meal_time": "19:00",
    "meal_notes": "6 couverts, 1 végétarien",
    "lodging_name": "Hôtel du Lac",
    "lodging_address": "3 quai du Lac, 69000 Lyon",
    "lodging_arrival_time": "23:00",
    "lodging_notes": "Petit-déjeuner à 9 h",
    "contact_name": "Régisseur Rémi",
    "contact_role": "Technique",
    "contact_phone": "06 11 22 33 44",
    "remarks": "Merci d'arriver avant 15 h.",
}


def _answered(gig=None, **response):
    gig = gig or GigFactory(performance_time=datetime.time(20, 0))
    request = tr.create_request(gig, None)
    return tr.submit_response(request, response or FULL)


# --- the link -----------------------------------------------------------------------------------


def test_a_link_is_secret_valid_for_a_week_and_made_by_the_user():
    membership = MembershipFactory()
    gig = GigFactory(tenant=membership.tenant)

    request = tr.create_request(gig, membership.user)
    other = tr.create_request(GigFactory(), None)

    assert len(request.token) >= 43 and request.token != other.token
    assert request.status == RoadmapRequest.Status.ACTIVE
    assert request.created_by == membership.user
    assert request.tenant == gig.tenant
    assert abs((request.expires_at - timezone.now()) - datetime.timedelta(days=7)) < (
        datetime.timedelta(minutes=1)
    )


def test_a_new_link_cancels_the_one_still_waiting():
    gig = GigFactory()
    first = tr.create_request(gig, None)

    second = tr.create_request(gig, None)

    first.refresh_from_db()
    assert first.status == RoadmapRequest.Status.REVOKED
    assert second.status == RoadmapRequest.Status.ACTIVE
    assert tr.latest_request(gig) == second


def test_a_new_link_leaves_an_answer_waiting_for_review_alone():
    gig = GigFactory()
    answered = _answered(gig)

    tr.create_request(gig, None)

    answered.refresh_from_db()
    assert answered.status == RoadmapRequest.Status.ANSWERED
    assert answered.response


def test_the_status_follows_the_dates():
    request = RoadmapRequestFactory()
    assert request.status == RoadmapRequest.Status.ACTIVE

    request.expires_at = timezone.now() - datetime.timedelta(seconds=1)
    assert request.status == RoadmapRequest.Status.EXPIRED

    request.revoked_at = timezone.now()
    assert request.status == RoadmapRequest.Status.REVOKED

    request.completed_at = timezone.now()
    assert request.status == RoadmapRequest.Status.ANSWERED

    request.reviewed_at = timezone.now()
    assert request.status == RoadmapRequest.Status.REVIEWED


def test_revoking_only_works_on_an_active_link():
    gig = GigFactory()
    assert tr.revoke_request(gig) is False  # nothing yet

    request = tr.create_request(gig, None)
    assert tr.revoke_request(gig) is True
    request.refresh_from_db()
    assert request.status == RoadmapRequest.Status.REVOKED
    assert tr.revoke_request(gig) is False  # already cancelled


def test_an_answered_link_cannot_be_revoked():
    gig = GigFactory()
    _answered(gig)

    assert tr.revoke_request(gig) is False


def test_an_unknown_token_finds_nothing():
    RoadmapRequestFactory(token="real")

    assert tr.find_request("real") is not None
    assert tr.find_request("fake") is None
    assert tr.find_request("") is None


# --- the answer ---------------------------------------------------------------------------------


def test_an_answer_keeps_only_the_known_fields_that_are_filled_in():
    request = tr.create_request(GigFactory(), None)

    answered = tr.submit_response(
        request,
        {
            "get_in_time": datetime.time(9, 5),
            "soundcheck_time": "",
            "performance_time": "not a time",
            "remarks": "  Bonjour  ",
            "tenant": 999,
            "gig": 999,
            "is_admin": "1",
        },
    )

    assert answered.response == {"get_in_time": "09:05", "remarks": "Bonjour"}
    assert answered.status == RoadmapRequest.Status.ANSWERED


def test_the_link_can_only_be_used_once():
    request = tr.create_request(GigFactory(), None)
    tr.submit_response(request, {"remarks": "premier"})

    with pytest.raises(tr.RequestClosed):
        tr.submit_response(request, {"remarks": "second"})

    request.refresh_from_db()
    assert request.response == {"remarks": "premier"}


@pytest.mark.parametrize("how", ["expired", "revoked"])
def test_a_closed_link_takes_no_answer(how):
    request = RoadmapRequestFactory()
    if how == "expired":
        request.expires_at = timezone.now() - datetime.timedelta(minutes=1)
    else:
        request.revoked_at = timezone.now()
    request.save()

    with pytest.raises(tr.RequestClosed):
        tr.submit_response(request, {"remarks": "trop tard"})

    request.refresh_from_db()
    assert request.response == {}


def test_nothing_reaches_the_date_before_the_owner_applies_it():
    gig = GigFactory(performance_time=datetime.time(20, 0))
    roadmap = RoadmapFactory(gig=gig, notes="Mes notes")

    _answered(gig)

    gig.refresh_from_db()
    roadmap.refresh_from_db()
    assert gig.performance_time == datetime.time(20, 0)
    assert roadmap.notes == "Mes notes"
    assert not Meal.objects.exists() and not Lodging.objects.exists()
    assert not Contact.objects.exists()


def test_the_review_lists_what_was_answered_by_group():
    answered = _answered(**{"get_in_time": "14:30", "meal_place": "Resto", "remarks": "Hop"})

    groups = {key: rows for key, _label, rows in tr.answered_groups(answered)}

    assert set(groups) == {"times", "meal", "remarks"}
    assert groups["times"] == [("Get in", "14:30")]


def test_pending_requests_are_the_answered_ones_not_yet_reviewed():
    gig = GigFactory()
    answered = _answered(gig)
    RoadmapRequestFactory(gig=GigFactory(tenant=gig.tenant))  # still waiting for an answer

    assert list(tr.pending_requests(gig.tenant)) == [answered]
    tr.ignore_response(answered)
    assert list(tr.pending_requests(gig.tenant)) == []


# --- applying -----------------------------------------------------------------------------------


def test_applying_everything_fills_the_date_and_its_roadmap():
    gig = GigFactory(performance_time=datetime.time(20, 0))
    roadmap = RoadmapFactory(gig=gig, notes="Mes notes")
    answered = _answered(gig)

    applied = tr.apply_response(answered, list(tr.GROUPS))

    assert applied == list(tr.GROUPS)
    gig.refresh_from_db()
    roadmap.refresh_from_db()
    assert (gig.get_in_time, gig.soundcheck_time, gig.performance_time) == (
        datetime.time(14, 30),
        datetime.time(17, 0),
        datetime.time(21, 15),
    )
    slots = {slot.kind: slot.time for slot in roadmap.slots.all()}
    assert slots == {
        RoadmapSlot.Kind.ARRIVAL: datetime.time(14, 30),
        RoadmapSlot.Kind.SOUNDCHECK: datetime.time(17, 0),
        RoadmapSlot.Kind.PERFORMANCE: datetime.time(21, 15),
    }
    assert roadmap.notes.startswith("Mes notes")
    assert "Accueil : Camion par le quai arrière" in roadmap.notes
    assert "Remarques : Merci d'arriver avant 15 h." in roadmap.notes
    meal = Meal.objects.get()
    assert (meal.roadmap, meal.place, meal.time) == (
        roadmap,
        "Brasserie du coin",
        datetime.time(19, 0),
    )
    assert meal.notes == "6 couverts, 1 végétarien"
    lodging = Lodging.objects.get()
    assert (lodging.roadmap, lodging.name, lodging.arrival_time) == (
        roadmap,
        "Hôtel du Lac",
        datetime.time(23, 0),
    )
    contact = Contact.objects.get()
    assert (contact.name, contact.role, contact.phone) == (
        "Régisseur Rémi",
        "Technique",
        "06 11 22 33 44",
    )
    assert list(contact.venues.all()) == [gig.venue]
    assert contact.tenant == gig.tenant


def test_only_the_chosen_groups_are_applied():
    gig = GigFactory(performance_time=datetime.time(20, 0))
    answered = _answered(gig)

    applied = tr.apply_response(answered, ["meal", "nonsense"])

    assert applied == ["meal"]
    gig.refresh_from_db()
    assert gig.performance_time == datetime.time(20, 0)  # times were not chosen
    assert Meal.objects.count() == 1
    assert not Lodging.objects.exists() and not Contact.objects.exists()


def test_applying_closes_the_answer_and_forgets_it():
    answered = _answered()

    tr.apply_response(answered, ["remarks"])

    answered.refresh_from_db()
    assert answered.status == RoadmapRequest.Status.REVIEWED
    assert answered.response == {}
    with pytest.raises(tr.RequestClosed):
        tr.apply_response(answered, ["remarks"])


def test_ignoring_changes_nothing_and_forgets_the_answer():
    gig = GigFactory(performance_time=datetime.time(20, 0))
    answered = _answered(gig)

    tr.ignore_response(answered)

    gig.refresh_from_db()
    answered.refresh_from_db()
    assert gig.performance_time == datetime.time(20, 0)
    assert not Meal.objects.exists()
    assert answered.status == RoadmapRequest.Status.REVIEWED and answered.response == {}


def test_an_existing_slot_is_moved_not_duplicated():
    gig = GigFactory()
    roadmap = RoadmapFactory(gig=gig)
    RoadmapSlotFactory(roadmap=roadmap, kind=RoadmapSlot.Kind.ARRIVAL, time=datetime.time(10, 0))
    answered = _answered(gig, get_in_time="13:00")

    tr.apply_response(answered, ["times"])

    assert roadmap.slots.filter(kind=RoadmapSlot.Kind.ARRIVAL).count() == 1
    assert roadmap.slots.get(kind=RoadmapSlot.Kind.ARRIVAL).time == datetime.time(13, 0)


def test_a_shared_roadmap_goes_up_one_version_once():
    gig = GigFactory()
    roadmap = RoadmapFactory(gig=gig)
    publish(roadmap)
    answered = _answered(gig)

    tr.apply_response(answered, list(tr.GROUPS))

    roadmap.refresh_from_db()
    assert roadmap.version == 2


def test_an_unshared_roadmap_keeps_its_version():
    gig = GigFactory()
    roadmap = RoadmapFactory(gig=gig)
    answered = _answered(gig)

    tr.apply_response(answered, list(tr.GROUPS))

    roadmap.refresh_from_db()
    assert roadmap.version == 1


def test_a_missing_name_gets_a_neutral_label():
    answered = _answered(meal_time="12:00", lodging_address="Rue X")

    tr.apply_response(answered, ["meal", "lodging"])

    assert Meal.objects.get().place == "Repas"
    assert Lodging.objects.get().name == "Hébergement"


def test_a_contact_without_a_name_is_not_created():
    answered = _answered(contact_phone="06 00 00 00 00")

    assert tr.apply_response(answered, ["contact"]) == ["contact"]
    assert not Contact.objects.exists()


def test_nothing_is_created_in_another_structure():
    gig = GigFactory()
    other = GigFactory()
    answered = _answered(gig)

    tr.apply_response(answered, list(tr.GROUPS))

    assert not Meal.objects.filter(tenant=other.tenant).exists()
    assert not Lodging.objects.filter(tenant=other.tenant).exists()
    assert not Contact.objects.filter(tenant=other.tenant).exists()
    assert Meal.objects.get().tenant == gig.tenant
