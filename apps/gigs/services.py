import calendar
import datetime
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import BooleanField, Exists, ExpressionWrapper, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show
from apps.documents.models import Contract, ContractVersion, Invoice, Quote
from apps.finance.models import Expense

from .models import Gig, PriceChange


def get_wizard_related_objects(tenant, data):
    """Fetch the Show/Promoter/Venue chosen in the wizard, scoped to the tenant."""
    show = get_object_or_404(Show, pk=data["show_id"], tenant=tenant)
    promoter = get_object_or_404(Promoter, pk=data["promoter_id"], tenant=tenant)
    venue = get_object_or_404(Venue, pk=data["venue_id"], tenant=tenant)
    return show, promoter, venue


def create_gig_from_wizard_data(tenant, data, user=None):
    show, promoter, venue = get_wizard_related_objects(tenant, data)
    with transaction.atomic():
        gig = Gig.objects.create(
            tenant=tenant,
            show=show,
            promoter=promoter,
            venue=venue,
            date=data["date"],
            option_expires_on=data.get("option_expires_on") or None,
            price=data["price"],
            conditions=data.get("conditions", ""),
        )
        PriceChange.objects.create(
            tenant=tenant, gig=gig, old_price=None, new_price=gig.price, changed_by=user
        )
    return gig


def count_gigs_for_year(tenant, year):
    """Number of gigs dated in `year`, cancelled ones excluded (prepares the freemium quota)."""
    return (
        Gig.objects.filter(tenant=tenant, date__year=year)
        .exclude(status=Gig.Status.CANCELLED)
        .count()
    )


CALENDAR_YEARS = range(2000, 2101)


def parse_month(value, today=None):
    """First day of the month in "YYYY-MM", or of the current month if it is missing or odd."""
    today = today or timezone.localdate()
    try:
        month = datetime.datetime.strptime(value, "%Y-%m").date()
    except (TypeError, ValueError):
        return today.replace(day=1)
    return month if month.year in CALENDAR_YEARS else today.replace(day=1)


def build_month_grid(month_start, gigs):
    """Weeks (Monday first) of `month_start`'s month, each day carrying its gigs.

    Days of the neighbouring months only fill the first and last weeks: they are
    marked `in_month=False` and never carry gigs.
    """
    by_day = defaultdict(list)
    for gig in gigs:
        by_day[gig.date].append(gig)
    today = timezone.localdate()
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
        month_start.year, month_start.month
    )
    return [
        [
            {
                "date": day,
                "in_month": day.month == month_start.month,
                "is_today": day == today,
                "gigs": by_day.get(day, []) if day.month == month_start.month else [],
            }
            for day in week
        ]
        for week in weeks
    ]


class InvalidTransition(Exception):
    """Raised when a status change is not allowed from the gig's current status."""


# F-31: option -> confirmed -> signed, and any live status -> cancelled.
# A cancelled gig only comes back through reactivate_gig() (RG-04).
ALLOWED_TRANSITIONS = {
    Gig.Status.OPTION: {Gig.Status.CONFIRMED, Gig.Status.CANCELLED},
    Gig.Status.CONFIRMED: {Gig.Status.SIGNED, Gig.Status.CANCELLED},
    Gig.Status.SIGNED: {Gig.Status.CANCELLED},
    Gig.Status.CANCELLED: set(),
}


def _lock_gig(gig):
    # Re-read under a lock so a double click or two tabs cannot apply a stale transition.
    return Gig.objects.select_for_update().get(pk=gig.pk, tenant=gig.tenant)


def change_status(gig, new_status):
    """Move a gig to `new_status` if F-31 allows it, otherwise raise InvalidTransition."""
    with transaction.atomic():
        locked = _lock_gig(gig)
        if new_status not in ALLOWED_TRANSITIONS[locked.status]:
            raise InvalidTransition(
                _("Le passage de « %(old)s » à « %(new)s » n'est pas possible.")
                % {"old": locked.get_status_display(), "new": Gig.Status(new_status).label}
            )
        locked.status = new_status
        locked.save(update_fields=["status"])
    gig.status = new_status
    return gig


def reactivate_gig(gig):
    """Explicit reactivation of a cancelled gig: it goes back to `option` (RG-04).

    Exception: a gig whose contract is signed goes back to `signed`, since the frozen
    contract is still valid (RG-08).
    """
    with transaction.atomic():
        locked = _lock_gig(gig)
        if locked.status != Gig.Status.CANCELLED:
            raise InvalidTransition(_("Seule une date annulée peut être réactivée."))
        has_signed_contract = Contract.objects.filter(
            gig=locked, tenant=locked.tenant, status=Contract.Status.SIGNED
        ).exists()
        locked.status = Gig.Status.SIGNED if has_signed_contract else Gig.Status.OPTION
        locked.save(update_fields=["status"])
    gig.status = locked.status
    return gig


class CannotDelete(Exception):
    """Raised when a gig still carries legal or financial traces."""


