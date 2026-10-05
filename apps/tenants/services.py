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
from .models import Tenant

DELETION_GRACE_DAYS = 30


def create_tenant_for_user(user, **tenant_fields):
    """Create a Tenant and make `user` its owner, atomically."""
    with transaction.atomic():
        tenant = Tenant.objects.create(**tenant_fields)
        Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.OWNER)
    return tenant


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
