import secrets

from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.services import render_pdf
from apps.gigs.models import GigMember
from apps.tenants.models import Person

from .models import Roadmap, RoadmapSlot, tel_link


class AlreadyOnTheGig(Exception):
    """The person is already part of this gig's team."""


def available_team(gig):
    """The structure's people who are not yet on this gig."""
    taken = gig.members.exclude(person=None).values_list("person_id", flat=True)
    return Person.objects.filter(tenant=gig.tenant).exclude(pk__in=taken)


def add_team_member(gig, person):
    """Put a person of the team on the gig, copying what the roadmap shows.

    The average fee is never copied: a roadmap can be shared with a public link.
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


def public_context(roadmap):
    """Everything a roadmap may show to someone who only has the link.

    This is a whitelist, on purpose: prices, conditions, contract, invoices, the billed
    promoter, the gig status and e-mail addresses never go through here. Both the public
    page and the PDF are built from it only.
    """
    gig = roadmap.gig
    venue = gig.venue
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
        "slots": list(roadmap.slots.all()),
        "lodgings": list(roadmap.lodgings.prefetch_related("contacts")),
        "meals": list(roadmap.meals.prefetch_related("contacts")),
        "notes": roadmap.notes,
        "version": roadmap.version,
        "updated_at": roadmap.updated_at,
        "members": _people(gig.members.all()),
        "venue_contacts": _people(venue.contacts.all()),
    }


def render_roadmap_pdf(roadmap):
    """PDF bytes of the roadmap, rendered on the fly (nothing is stored)."""
    return render_pdf("roadmaps/roadmap_pdf.html", public_context(roadmap))