def deletion_blockers(gig):
    """Plain-French reasons why this gig cannot be deleted (empty list = it can)."""
    scope = {"gig": gig, "tenant": gig.tenant}
    reasons = []
    if Invoice.objects.filter(**scope, status=Invoice.Status.ISSUED).exists():
        reasons.append(_("Une facture ou un avoir a été émis pour cette date."))
    if Quote.objects.filter(**scope, status=Quote.Status.ISSUED).exists():
        reasons.append(_("Un devis a été émis pour cette date."))
    if Contract.objects.filter(**scope, status=Contract.Status.SIGNED).exists():
        reasons.append(_("Le contrat de cession est signé."))
    if Expense.objects.filter(**scope).exists():
        reasons.append(_("Des dépenses sont enregistrées pour cette date."))
    return reasons


def delete_blank_gig(gig):
    """Delete a gig with no legal or financial trace, with its drafts, contract and roadmap.

    Re-checked under the gig lock; raises CannotDelete otherwise. Stored PDFs of the
    unsigned contract are removed from the storage once the transaction has succeeded.
    """
    files = []
    with transaction.atomic():
        locked = _lock_gig(gig)
        reasons = deletion_blockers(locked)
        if reasons:
            raise CannotDelete(reasons[0])
        for model in (Invoice, Quote):
            for draft in model.objects.filter(gig=locked, tenant=locked.tenant):
                draft.delete()
        versions = ContractVersion.objects.filter(contract__gig=locked, tenant=locked.tenant)
        files = [(v.pdf_file.storage, v.pdf_file.name) for v in versions if v.pdf_file]
        locked.delete()
    for storage, name in files:
        storage.delete(name)


class CannotChangePrice(Exception):
    """Raised when the price of a gig may not change (or the new price is not valid)."""


def price_blockers(gig):
    """Plain-French reasons why the price of this gig is locked (empty list = it can change)."""
    scope = {"gig": gig, "tenant": gig.tenant}
    reasons = []
    if gig.status == Gig.Status.CANCELLED:
        reasons.append(_("La date est annulée."))
    if Contract.objects.filter(**scope, status=Contract.Status.SIGNED).exists():
        reasons.append(_("Le contrat de cession est signé."))
    if Invoice.objects.filter(**scope).exclude(status=Invoice.Status.DRAFT).exists():
        reasons.append(_("Une facture ou un avoir a été émis pour cette date."))
    return reasons


def clean_price(value):
    """The price as a Decimal to the cent, or CannotChangePrice when it is not a valid amount."""
    try:
        price = Decimal(str(value).replace(",", ".").strip())
    except InvalidOperation:
        raise CannotChangePrice(_("Le prix doit être un nombre.")) from None
    if not price.is_finite() or price.quantize(Decimal("0.01")) != price:
        raise CannotChangePrice(_("Le prix s'écrit en euros, avec au plus deux décimales."))
    if price <= 0:
        raise CannotChangePrice(_("Le prix doit être supérieur à 0."))
    if price >= Decimal("1000000"):
        raise CannotChangePrice(_("Ce prix est trop élevé."))
    return price


def change_price(gig, new_price, user, note=""):
    """Set a new price HT on the gig and write it in the price history.

    Returns the new PriceChange, or None when the price is the same (nothing is written).
    """
    price = clean_price(new_price)
    with transaction.atomic():
        locked = _lock_gig(gig)
        reasons = price_blockers(locked)
        if reasons:
            raise CannotChangePrice(" ".join(str(reason) for reason in reasons))
        if locked.price == price:
            return None
        change = PriceChange.objects.create(
            tenant=locked.tenant,
            gig=locked,
            old_price=locked.price,
            new_price=price,
            changed_by=user,
            note=note.strip()[:255],
        )
        locked.price = price
        locked.save(update_fields=["price"])
    gig.price = price
    return change


def with_locks(queryset):
    """Annotate gigs with `price_locked` (`price_blockers` is not empty) and `terms_locked`."""
    signed = Contract.objects.filter(gig=OuterRef("pk"), status=Contract.Status.SIGNED)
    invoiced = Invoice.objects.filter(gig=OuterRef("pk")).exclude(status=Invoice.Status.DRAFT)
    return queryset.annotate(
        terms_locked=Exists(signed),
        price_locked=ExpressionWrapper(
            Q(status=Gig.Status.CANCELLED) | Q(Exists(signed)) | Q(Exists(invoiced)),
            output_field=BooleanField(),
        ),
    )


class CannotChangeTerms(Exception):
    """Raised when the payment terms of a gig may not change."""


def update_terms(gig, deposit_due_on, balance_due_on, payment_method):
    """Set the payment terms printed in the contract (refused once the contract is signed)."""
    with transaction.atomic():
        locked = _lock_gig(gig)
        if Contract.objects.filter(
            gig=locked, tenant=locked.tenant, status=Contract.Status.SIGNED
        ).exists():
            raise CannotChangeTerms(
                _("Ce contrat est signé : ses informations ne peuvent plus être modifiées.")
            )
        locked.deposit_due_on = deposit_due_on
        locked.balance_due_on = balance_due_on
        locked.payment_method = payment_method
        locked.save(update_fields=["deposit_due_on", "balance_due_on", "payment_method"])
    gig.deposit_due_on = deposit_due_on
    gig.balance_due_on = balance_due_on
    gig.payment_method = payment_method
    return gig
