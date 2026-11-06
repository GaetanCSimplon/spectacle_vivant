"""The "Régie de tournée" form sent to an organiser for one date (F-90).

Same life cycle as the form of the organiser's card (`addressbook.services`): a link valid for a
week, used once; the answer waits, untouched, until the owner reviews it and chooses what to
apply. Nothing the organiser sends goes to the date or its roadmap on its own.
"""

import datetime
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.addressbook.models import Contact
from apps.gigs.models import Gig

from .models import Lodging, Meal, Roadmap, RoadmapRequest, RoadmapSlot
from .services import bump_version, get_or_create_roadmap

REQUEST_DAYS = 7

# What the organiser can answer, by group: a group is applied, or ignored, as a whole.
# key -> label, in the order of the form and of the review screen.
GROUPS = {
    "times": (
        _("Horaires"),
        {
            "get_in_time": _("Get in"),
            "soundcheck_time": _("Balances"),
            "performance_time": _("Concert"),
        },
    ),
    "access": (_("Accueil, accès et consignes"), {"access_notes": _("Accueil")}),
    "meal": (
        _("Repas"),
        {"meal_place": _("Lieu"), "meal_time": _("Heure"), "meal_notes": _("Détails")},
    ),
    "lodging": (
        _("Hébergement"),
        {
            "lodging_name": _("Nom"),
            "lodging_address": _("Adresse"),
            "lodging_arrival_time": _("Heure d'arrivée"),
            "lodging_notes": _("Détails"),
        },
    ),
    "contact": (
        _("Contact sur place"),
        {"contact_name": _("Nom"), "contact_role": _("Fonction"), "contact_phone": _("Téléphone")},
    ),
    "remarks": (_("Remarques"), {"remarks": _("Remarques")}),
}
TIME_KEYS = {
    "get_in_time",
    "soundcheck_time",
    "performance_time",
    "meal_time",
    "lodging_arrival_time",
}
ALL_KEYS = {key for _label, keys in GROUPS.values() for key in keys}
SLOT_KINDS = {
    "get_in_time": RoadmapSlot.Kind.ARRIVAL,
    "soundcheck_time": RoadmapSlot.Kind.SOUNDCHECK,
    "performance_time": RoadmapSlot.Kind.PERFORMANCE,
}


class RequestClosed(Exception):
    """The link is no longer usable (expired, cancelled, or already answered)."""


def create_request(gig, user):
    """A new link valid for a week. The link still waiting for an answer is cancelled."""
    now = timezone.now()
    with transaction.atomic():
        for old in RoadmapRequest.objects.select_for_update().filter(
            gig=gig, tenant=gig.tenant, completed_at=None, revoked_at=None
        ):
            if old.status == RoadmapRequest.Status.ACTIVE:
                old.revoked_at = now
                old.save(update_fields=["revoked_at"])
        return RoadmapRequest.objects.create(
            tenant=gig.tenant,
            gig=gig,
            token=secrets.token_urlsafe(32),
            created_by=user,
            expires_at=now + timedelta(days=REQUEST_DAYS),
        )


def revoke_request(gig):
    """Cancel the link that still waits for an answer. True if there was one."""
    request = latest_request(gig)
    if request is None or request.status != RoadmapRequest.Status.ACTIVE:
        return False
    request.revoked_at = timezone.now()
    request.save(update_fields=["revoked_at"])
    return True


def latest_request(gig):
    return RoadmapRequest.objects.filter(gig=gig, tenant=gig.tenant).first()


def find_request(token):
    """The request of a link, or None for an unknown token. Its status says if it is usable."""
    return (
        RoadmapRequest.objects.select_related("gig__show", "gig__venue", "tenant")
        .filter(token=token)
        .first()
    )


def _clean_value(key, value):
    if key in TIME_KEYS:
        if isinstance(value, datetime.time):
            return value.strftime("%H:%M")
        try:
            return datetime.datetime.strptime(str(value), "%H:%M").strftime("%H:%M")
        except ValueError:
            return ""
    return str(value or "").strip()


def build_response(cleaned):
    """What the organiser sent, as plain text, keeping only the known fields they filled in."""
    response = {}
    for key in ALL_KEYS:
        value = _clean_value(key, cleaned.get(key))
        if value:
            response[key] = value
    return response


def submit_response(request, cleaned):
    """Store the organiser's answer and close the link (it can only be used once)."""
    with transaction.atomic():
        locked = RoadmapRequest.objects.select_for_update().get(pk=request.pk)
        if locked.status != RoadmapRequest.Status.ACTIVE:
            raise RequestClosed
        locked.response = build_response(cleaned)
        locked.completed_at = timezone.now()
        locked.save(update_fields=["response", "completed_at"])
    return locked


def pending_requests(tenant):
    """Dates whose organiser answered and whose answer nobody has reviewed yet."""
    return RoadmapRequest.objects.filter(
        tenant=tenant, completed_at__isnull=False, reviewed_at=None
    ).select_related("gig__show")


