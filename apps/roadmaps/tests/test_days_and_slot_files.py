"""A roadmap over several days (FDR-02) and files attached to a slot (FDR-03)."""

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.roadmaps import documents as docs
from apps.roadmaps.factories import LodgingFactory, MealFactory, RoadmapFactory, RoadmapSlotFactory
from apps.roadmaps.models import RoadmapDocument, RoadmapSlot
from apps.roadmaps.services import build_program, program_days, public_context, publish
from apps.tenants import services as tenant_services
from apps.tenants.factories import MembershipFactory, PersonFactory

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4\n%fake but starts like a PDF\n"
CONCERT = datetime.date(2030, 7, 27)


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def roadmap():
    return RoadmapFactory(gig=GigFactory(date=CONCERT))


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _file_for(roadmap, slot, person=None, title="Billet"):
    return docs.add_document(
        roadmap,
        title=title,
        file=SimpleUploadedFile("f.pdf", PDF),
        kind="application/pdf",
        person=person,
        user=None,
        slot=slot,
    )


# --- several days (FDR-02) -----------------------------------------------------------------------


def test_an_item_without_a_day_is_on_the_day_of_the_concert(roadmap):
    RoadmapSlotFactory(roadmap=roadmap, time=datetime.time(19, 0), label="Concert")

    program = build_program(roadmap)

    assert [item.day for item in program] == [CONCERT]
    assert len(program_days(program, CONCERT)) == 1


def test_the_program_runs_by_day_then_by_time(roadmap):
    RoadmapSlotFactory(
        roadmap=roadmap,
        time=datetime.time(10, 0),
        label="Retour",
        day=CONCERT + datetime.timedelta(days=1),
    )
    RoadmapSlotFactory(roadmap=roadmap, time=datetime.time(21, 0), label="Concert")
    RoadmapSlotFactory(
        roadmap=roadmap,
        time=datetime.time(22, 0),
        label="Départ la veille",
        day=CONCERT - datetime.timedelta(days=1),
    )
    RoadmapSlotFactory(roadmap=roadmap, time=datetime.time(9, 0), label="Arrivée")

    days = program_days(build_program(roadmap), CONCERT)

    assert [d.day for d in days] == [
        CONCERT - datetime.timedelta(days=1),
        CONCERT,
        CONCERT + datetime.timedelta(days=1),
    ]
    assert [i.label for i in days[1].items] == ["Arrivée", "Concert"]
    assert [d.is_concert_day for d in days] == [False, True, False]


def test_a_meal_and_a_lodging_can_be_on_another_day(roadmap):
    tomorrow = CONCERT + datetime.timedelta(days=1)
    MealFactory(roadmap=roadmap, place="Brunch", time=datetime.time(11, 0), day=tomorrow)
    LodgingFactory(roadmap=roadmap, name="Hôtel", arrival_time=datetime.time(23, 30))

    days = program_days(build_program(roadmap), CONCERT)

    assert [(d.day, [i.kind for i in d.items]) for d in days] == [
        (CONCERT, ["lodging"]),
        (tomorrow, ["meal"]),
    ]


def test_a_meal_is_repeated_only_on_another_day_than_a_meal_slot(roadmap):
    RoadmapSlotFactory(roadmap=roadmap, kind="meal", time=datetime.time(13, 0), label="Déjeuner")
    MealFactory(roadmap=roadmap, place="Même heure", time=datetime.time(13, 0))
    MealFactory(
        roadmap=roadmap,
        place="Lendemain",
        time=datetime.time(13, 0),
        day=CONCERT + datetime.timedelta(days=1),
    )

    labels = [item.label for item in build_program(roadmap)]

    assert sum("Même heure" in label for label in labels) == 0
    assert sum("Lendemain" in label for label in labels) == 1


def test_the_public_page_titles_each_day_only_when_there_are_several(client, roadmap):
    publish(roadmap)
    RoadmapSlotFactory(roadmap=roadmap, label="Concert")
    url = reverse("roadmap-public", args=[roadmap.token])

    single = client.get(url).content.decode()
    RoadmapSlotFactory(roadmap=roadmap, label="Retour", day=CONCERT + datetime.timedelta(days=1))
    several = client.get(url).content.decode()

    assert "Programme de la journée" in single and "Jour du concert" not in single
    assert "Jour du concert" in several and "Retour" in several


def test_the_pdf_is_still_a_pdf_over_several_days(client, roadmap):
    publish(roadmap)
    RoadmapSlotFactory(roadmap=roadmap, label="Retour", day=CONCERT + datetime.timedelta(days=1))

    response = client.get(reverse("roadmap-public-pdf", args=[roadmap.token]))

    assert response.status_code == 200 and response.content.startswith(b"%PDF")


# --- the forms ----------------------------------------------------------


def test_the_owner_adds_a_slot_on_another_day(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=CONCERT)
    RoadmapFactory(gig=gig)

    response = client.post(
        reverse("roadmaps:item-add", args=[gig.pk, "creneaux"]),
        {"kind": "departure", "day": "2030-07-28", "time": "10:00", "label": "Retour"},
    )

    assert response.status_code == 302
    assert RoadmapSlot.objects.get().day == datetime.date(2030, 7, 28)


