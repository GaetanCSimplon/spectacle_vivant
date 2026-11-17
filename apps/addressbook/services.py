"""Addressbook logic: the form sent to an organiser (F-16)."""

import secrets
from datetime import timedelta

from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.addresses import DEPARTMENT_CHOICES

from .models import Contact, PromoterInvitation

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
    ("legal_form", _("Nature juridique")),
    ("licence_number", _("N° de licence d'entrepreneur de spectacles")),
    ("licence_categories", _("Catégories de la licence")),
    ("email", _("E-mail")),
    ("phone", _("Téléphone")),
]
CONTACT_KEYS = ["name", "role", "email", "phone"]
CONTACT_SLOTS = 4
# Suggested roles of the contacts an organiser gives (ORG-04); the field stays free text.
CONTACT_ROLES = [
    _("Direction"),
    _("Programmation"),
    _("Administration"),
    _("Comptabilité"),
    _("Régie technique"),
    _("Accueil"),
]
_DEPARTMENTS = dict(DEPARTMENT_CHOICES)


class InvitationClosed(Exception):
    """The link is no longer usable (expired, cancelled, or already answered)."""


def invitation_path(token):
    return reverse("promoter-form-public", args=[token])


def create_invitation(promoter, user, gig=None):
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
            gig=gig,
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
    contacts = []
    for slot in range(1, CONTACT_SLOTS + 1):
        contact = {
            key: cleaned[f"contact{slot}_{key}"]
            for key in CONTACT_KEYS
            if cleaned.get(f"contact{slot}_{key}")
        }
        if contact.get("name"):
            contacts.append(contact)
    return {"fields": fields, "contacts": contacts}


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


def answer_contacts(invitation):
    """The contacts the organiser gave. An answer stored before several contacts were allowed
    holds a single `contact`: it is read as a list of one."""
    contacts = invitation.response.get("contacts")
    if contacts is None:
        single = invitation.response.get("contact")
        contacts = [single] if single else []
    return contacts


def pending_answers(tenant):
    """Organisers who answered and whose answer nobody has reviewed yet."""
    return PromoterInvitation.objects.filter(
        tenant=tenant, completed_at__isnull=False, reviewed_at=None
    ).select_related("promoter")


def _add_contact(tenant, promoter, data):
    """Create the contact for the organiser, unless the same person (name and e-mail) is already
    in the address book: then the existing contact is attached instead of duplicated."""
    values = {key: data[key] for key in CONTACT_KEYS if data.get(key)}
    existing = Contact.objects.filter(
        tenant=tenant, name__iexact=values["name"], email=values.get("email", "")
    ).first()
    contact = existing or Contact.objects.create(tenant=tenant, **values)
    contact.promoters.add(promoter)
    return contact


def apply_response(invitation, keys, contact_indexes):
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
        contacts = answer_contacts(locked)
        for index in sorted(set(contact_indexes)):
            if 0 <= index < len(contacts) and contacts[index].get("name"):
                _add_contact(locked.tenant, promoter, contacts[index])
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
