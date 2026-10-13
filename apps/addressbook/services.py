"""Addressbook logic: qualification suggestions (F-15) and the form sent to an organiser (F-16)."""

import secrets
from datetime import timedelta

from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.addresses import DEPARTMENT_CHOICES

from .models import Contact, Promoter, PromoterInvitation

EVENT_TYPE_SUGGESTIONS = [
    "Concert",
    "Festival",
    "Fête locale",
    "Soirée privée",
    "Jeune public",
    "Scolaire",
    "Spectacle de rue",
    "Saison culturelle",
]
AESTHETIC_SUGGESTIONS = [
    "Chanson",
    "Jazz",
    "Rock",
    "Pop",
    "Musiques du monde",
    "Musique classique",
    "Électro",
    "Théâtre musical",
    "Jeune public",
]


def used_values(tenant, field):
    """Values already typed by this tenant for `field`, alphabetical, without duplicates."""
    values = Promoter.objects.filter(tenant=tenant).exclude(**{field: ""})
    seen = {}
    for value in values.values_list(field, flat=True):
        seen.setdefault(value.casefold(), value)
    return sorted(seen.values(), key=str.casefold)


def suggestions(tenant, field, fixed):
    """The proposed values followed by the tenant's own, ignoring case duplicates."""
    merged = {}
    for value in [*fixed, *used_values(tenant, field)]:
        merged.setdefault(value.casefold(), value)
    return sorted(merged.values(), key=str.casefold)


# --- the form sent to an organiser (F-16) -------------------------------------------------

INVITATION_DAYS = 7

# What the organiser can fill in, in the order of the form and of the review screen.
PROMOTER_FIELDS = [
    ("billing_address", _("Adresse")),
    ("postal_code", _("Code postal")),
    ("city", _("Ville")),
    ("department", _("Département")),
    ("siret", _("SIRET")),
    ("code_ape", _("Code APE")),
    ("vat_number", _("N° de TVA intracommunautaire")),
    ("representative_name", _("Représentant légal")),
    ("representative_role", _("Qualité du représentant")),
    ("licence_number", _("N° de licence d'entrepreneur de spectacles")),
    ("email", _("E-mail")),
    ("phone", _("Téléphone")),
]
CONTACT_KEYS = ["name", "role", "email", "phone"]
_DEPARTMENTS = dict(DEPARTMENT_CHOICES)


class InvitationClosed(Exception):
    """The link is no longer usable (expired, cancelled, or already answered)."""


def invitation_path(token):
    return reverse("promoter-form-public", args=[token])


def create_invitation(promoter, user):
    """A new link valid for a week. The link still waiting for an answer is cancelled."""
    now = timezone.now()
    with transaction.atomic():
        for old in PromoterInvitation.objects.select_for_update().filter(
            promoter=promoter, tenant=promoter.tenant, completed_at=None, revoked_at=None
        ):
            if old.status == PromoterInvitation.Status.ACTIVE:
                old.revoked_at = now
                old.save(update_fields=["revoked_at"])
        return PromoterInvitation.objects.create(
            tenant=promoter.tenant,
            promoter=promoter,
            token=secrets.token_urlsafe(32),
            created_by=user,
            expires_at=now + timedelta(days=INVITATION_DAYS),
        )


def revoke_invitation(promoter):
    """Cancel the link of this organiser, if it is still waiting for an answer."""
    invitation = latest_invitation(promoter)
    if invitation and invitation.status == PromoterInvitation.Status.ACTIVE:
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["revoked_at"])
        return True
    return False


def latest_invitation(promoter):
    return PromoterInvitation.objects.filter(promoter=promoter, tenant=promoter.tenant).first()


def find_invitation(token):
    """The invitation of a link, or None for an unknown token. Its status says if it is usable."""
    return (
        PromoterInvitation.objects.select_related("promoter", "tenant").filter(token=token).first()
    )


def build_response(cleaned):
    """What the organiser sent, as plain text, keeping only the fields they filled in."""
    fields = {key: cleaned[key] for key, _label in PROMOTER_FIELDS if cleaned.get(key)}
    contact = {
        key: cleaned[f"contact_{key}"] for key in CONTACT_KEYS if cleaned.get(f"contact_{key}")
    }
    return {"fields": fields, "contact": contact}


def submit_response(invitation, cleaned):
    """Store the organiser's answer and close the link (it can only be used once)."""
    with transaction.atomic():
        locked = PromoterInvitation.objects.select_for_update().get(pk=invitation.pk)
        if locked.status != PromoterInvitation.Status.ACTIVE:
            raise InvitationClosed
        locked.response = build_response(cleaned)
        locked.completed_at = timezone.now()
        locked.save(update_fields=["response", "completed_at"])
    return locked


def _display(key, value):
    return _DEPARTMENTS.get(value, value) if key == "department" else value


def review_rows(invitation):
    """Rows of the review screen: what is there now, what the organiser proposes."""
    promoter = invitation.promoter
    rows = []
    for key, label in PROMOTER_FIELDS:
        proposed = invitation.response.get("fields", {}).get(key)
        if not proposed:
            continue
        current = getattr(promoter, key)
        rows.append(
            {
                "key": key,
                "label": label,
                "current": _display(key, current),
                "proposed": _display(key, proposed),
                "same": current == proposed,
            }
        )
    return rows


def answer_contact(invitation):
    return invitation.response.get("contact") or {}


def pending_answers(tenant):
    """Organisers who answered and whose answer nobody has reviewed yet."""
    return PromoterInvitation.objects.filter(
        tenant=tenant, completed_at__isnull=False, reviewed_at=None
    ).select_related("promoter")


def apply_response(invitation, keys, with_contact):
    """Write the chosen answers into the organiser's card, then forget the stored answer."""
    allowed = {key for key, _label in PROMOTER_FIELDS}
    with transaction.atomic():
        locked = PromoterInvitation.objects.select_for_update().get(pk=invitation.pk)
        if locked.status != PromoterInvitation.Status.ANSWERED:
            raise InvitationClosed
        promoter = locked.promoter
        fields = locked.response.get("fields", {})
        chosen = [key for key in keys if key in allowed and key in fields]
        for key in chosen:
            setattr(promoter, key, fields[key])
        if chosen:
            promoter.save(update_fields=chosen)
        contact = answer_contact(locked)
        if with_contact and contact:
            Contact.objects.create(tenant=locked.tenant, promoter=promoter, **contact)
        close_review(locked)
    return chosen


def close_review(invitation):
    """Mark the answer as handled and empty it (applied, partly applied, or ignored)."""
    invitation.response = {}
    invitation.reviewed_at = timezone.now()
    invitation.save(update_fields=["response", "reviewed_at"])


def ignore_response(invitation):
    """Throw the organiser's answer away without applying anything."""
    with transaction.atomic():
        locked = PromoterInvitation.objects.select_for_update().get(pk=invitation.pk)
        if locked.status != PromoterInvitation.Status.ANSWERED:
            raise InvitationClosed
        close_review(locked)
