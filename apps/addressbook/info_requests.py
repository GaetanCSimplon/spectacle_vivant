"""The form a contact or a team member fills in about themselves (ORG-07).

Same life cycle as the organiser's form (`services`): a link valid for a week, used once; the
answer waits, untouched, until the user reviews it and picks what to apply. A team member's
form carries the private fields (birth date, social security number, address, GUSO number): only
the owner of the structure may send it and review its answer.
"""

import datetime
import secrets
from datetime import timedelta
from urllib.parse import quote

from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy

from apps.core.addresses import DEPARTMENT_CHOICES
from apps.tenants import message_templates
from apps.tenants.models import Person
from apps.tenants.validators import normalize_social_security_number

from .models import Contact, InfoInvitation

INVITATION_DAYS = 7

CONTACT_FIELDS = [
    ("name", gettext_lazy("Nom")),
    ("role", gettext_lazy("Fonction")),
    ("email", gettext_lazy("E-mail")),
    ("phone", gettext_lazy("Téléphone")),
]
PERSON_FIELDS = [
    ("phone", gettext_lazy("Téléphone")),
    ("email", gettext_lazy("E-mail")),
    ("address", gettext_lazy("Adresse")),
    ("postal_code", gettext_lazy("Code postal")),
    ("city", gettext_lazy("Ville")),
    ("department", gettext_lazy("Département")),
    ("birth_date", gettext_lazy("Date de naissance")),
    ("social_security_number", gettext_lazy("N° de sécurité sociale")),
    ("guso_number", gettext_lazy("N° GUSO")),
]
_DEPARTMENTS = dict(DEPARTMENT_CHOICES)


class InvitationClosed(Exception):
    """The link is no longer usable (expired, cancelled, or already answered)."""


def fields_for(target):
    return CONTACT_FIELDS if isinstance(target, Contact) else PERSON_FIELDS


def public_path(token):
    return reverse("info-form-public", args=[token])


def _filter(target):
    key = "contact" if isinstance(target, Contact) else "person"
    return {key: target, "tenant": target.tenant}


def _invitations(target):
    return InfoInvitation.objects.filter(**_filter(target))


def latest_invitation(target):
    return _invitations(target).first()


def create_invitation(target, user):
    """A new link valid for a week. The link still waiting for an answer is cancelled."""
    now = timezone.now()
    with transaction.atomic():
        for old in (
            _invitations(target).select_for_update().filter(completed_at=None, revoked_at=None)
        ):
            if old.status == InfoInvitation.Status.ACTIVE:
                old.revoked_at = now
                old.save(update_fields=["revoked_at"])
        return InfoInvitation.objects.create(
            **_filter(target),
            token=secrets.token_urlsafe(32),
            created_by=user,
            expires_at=now + timedelta(days=INVITATION_DAYS),
        )


def revoke_invitation(target):
    invitation = latest_invitation(target)
    if invitation and invitation.status == InfoInvitation.Status.ACTIVE:
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["revoked_at"])
        return True
    return False


def find_invitation(token):
    return (
        InfoInvitation.objects.select_related("contact", "person", "tenant")
        .filter(token=token)
        .first()
    )


def _clean(value):
    if isinstance(value, datetime.date):
        return value.isoformat()
    return str(value or "").strip()


def build_response(target, cleaned):
    """What was sent, as plain text, keeping only the known fields that were filled in."""
    response = {}
    for key, _label in fields_for(target):
        value = _clean(cleaned.get(key))
        if value:
            response[key] = value
    return response


def submit_response(invitation, cleaned):
    """Store the answer and close the link (it can only be used once)."""
    with transaction.atomic():
        locked = InfoInvitation.objects.select_for_update().get(pk=invitation.pk)
        if locked.status != InfoInvitation.Status.ACTIVE:
            raise InvitationClosed
        locked.response = build_response(locked.target, cleaned)
        locked.completed_at = timezone.now()
        locked.save(update_fields=["response", "completed_at"])
    return locked


def _display(target, key, value):
    if key == "department":
        return _DEPARTMENTS.get(value, value)
    if key == "birth_date" and value:
        return datetime.date.fromisoformat(str(value)).strftime("%d/%m/%Y")
    if key == "social_security_number" and value:
        return Person(social_security_number=str(value)).formatted_social_security_number
    return value


def review_rows(invitation):
    """Rows of the review screen: what the fiche has now, what the person proposes."""
    target = invitation.target
    rows = []
    for key, label in fields_for(target):
        proposed = invitation.response.get(key)
        if not proposed:
            continue
        current = getattr(target, key) or ""
        rows.append(
            {
                "key": key,
                "label": label,
                "current": _display(target, key, current),
                "proposed": _display(target, key, proposed),
                "same": _clean(current) == proposed,
            }
        )
    return rows


def pending_answers(tenant):
    return InfoInvitation.objects.filter(
        tenant=tenant, completed_at__isnull=False, reviewed_at=None
    ).select_related("contact", "person")


def apply_response(invitation, keys):
    """Write the chosen answers into the fiche, then forget the stored answer."""
    with transaction.atomic():
        locked = InfoInvitation.objects.select_for_update().get(pk=invitation.pk)
        if locked.status != InfoInvitation.Status.ANSWERED:
            raise InvitationClosed
        target = locked.target
        allowed = {key for key, _label in fields_for(target)}
        chosen = [key for key in keys if key in allowed and key in locked.response]
        for key in chosen:
            value = locked.response[key]
            if key == "birth_date":
                value = datetime.date.fromisoformat(value)
            elif key == "social_security_number":
                value = normalize_social_security_number(value)
            setattr(target, key, value)
        if chosen:
            target.save(update_fields=chosen)
        close_review(locked)
    return chosen


def close_review(invitation):
    invitation.response = {}
    invitation.reviewed_at = timezone.now()
    invitation.save(update_fields=["response", "reviewed_at"])


def ignore_response(invitation):
    with transaction.atomic():
        locked = InfoInvitation.objects.select_for_update().get(pk=invitation.pk)
        if locked.status != InfoInvitation.Status.ANSWERED:
            raise InvitationClosed
        close_review(locked)


def mail(target, link):
    """The message to send from the user's own mail software (nothing is sent by the app)."""
    tenant = target.tenant
    data = {
        "Contact": target.name if isinstance(target, Contact) else target.first_name,
        "Nom du groupe": tenant.name,
        "Lien": link,
        "Signature": tenant.name,
    }
    subject, body = message_templates.render(tenant, message_templates.INFO, data)
    email = target.email
    mailto = (
        f"mailto:{quote(email, safe='@')}?subject={quote(subject, safe='')}"
        f"&body={quote(body, safe='')}"
        if email
        else ""
    )
    return {"subject": subject, "body": body, "link": link, "to": email, "mailto": mailto}
