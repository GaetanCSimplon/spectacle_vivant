from django.db import migrations
from django.db.models import F, Q

FIELDS = {
    "arrival": "get_in_time",
    "soundcheck": "soundcheck_time",
    "performance": "performance_time",
}


def copy_slot_times(apps, schema_editor):
    """The slots of the concert day now give the times of the gig: apply it once to old dates."""
    RoadmapSlot = apps.get_model("roadmaps", "RoadmapSlot")
    Gig = apps.get_model("gigs", "Gig")
    slots = RoadmapSlot.objects.filter(
        Q(day=None) | Q(day=F("roadmap__gig__date")), kind__in=FIELDS
    )
    # Latest first, so that the earliest slot of a kind is written last and wins.
    for kind, time, gig_id in slots.order_by("-time").values_list("kind", "time", "roadmap__gig_id"):
        Gig.objects.filter(pk=gig_id).update(**{FIELDS[kind]: time})


class Migration(migrations.Migration):
    dependencies = [
        ("roadmaps", "0009_roadmap_days_and_slot_files"),
        ("gigs", "0016_gigmember_hours"),
    ]

    operations = [migrations.RunPython(copy_slot_times, migrations.RunPython.noop)]
