import calendar
import datetime
from collections import defaultdict

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show

from .models import Gig


def get_wizard_related_objects(tenant, data):
    """Fetch the Show/Promoter/Venue chosen in the wizard, scoped to the tenant."""
    show = get_object_or_404(Show, pk=data["show_id"], tenant=tenant)
    promoter = get_object_or_404(Promoter, pk=data["promoter_id"], tenant=tenant)
    venue = get_object_or_404(Venue, pk=data["venue_id"], tenant=tenant)
    return show, promoter, venue


def create_gig_from_wizard_data(tenant, data):
    show, promoter, venue = get_wizard_related_objects(tenant, data)
    return Gig.objects.create(
        tenant=tenant,
        show=show,
        promoter=promoter,
        venue=venue,
        date=data["date"],
        option_expires_on=data.get("option_expires_on") or None,
        price=data["price"],
        conditions=data.get("conditions", ""),
    )


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
    """Explicit reactivation of a cancelled gig: it goes back to `option` (RG-04)."""
    with transaction.atomic():
        locked = _lock_gig(gig)
        if locked.status != Gig.Status.CANCELLED:
            raise InvalidTransition(_("Seule une date annulée peut être réactivée."))
        locked.status = Gig.Status.OPTION
        locked.save(update_fields=["status"])
    gig.status = Gig.Status.OPTION
    return gig
