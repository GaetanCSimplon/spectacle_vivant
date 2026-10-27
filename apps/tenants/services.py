import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Membership, User
from apps.addressbook.models import Contact, Promoter, Venue
from apps.catalog.models import Show
from apps.documents.models import Contract, Invoice, Quote
from apps.finance.models import Expense, Payment
from apps.gigs.models import Gig

from .data_export import stored_files
from .models import Person, Tenant

DELETION_GRACE_DAYS = 30


def create_tenant_for_user(user, **tenant_fields):
    """Create a Tenant and make `user` its owner, atomically."""
    with transaction.atomic():
        tenant = Tenant.objects.create(**tenant_fields)
        Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.OWNER)
    return tenant


# --- personal space of a team member (a secret link, no account) ------------------------------

RECENT_DAYS = 30


def enable_team_space(person):
    """Give the person a personal link (a brand-new secret: a revoked one never comes back)."""
    person.access_token = secrets.token_urlsafe(32)
    person.save(update_fields=["access_token"])


def disable_team_space(person):
    person.access_token = ""
    person.save(update_fields=["access_token"])


def person_for_token(token):
    """The person a personal link belongs to, or None. An empty token never matches anybody."""
    if not token:
        return None
    return Person.objects.filter(access_token=token).select_related("tenant").first()


def team_space_gigs(person):
    """The dates of the person: those where they are on the team of the roadmap (picked from
    the team, so they are linked to their card). Cancelled dates are left out."""
    return (
        Gig.objects.filter(tenant=person.tenant, members__person=person)
        .exclude(status=Gig.Status.CANCELLED)
        .select_related("show", "venue")
        .distinct()
    )


def team_space_dates(person, today):
    """(coming dates, dates of the last RECENT_DAYS days) for the personal page."""
    gigs = team_space_gigs(person)
    coming = gigs.filter(date__gte=today).order_by("date")
    recent = gigs.filter(date__lt=today, date__gte=today - timedelta(days=RECENT_DAYS))
    return list(coming), list(recent.order_by("-date"))


class CannotLeave(Exception):
    """The user is the last owner of the tenant: they must delete it or hand it over."""


def request_deletion(tenant):
    """Start the grace period. Asking twice keeps the first date."""
    if tenant.deletion_requested_at is None:
        tenant.deletion_requested_at = timezone.now()
        tenant.save(update_fields=["deletion_requested_at"])


def cancel_deletion(tenant):
    tenant.deletion_requested_at = None
    tenant.save(update_fields=["deletion_requested_at"])


def deletion_date(tenant):
    """The day the data will be purged, or None if no deletion is pending."""
    if tenant.deletion_requested_at is None:
        return None
    return (tenant.deletion_requested_at + timedelta(days=DELETION_GRACE_DAYS)).date()


def leave_tenant(user, tenant):
    """Remove `user` from the tenant, unless they are its last owner."""
    membership = Membership.objects.get(user=user, tenant=tenant)
    if membership.role == Membership.Role.OWNER:
        other_owners = (
            Membership.objects.filter(tenant=tenant, role=Membership.Role.OWNER)
            .exclude(pk=membership.pk)
            .exists()
        )
        if not other_owners:
            raise CannotLeave
    membership.delete()


def _deletion_order(tenant):
    """Querysets to delete one after the other: what protects something goes first."""
    credit_notes = Invoice.objects.filter(tenant=tenant, kind=Invoice.Kind.CREDIT_NOTE)
    return [
        Payment.objects.filter(tenant=tenant),
        credit_notes,
        Invoice.objects.filter(tenant=tenant),
        Quote.objects.filter(tenant=tenant),
        Expense.objects.filter(tenant=tenant),
        Contract.objects.filter(tenant=tenant),
        Gig.objects.filter(tenant=tenant),  # roadmaps and crew go with their gig
        Contact.objects.filter(tenant=tenant),
        Promoter.objects.filter(tenant=tenant),
        Venue.objects.filter(tenant=tenant),
        Show.objects.filter(tenant=tenant),
    ]


def purge_tenant(tenant):
    """Delete the tenant, all its data and its stored files, for good.

    Django refuses to delete a tenant in one go because of the PROTECT links (an invoice
    protects its gig, a payment its invoice...). So the data goes in dependency order, on
    querysets: the model-level `delete()` guards on issued invoices are not involved.
    Files are removed only once the database change is committed. Users who belonged to no
    other tenant are deleted too (staff accounts are kept).
    """
    files = [(field.storage, field.name) for _path, field in stored_files(tenant)]
    with transaction.atomic():
        user_ids = list(tenant.memberships.values_list("user_id", flat=True))
        # A signed contract and its frozen version protect each other: break the loop first.
        Contract.objects.filter(tenant=tenant).update(signed_version=None)
        for queryset in _deletion_order(tenant):
            queryset.delete()
        tenant.delete()
        User.objects.filter(pk__in=user_ids, memberships__isnull=True, is_staff=False).delete()
    for storage, name in files:
        storage.delete(name)


def purge_due_tenants():
    """Purge the tenants whose grace period is over. Returns how many were deleted."""
    limit = timezone.now() - timedelta(days=DELETION_GRACE_DAYS)
    due = list(Tenant.objects.filter(deletion_requested_at__lte=limit))
    for tenant in due:
        purge_tenant(tenant)
    return len(due)


# --- team (F-06) ---------------------------------------------------------------------

ROLE_SUGGESTIONS = [
    "Chanteur",
    "Chanteuse",
    "Guitariste",
    "Bassiste",
    "Batteur",
    "Pianiste",
    "Claviériste",
    "Technicien son",
    "Technicien lumière",
    "Régisseur",
    "Chargé de production",
]
STATUS_SUGGESTIONS = ["Intermittent", "Salarié", "Auto-entrepreneur", "Bénévole", "Amateur"]


def team_suggestions(tenant, field, fixed):
    """The proposed values followed by those this tenant already typed, without case duplicates."""
    typed = (
        Person.objects.filter(tenant=tenant).exclude(**{field: ""}).values_list(field, flat=True)
    )
    merged = {}
    for value in [*fixed, *typed]:
        merged.setdefault(value.casefold(), value)
    return sorted(merged.values(), key=str.casefold)
