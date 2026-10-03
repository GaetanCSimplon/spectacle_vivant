import datetime

import pytest
from django.db import IntegrityError, transaction

from apps.gigs.factories import GigFactory

from ..factories import RoadmapFactory
from ..models import Roadmap, RoadmapSlot
from ..services import get_or_create_roadmap, publish, revoke

pytestmark = pytest.mark.django_db


def test_prefill_from_gig_times():
    gig = GigFactory(
        get_in_time=datetime.time(15, 0),
        soundcheck_time=datetime.time(16, 30),
        performance_time=datetime.time(21, 0),
    )

    roadmap = get_or_create_roadmap(gig)

    assert roadmap.tenant == gig.tenant
    assert [(s.kind, s.time) for s in roadmap.slots.all()] == [
        (RoadmapSlot.Kind.ARRIVAL, datetime.time(15, 0)),
        (RoadmapSlot.Kind.SOUNDCHECK, datetime.time(16, 30)),
        (RoadmapSlot.Kind.PERFORMANCE, datetime.time(21, 0)),
    ]


def test_prefill_skips_missing_times():
    gig = GigFactory(performance_time=datetime.time(21, 0))

    roadmap = get_or_create_roadmap(gig)

    assert [s.kind for s in roadmap.slots.all()] == [RoadmapSlot.Kind.PERFORMANCE]


def test_get_or_create_is_idempotent_and_does_not_refill():
    gig = GigFactory(performance_time=datetime.time(21, 0))
    roadmap = get_or_create_roadmap(gig)
    roadmap.slots.all().delete()

    again = get_or_create_roadmap(gig)

    assert again.pk == roadmap.pk
    assert Roadmap.objects.count() == 1
    assert again.slots.count() == 0


def test_a_new_roadmap_is_not_shared():
    roadmap = get_or_create_roadmap(GigFactory())

    assert roadmap.token == ""
    assert roadmap.is_published is False


def test_publish_generates_a_long_random_token():
    roadmap = RoadmapFactory()

    publish(roadmap)
    roadmap.refresh_from_db()

    assert roadmap.is_published is True
    assert len(roadmap.token) >= 43  # token_urlsafe(32)
    other = RoadmapFactory()
    publish(other)
    assert other.token != roadmap.token


def test_revoke_erases_the_token():
    roadmap = RoadmapFactory()
    publish(roadmap)

    revoke(roadmap)
    roadmap.refresh_from_db()

    assert roadmap.token == ""
    assert roadmap.is_published is False


def test_publishing_again_gives_a_new_token():
    roadmap = RoadmapFactory()
    publish(roadmap)
    old_token = roadmap.token
    revoke(roadmap)

    publish(roadmap)

    assert roadmap.token != old_token
    assert not Roadmap.objects.filter(token=old_token).exists()


def test_token_is_unique_when_set():
    first = RoadmapFactory(token="abc")
    with pytest.raises(IntegrityError), transaction.atomic():
        RoadmapFactory(token=first.token)


def test_several_unshared_roadmaps_can_coexist():
    RoadmapFactory()
    RoadmapFactory()

    assert Roadmap.objects.filter(token="").count() == 2


def test_one_roadmap_per_gig():
    roadmap = RoadmapFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        Roadmap.objects.create(gig=roadmap.gig, tenant=roadmap.tenant)
