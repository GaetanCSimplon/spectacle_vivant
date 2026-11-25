import datetime
import secrets
from dataclasses import dataclass

from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.services import render_pdf
from apps.gigs import hospitality
from apps.gigs.models import GigMember
from apps.tenants.models import Person

from .models import Roadmap, RoadmapSlot, tel_link

# The times of a gig (read by the contract, Radar and the calendar) and the slots that give them.
SLOT_KINDS = {
    "get_in_time": RoadmapSlot.Kind.ARRIVAL,
    "soundcheck_time": RoadmapSlot.Kind.SOUNDCHECK,
    "performance_time": RoadmapSlot.Kind.PERFORMANCE,
}


class AlreadyOnTheGig(Exception):
    """The person is already part of this gig's team."""


def available_team(gig):
    """The structure's people who are not yet on this gig."""
    taken = gig.members.exclude(person=None).values_list("person_id", flat=True)
    return Person.objects.filter(tenant=gig.tenant).exclude(pk__in=taken)


def cast_not_on_gig(gig):
    """The people of the show's cast (its distribution) who are not on this gig yet."""
    taken = gig.members.exclude(person=None).values_list("person_id", flat=True)
    return gig.show.cast.filter(tenant=gig.tenant).exclude(pk__in=taken)


def add_team_member(gig, person):
    """Put a person of the team on the gig, copying what the roadmap shows.

    The reference fee is copied into the private cachet of the date (owner only, a copy: later
    changes to the reference do not touch the date). It never reaches a roadmap.
    """
    if person.tenant_id != gig.tenant_id:
        raise ValueError("A person of another tenant cannot join this gig.")
    if gig.members.filter(person=person).exists():
        raise AlreadyOnTheGig(
            _("%(name)s fait déjà partie de cette date.") % {"name": person.full_name}
        )
    return GigMember.objects.create(
        tenant=gig.tenant,
        gig=gig,
        person=person,
        name=person.full_name,
        role=person.role,
        phone=person.phone,
        email=person.email,
        cachet_amount=person.average_fee,
    )


def get_or_create_roadmap(gig):
    """Return the gig's roadmap; a new one is pre-filled from the gig's times."""
    roadmap, created = Roadmap.objects.get_or_create(gig=gig, defaults={"tenant": gig.tenant})
    if created:
        prefill = [
            (RoadmapSlot.Kind.ARRIVAL, gig.get_in_time),
            (RoadmapSlot.Kind.SOUNDCHECK, gig.soundcheck_time),
            (RoadmapSlot.Kind.PERFORMANCE, gig.performance_time),
        ]
        RoadmapSlot.objects.bulk_create(
            RoadmapSlot(tenant=gig.tenant, roadmap=roadmap, kind=kind, time=time)
            for kind, time in prefill
            if time is not None
        )
    return roadmap


def concert_day_kinds(gig, item):
    """The slot kind of `item` if it is a slot of the day of the concert, else nothing."""
    if isinstance(item, RoadmapSlot) and item.day in (None, gig.date):
        return {item.kind}
    return set()


def sync_gig_times(gig, kinds):
    """Copy the times of these kinds of slot onto the gig: the earliest slot of the concert day.

    No slot left of a kind: the time is emptied. Only pass the kinds a change touched, so that a
    time without any slot is never lost.
    """
    changed = []
    for field, kind in SLOT_KINDS.items():
        if kind not in kinds:
            continue
        slot = (
            RoadmapSlot.objects.filter(
                Q(day=None) | Q(day=gig.date), tenant=gig.tenant, roadmap__gig=gig, kind=kind
            )
            .order_by("time")
            .first()
        )
        setattr(gig, field, slot.time if slot else None)
        changed.append(field)
    if changed:
        gig.save(update_fields=changed)


def bump_version(roadmap):
    """Version +1 and the time of the change, only while the roadmap is shared.

    Changes made before the first sharing do not count: the first link shows "Version 1".
    """
    if not roadmap.is_published:
        return
    Roadmap.objects.filter(pk=roadmap.pk).update(
        version=F("version") + 1, updated_at=timezone.now()
    )
    roadmap.refresh_from_db(fields=["version", "updated_at"])


def places_without_map(gig, roadmap):
    """Places that have an address but no map point (the lookup did not recognise the address)."""
    places = [gig.venue, *roadmap.lodgings.all()]
    return [place for place in places if place.one_line_address and not place.has_point]


def publish(roadmap):
    """Turn sharing on with a brand-new secret token (an old link never comes back)."""
    roadmap.token = secrets.token_urlsafe(32)
    roadmap.is_published = True
    roadmap.updated_at = timezone.now()
    roadmap.save(update_fields=["token", "is_published", "updated_at"])


def revoke(roadmap):
    """Turn sharing off for good: the token is erased."""
    roadmap.token = ""
    roadmap.is_published = False
    roadmap.save(update_fields=["token", "is_published"])


def public_path(token):
    """Path of the public page of a shared roadmap."""
    return reverse("roadmap-public", args=[token])


_tel = tel_link


def _people(people):
    return [
        {"name": p.name, "role": p.role, "phone": p.phone, "tel": _tel(p.phone)} for p in people
    ]


def chronological(items, gig):
    """Slots, meals or lodgings in the order they happen: by day (an empty day is the day of the
    concert), then by time (none first), then as they were added."""
    return sorted(
        items,
        key=lambda item: (
            item.day or gig.date,
            getattr(item, "time", None) or getattr(item, "arrival_time", None) or datetime.time(0),
            item.pk,
        ),
    )


