"""The slots of the concert day give the times of the gig, which the contract reads."""

import datetime
from importlib import import_module

import pytest
from django.apps import apps
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

from ..factories import RoadmapFactory, RoadmapSlotFactory
from ..models import RoadmapSlot

pytestmark = pytest.mark.django_db

NINE = datetime.time(21, 0)


@pytest.fixture
def gig(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return GigFactory(tenant=membership.tenant)


def _post(client, name, gig, *args, **data):
    return client.post(reverse(f"roadmaps:{name}", args=[gig.pk, "creneaux", *args]), data)


def _times(gig):
    gig.refresh_from_db()
    return gig.get_in_time, gig.soundcheck_time, gig.performance_time


def test_adding_changing_and_deleting_a_slot_updates_the_gig(client, gig):
    _post(client, "item-add", gig, kind="performance", time="21:00")
    assert _times(gig) == (None, None, NINE)
    slot = RoadmapSlot.objects.get()

    _post(client, "item-edit", gig, slot.pk, kind="soundcheck", time="17:00")
    assert _times(gig) == (None, datetime.time(17, 0), None)

    _post(client, "item-delete", gig, slot.pk)
    assert _times(gig) == (None, None, None)


def test_the_earliest_slot_of_the_concert_day_wins(client, gig):
    _post(client, "item-add", gig, kind="performance", time="21:00")
    _post(client, "item-add", gig, kind="performance", time="23:00", day=gig.date.isoformat())

    assert _times(gig)[2] == NINE


def test_other_days_and_other_kinds_leave_the_times_alone(client, gig):
    gig.soundcheck_time = NINE
    gig.save()
    eve = (gig.date - datetime.timedelta(days=1)).isoformat()

    _post(client, "item-add", gig, kind="soundcheck", time="10:00", day=eve)
    _post(client, "item-add", gig, kind="other", time="11:00")

    assert _times(gig) == (None, NINE, None)


def test_the_migration_copies_slot_times_and_erases_nothing(gig):
    gig.get_in_time = datetime.time(15, 0)
    gig.performance_time = datetime.time(20, 0)
    gig.save()
    roadmap = RoadmapFactory(gig=gig)
    for time, day in ((datetime.time(23, 0), None), (NINE, gig.date)):
        RoadmapSlotFactory(roadmap=roadmap, kind="performance", time=time, day=day)
    RoadmapSlotFactory(
        roadmap=roadmap,
        kind="soundcheck",
        time=NINE,
        day=gig.date - datetime.timedelta(days=1),
    )

    migration = import_module("apps.roadmaps.migrations.0010_copy_slot_times_to_gigs")
    migration.copy_slot_times(apps, None)

    assert _times(gig) == (datetime.time(15, 0), None, NINE)