def answered_groups(request):
    """The groups the organiser filled in, for the review screen: (key, label, [(label, value)])."""
    groups = []
    for key, (label, fields) in GROUPS.items():
        rows = [
            (name, request.response[field])
            for field, name in fields.items()
            if field in request.response
        ]
        if rows:
            groups.append((key, label, rows))
    return groups


def review_groups(request):
    """The review screen: each group the organiser filled in, with what the date has now.

    A list of dicts `key`, `label`, `rows` (each `label`, `value`, and for a time `current`).
    """
    gig = request.gig
    current = {key: getattr(gig, key) for key in SLOT_KINDS}
    groups = []
    for key, (label, fields) in GROUPS.items():
        rows = []
        for field, name in fields.items():
            if field not in request.response:
                continue
            row = {"label": name, "value": request.response[field]}
            if field in current:
                row["current"] = current[field].strftime("%H:%M") if current[field] else ""
            rows.append(row)
        if rows:
            groups.append({"key": key, "label": label, "rows": rows})
    return groups


def _time(value):
    return datetime.datetime.strptime(value, "%H:%M").time()


def _append(text, addition):
    return f"{text.rstrip()}\n\n{addition}".strip() if text.strip() else addition


def _apply_times(gig, roadmap, response):
    changed = []
    for key, kind in SLOT_KINDS.items():
        if key not in response:
            continue
        value = _time(response[key])
        setattr(gig, key, value)
        changed.append(key)
        slot = roadmap.slots.filter(kind=kind).first()
        if slot is None:
            RoadmapSlot.objects.create(tenant=gig.tenant, roadmap=roadmap, kind=kind, time=value)
        else:
            slot.time = value
            slot.save(update_fields=["time"])
    if changed:
        gig.save(update_fields=changed)


def _apply_group(group, gig, roadmap, response):
    if group == "times":
        _apply_times(gig, roadmap, response)
    elif group == "access" and "access_notes" in response:
        roadmap.notes = _append(roadmap.notes, f"{_('Accueil')} : {response['access_notes']}")
    elif group == "remarks" and "remarks" in response:
        roadmap.notes = _append(roadmap.notes, f"{_('Remarques')} : {response['remarks']}")
    elif group == "meal" and any(key.startswith("meal_") for key in response):
        Meal.objects.create(
            tenant=gig.tenant,
            roadmap=roadmap,
            place=response.get("meal_place") or _("Repas"),
            time=_time(response["meal_time"]) if "meal_time" in response else None,
            notes=response.get("meal_notes", ""),
        )
    elif group == "lodging" and any(key.startswith("lodging_") for key in response):
        Lodging.objects.create(
            tenant=gig.tenant,
            roadmap=roadmap,
            name=response.get("lodging_name") or _("Hébergement"),
            address=response.get("lodging_address", ""),
            arrival_time=(
                _time(response["lodging_arrival_time"])
                if "lodging_arrival_time" in response
                else None
            ),
            notes=response.get("lodging_notes", ""),
        )
    elif group == "contact" and response.get("contact_name"):
        contact = Contact.objects.create(
            tenant=gig.tenant,
            name=response["contact_name"],
            role=response.get("contact_role", ""),
            phone=response.get("contact_phone", ""),
        )
        contact.venues.add(gig.venue)


def apply_response(request, groups):
    """Write the chosen groups into the date and its roadmap, then forget the stored answer.

    Only the groups the organiser actually filled in can be applied; any other name is ignored.
    The roadmap version goes up once, if it is shared. Returns the groups that were applied.
    """
    with transaction.atomic():
        locked = RoadmapRequest.objects.select_for_update().get(pk=request.pk)
        if locked.status != RoadmapRequest.Status.ANSWERED:
            raise RequestClosed
        gig = Gig.objects.select_for_update().get(pk=locked.gig_id, tenant=locked.tenant)
        roadmap = get_or_create_roadmap(gig)
        response = locked.response
        applied = [
            group
            for group in GROUPS
            if group in groups and any(field in response for field in GROUPS[group][1])
        ]
        for group in applied:
            _apply_group(group, gig, roadmap, response)
        if applied:
            Roadmap.objects.filter(pk=roadmap.pk).update(notes=roadmap.notes)
            bump_version(roadmap)
        close_review(locked)
    return applied


def close_review(request):
    """Mark the answer as handled and empty it (applied, partly applied, or ignored)."""
    request.response = {}
    request.reviewed_at = timezone.now()
    request.save(update_fields=["response", "reviewed_at"])


def ignore_response(request):
    """Throw the organiser's answer away without applying anything."""
    with transaction.atomic():
        locked = RoadmapRequest.objects.select_for_update().get(pk=request.pk)
        if locked.status != RoadmapRequest.Status.ANSWERED:
            raise RequestClosed
        close_review(locked)