@dataclass(frozen=True)
class ProgramItem:
    """One line of the program: a slot, a meal or an arrival at the lodging."""

    time: datetime.time
    kind: str
    label: str
    note: str = ""
    day: datetime.date = None
    # A file hangs from this slot: the shared page only says so; the files are in `files`, which
    # only the personal space fills (FDR-03).
    has_files: bool = False
    files: tuple = ()


@dataclass(frozen=True)
class ProgramDay:
    """The items of one day of the program."""

    day: datetime.date
    is_concert_day: bool
    items: list


def build_program(roadmap, file_link=None, person=None):
    """The program in order, by day: the slots, plus the meals and the lodging arrivals that have
    a time. A meal at the very day and time of a "Repas" slot is not repeated (FDR-04). The
    details of a meal or of a lodging (address, map, contacts) stay in their own sections.

    `file_link(document)` makes the link of a file; with it (personal space), the files of each
    slot visible to `person` are listed under it. Without it, a slot only says it has files.
    """
    gig_day = roadmap.gig.date
    slots = list(roadmap.slots.all())
    meal_keys = {(slot.day or gig_day, slot.time) for slot in slots if slot.kind == "meal"}
    by_slot = {}
    for document in roadmap.documents.filter(slot__isnull=False):
        by_slot.setdefault(document.slot_id, []).append(document)
    visible = {
        pk: [doc for doc in docs if doc.person_id in (None, getattr(person, "pk", None))]
        for pk, docs in by_slot.items()
    }
    items = []
    for slot in slots:
        files = ()
        if file_link is not None:
            files = tuple(file_link(doc) for doc in visible.get(slot.pk, []))
        items.append(
            ProgramItem(
                slot.time,
                slot.kind,
                slot.label or slot.get_kind_display(),
                slot.note,
                day=slot.day or gig_day,
                has_files=slot.pk in by_slot,
                files=files,
            )
        )
    items += [
        ProgramItem(meal.time, "meal", f"{_('Repas')} — {meal.place}", day=meal.day or gig_day)
        for meal in roadmap.meals.all()
        if meal.time and (meal.day or gig_day, meal.time) not in meal_keys
    ]
    items += [
        ProgramItem(
            lodging.arrival_time,
            "lodging",
            f"{_('Arrivée à l’hébergement')} — {lodging.name}",
            day=lodging.day or gig_day,
        )
        for lodging in roadmap.lodgings.all()
        if lodging.arrival_time
    ]
    return sorted(items, key=lambda item: (item.day, item.time))  # stable: slots first at a tie


def program_days(program, gig_day):
    """The program grouped by day (the page shows a heading per day when there are several)."""
    days = {}
    for item in program:
        days.setdefault(item.day, []).append(item)
    return [ProgramDay(day, day == gig_day, days[day]) for day in sorted(days)]


def public_context(roadmap, file_link=None, person=None):
    """Everything a roadmap may show to someone who only has the link.

    This is a whitelist, on purpose: prices, conditions, contract, invoices, the billed
    promoter (only the names, roles and phones of its contacts), the gig status and e-mail
    addresses never go through here. Both the public page and the PDF are built from it only.
    """
    gig = roadmap.gig
    venue = gig.venue
    program = build_program(roadmap, file_link, person)
    venue_contacts = list(venue.contacts.filter(tenant=gig.tenant))
    # The people to call on the organiser's side (names, roles, phones: no e-mail, and never the
    # name or the billing address of the organiser). Someone who also works for the venue is
    # listed once, with the venue.
    on_venue = {c.pk for c in venue_contacts}
    promoter_contacts = [
        c for c in gig.promoter.contacts.filter(tenant=gig.tenant) if c.pk not in on_venue
    ]
    return {
        "show_title": gig.show.title,
        "group_name": gig.show.group_name,
        "date": gig.date,
        "venue": {
            "name": venue.name,
            "address": venue.full_address,
            "address_one_line": venue.one_line_address,
            "access_info": venue.access_info,
            "phone": venue.phone,
            "tel": _tel(venue.phone),
            "map_url": venue.map_embed_url,
        },
        "crew_headcount": gig.crew_headcount,
        "program": program,
        "program_days": program_days(program, gig.date),
        # Only who takes it in charge and how many: never the free text, which may speak of money.
        "meals_cover": hospitality.roadmap_line(
            gig.meals_covered_by, gig.meals_count, hospitality.MEAL_UNIT
        ),
        "lodging_cover": hospitality.roadmap_line(
            gig.lodging_covered_by, gig.lodging_nights, hospitality.NIGHT_UNIT
        ),
        "lodgings": list(roadmap.lodgings.prefetch_related("contacts")),
        "meals": list(roadmap.meals.prefetch_related("contacts")),
        "notes": roadmap.notes,
        "version": roadmap.version,
        "updated_at": roadmap.updated_at,
        "members": _people(gig.members.all()),
        "venue_contacts": _people(venue_contacts),
        "promoter_contacts": _people(promoter_contacts),
    }


def render_roadmap_pdf(roadmap):
    """PDF bytes of the roadmap, rendered on the fly (nothing is stored)."""
    return render_pdf("roadmaps/roadmap_pdf.html", public_context(roadmap))