def test_a_day_far_from_the_concert_is_refused(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=CONCERT)
    RoadmapFactory(gig=gig)

    response = client.post(
        reverse("roadmaps:item-add", args=[gig.pk, "creneaux"]),
        {"kind": "other", "day": "2030-09-01", "time": "10:00"},
    )

    assert response.status_code == 200 and "au plus du concert" in response.content.decode()
    assert not RoadmapSlot.objects.exists()


def test_the_day_is_optional_and_a_day_14_days_away_is_accepted(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=CONCERT)
    RoadmapFactory(gig=gig)
    url = reverse("roadmaps:item-add", args=[gig.pk, "repas"])

    client.post(url, {"place": "Sans jour", "time": "12:00"})
    client.post(url, {"place": "Limite", "day": "2030-08-10", "time": "12:00"})

    from apps.roadmaps.models import Meal

    assert Meal.objects.get(place="Sans jour").day is None
    assert Meal.objects.get(place="Limite").day == datetime.date(2030, 8, 10)


# --- files on a slot (FDR-03) ------------------------------------------------


def test_the_owner_attaches_a_file_to_a_slot_of_this_date_only(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=CONCERT)
    roadmap = RoadmapFactory(gig=gig)
    slot = RoadmapSlotFactory(roadmap=roadmap, label="Train")
    foreign = RoadmapSlotFactory()

    ok = client.post(
        reverse("roadmaps:document-add", args=[gig.pk]),
        {"title": "Billet", "file": SimpleUploadedFile("b.pdf", PDF), "slot": slot.pk},
    )
    refused = client.post(
        reverse("roadmaps:document-add", args=[gig.pk]),
        {"title": "Pirate", "file": SimpleUploadedFile("b.pdf", PDF), "slot": foreign.pk},
    )

    assert ok.status_code == 302 and RoadmapDocument.objects.get().slot == slot
    assert refused.status_code == 200
    assert RoadmapDocument.objects.count() == 1


def test_the_shared_link_only_says_there_is_a_file_never_its_title_or_content(client, roadmap):
    publish(roadmap)
    slot = RoadmapSlotFactory(roadmap=roadmap, label="Train")
    _file_for(roadmap, slot, title="Billet Marie Dupont")

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()

    assert "Pièce jointe dans votre espace personnel" in page
    assert "Billet Marie Dupont" not in page
    assert all(not item.files for item in public_context(roadmap)["program"])


def test_a_person_sees_the_files_of_a_slot_that_are_for_them_under_the_slot(client):
    gig = GigFactory(date=CONCERT)
    roadmap = RoadmapFactory(gig=gig)
    slot = RoadmapSlotFactory(roadmap=roadmap, label="Train")
    marie = PersonFactory(tenant=gig.tenant)
    paul = PersonFactory(tenant=gig.tenant)
    for person in (marie, paul):
        tenant_services.enable_team_space(person)
        person.refresh_from_db()
        GigMemberFactory(gig=gig, person=person, name=person.full_name)
    _file_for(roadmap, slot, person=marie, title="Billet de Marie")
    _file_for(roadmap, slot, title="Plan pour tous")

    page_marie = client.get(reverse("team-space-gig", args=[marie.access_token, gig.pk]))
    page_paul = client.get(reverse("team-space-gig", args=[paul.access_token, gig.pk]))

    assert "Billet de Marie" in page_marie.content.decode()
    assert "Plan pour tous" in page_marie.content.decode()
    assert "Billet de Marie" not in page_paul.content.decode()
    assert "Plan pour tous" in page_paul.content.decode()


def test_a_slot_file_is_not_repeated_in_the_general_list(client):
    gig = GigFactory(date=CONCERT)
    roadmap = RoadmapFactory(gig=gig)
    slot = RoadmapSlotFactory(roadmap=roadmap, label="Train")
    person = PersonFactory(tenant=gig.tenant)
    tenant_services.enable_team_space(person)
    person.refresh_from_db()
    GigMemberFactory(gig=gig, person=person, name=person.full_name)
    _file_for(roadmap, slot, title="Billet unique")

    page = client.get(
        reverse("team-space-gig", args=[person.access_token, gig.pk])
    ).content.decode()

    assert page.count("Billet unique") == 1


def test_deleting_a_slot_deletes_its_files(roadmap, django_capture_on_commit_callbacks):
    slot = RoadmapSlotFactory(roadmap=roadmap)
    document = _file_for(roadmap, slot)
    name, storage = document.file.name, document.file.storage

    with django_capture_on_commit_callbacks(execute=True):
        slot.delete()

    assert not RoadmapDocument.objects.exists()
    assert not storage.exists(name)


def test_a_slot_of_another_structure_cannot_receive_a_file(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=CONCERT)
    RoadmapFactory(gig=gig)
    other = RoadmapSlotFactory()  # another structure's slot

    client.post(
        reverse("roadmaps:document-add", args=[gig.pk]),
        {"title": "X", "file": SimpleUploadedFile("b.pdf", PDF), "slot": other.pk},
    )

    assert not RoadmapDocument.objects.exists()
