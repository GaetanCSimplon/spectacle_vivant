"""What the home page shows (F-74): the year in money, what is still owed, what needs action.

Every figure is exact; rounding to whole euros is only done by the template (F-58).
"""

import datetime
from decimal import Decimal

from django.db.models import Count, DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.addressbook.services import pending_answers
from apps.catalog.models import Show
from apps.documents import invoicing
from apps.documents.models import Invoice
from apps.gigs.models import OPTION_WARNING_DAYS, Gig

from .models import Expense, Payment
from .services import INVOICED, ZERO

NEXT_GIGS_LIMIT = 5


def _money_field():
    return DecimalField(max_digits=12, decimal_places=2)


def year_totals(tenant, year):
    """(invoiced, received) incl. tax over a calendar year; credit notes count as negative."""
    invoiced = Invoice.objects.filter(
        tenant=tenant, status__in=INVOICED, issue_date__year=year
    ).aggregate(total=Sum("total_incl_tax"))["total"]
    received = Payment.objects.filter(tenant=tenant, date__year=year).aggregate(
        total=Sum("amount")
    )["total"]
    return invoiced or ZERO, received or ZERO


def awaiting_payment(tenant, today):
    """Issued invoices not fully paid, oldest due date first, with what is left to pay."""
    paid = (
        Payment.objects.filter(invoice=OuterRef("pk"), tenant=tenant)
        .values("invoice")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    invoices = (
        Invoice.objects.filter(tenant=tenant, status=Invoice.Status.ISSUED)
        .exclude(kind=Invoice.Kind.CREDIT_NOTE)
        .select_related("gig__show")
        .annotate(
            paid=Coalesce(
                Subquery(paid, output_field=_money_field()),
                Value(Decimal("0.00")),
                output_field=_money_field(),
            )
        )
        .order_by("due_date", "number")
    )
    rows = []
    for invoice in invoices:
        remaining = invoice.total_incl_tax - invoice.paid
        if remaining > 0:
            overdue = invoice.due_date is not None and invoice.due_date < today
            late_days = (today - invoice.due_date).days if overdue else 0
            rows.append(
                {
                    "invoice": invoice,
                    "gig": invoice.gig,
                    "remaining": remaining,
                    "overdue": overdue,
                    "late_days": late_days,
                }
            )
    return rows


def gigs_without_contract(tenant, today):
    """Confirmed upcoming gigs for which no contract has been generated yet."""
    return (
        Gig.objects.filter(tenant=tenant, status=Gig.Status.CONFIRMED, date__gte=today)
        .exclude(contract__versions__isnull=False)
        .select_related("show", "venue", "promoter")
        .order_by("date")
    )


PERIODS = {
    "semaine": _("Semaine"),
    "mois": _("Mois"),
    "annee": _("Année"),
}
DEFAULT_PERIOD = "mois"


def period_end(today, period):
    """Last day (included) of the current week, month or year; an unknown period means month."""
    if period == "semaine":
        return today + datetime.timedelta(days=6 - today.weekday())  # the coming Sunday
    if period == "annee":
        return datetime.date(today.year, 12, 31)
    next_month = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    return next_month - datetime.timedelta(days=1)


def _live_upcoming(tenant, today, end=None):
    gigs = Gig.objects.filter(tenant=tenant, date__gte=today).exclude(status=Gig.Status.CANCELLED)
    return gigs.filter(date__lte=end) if end else gigs


def next_gigs(tenant, today, end=None):
    """The first upcoming live gigs (up to `end` if given), each with its deposit/balance lines."""
    gigs = list(
        _live_upcoming(tenant, today, end)
        .select_related("show", "venue", "promoter", "tenant")
        .order_by("date")[:NEXT_GIGS_LIMIT]
    )
    for gig in gigs:
        gig.payment_lines = gig_payment_lines(gig)
    return gigs


def active_shows_count(tenant, today):
    """Shows with at least one live gig still to come."""
    live = (Gig.Status.OPTION, Gig.Status.CONFIRMED, Gig.Status.SIGNED)
    return (
        Show.objects.filter(tenant=tenant, gigs__date__gte=today, gigs__status__in=live)
        .distinct()
        .count()
    )


ALERT_LIMIT = 8
UNSIGNED_CONTRACT_DAYS = 14


def _gig_label(gig):
    return f"{gig.date:%d/%m}"


def alerts(tenant, today, awaiting=None):
    """What needs attention, most urgent first: [{"level": "red"|"amber", "text", "url"}].

    Options about to expire, confirmed gigs without a contract or with a contract still to
    sign, invoices past their due date, expenses without a receipt.
    """
    found = []

    options = Gig.objects.filter(
        tenant=tenant,
        status=Gig.Status.OPTION,
        option_expires_on__isnull=False,
        option_expires_on__lte=today + datetime.timedelta(days=OPTION_WARNING_DAYS),
    ).order_by("option_expires_on")
    for gig in options:
        days_left = (gig.option_expires_on - today).days
        if days_left < 0:
            text = _("Option du %(date)s : expirée depuis %(n)s jour(s)") % {
                "date": _gig_label(gig),
                "n": -days_left,
            }
        else:
            text = _("Option du %(date)s : expire dans %(n)s jour(s)") % {
                "date": _gig_label(gig),
                "n": days_left,
            }
        found.append(
            {
                "level": "red" if days_left <= 3 else "amber",
                "text": text,
                "url": reverse("gigs:detail", args=[gig.pk]),
            }
        )

    for row in awaiting if awaiting is not None else awaiting_payment(tenant, today):
        if row["overdue"]:
            found.append(
                {
                    "level": "red",
                    "text": _("Facture %(number)s en retard de %(n)s jour(s)")
                    % {"number": row["invoice"].number, "n": row["late_days"]},
                    "url": reverse("finance:page", args=[row["gig"].pk]),
                }
            )

    for gig in gigs_without_contract(tenant, today):
        found.append(
            {
                "level": "amber",
                "text": _("Date du %(date)s : contrat à générer") % {"date": _gig_label(gig)},
                "url": reverse("documents:contract-history", args=[gig.pk]),
            }
        )

    unsigned = (
        Gig.objects.filter(
            tenant=tenant,
            status=Gig.Status.CONFIRMED,
            date__range=(today, today + datetime.timedelta(days=UNSIGNED_CONTRACT_DAYS)),
            contract__versions__isnull=False,
        )
        .distinct()
        .order_by("date")
    )
    for gig in unsigned:
        found.append(
            {
                "level": "amber",
                "text": _("Date du %(date)s : contrat à faire signer (dans %(n)s jour(s))")
                % {"date": _gig_label(gig), "n": (gig.date - today).days},
                "url": reverse("documents:contract-history", args=[gig.pk]),
            }
        )

    no_receipt = (
        Expense.objects.filter(tenant=tenant, receipt_file="")
        .values("gig_id", "gig__date")
        .annotate(n=Count("pk"))
        .order_by("-gig__date")
    )
    for row in no_receipt:
        found.append(
            {
                "level": "amber",
                "text": _("Date du %(date)s : %(n)s dépense(s) sans justificatif")
                % {"date": f"{row['gig__date']:%d/%m}", "n": row["n"]},
                "url": reverse("finance:page", args=[row["gig_id"]]),
            }
        )

    for invitation in pending_answers(tenant):
        found.append(
            {
                "level": "amber",
                "text": _("%(name)s a répondu au formulaire : informations à vérifier")
                % {"name": invitation.promoter.name},
                "url": reverse("addressbook:promoter-answer", args=[invitation.promoter_id]),
            }
        )

    found.sort(key=lambda alert: alert["level"] != "red")  # stable: red first
    return {"items": found[:ALERT_LIMIT], "hidden": max(len(found) - ALERT_LIMIT, 0)}


def _payment_line(label, planned, invoices):
    """One deposit / balance / full invoice line: what is planned, invoiced or settled."""
    invoiced = sum((i.total_incl_tax for i in invoices), ZERO)
    if not invoices:
        return {"label": label, "state": "to_invoice", "amount": planned}
    paid = Payment.objects.filter(invoice__in=invoices).aggregate(total=Sum("amount"))["total"]
    paid = paid or ZERO
    if paid >= invoiced:
        return {"label": label, "state": "paid", "amount": invoiced}
    return {"label": label, "state": "to_collect", "amount": invoiced - paid}


def gig_payment_lines(gig):
    """Deposit and balance of a gig, incl. tax: to invoice, to collect or paid (F-76).

    A gig invoiced in one full invoice gets a single line. Planned amounts follow the
    gig's own terms (price and deposit percentage).
    """
    rate = invoicing.vat_rate_for(gig.tenant)
    planned_total = invoicing.money(gig.price * (100 + rate) / 100)
    deposit = invoicing.money(
        invoicing.money(gig.price * gig.deposit_percent / 100) * (100 + rate) / 100
    )
    deposit = min(deposit, planned_total)
    settled = Invoice.objects.filter(
        tenant=gig.tenant, gig=gig, status__in=(Invoice.Status.ISSUED, Invoice.Status.PAID)
    )

    def of_kind(kind):
        return [i for i in settled if i.kind == kind]

    full = of_kind(Invoice.Kind.FULL)
    if full:
        return [_payment_line(_("Facture totale"), planned_total, full)]
    return [
        _payment_line(_("Acompte"), deposit, of_kind(Invoice.Kind.DEPOSIT)),
        _payment_line(_("Solde"), planned_total - deposit, of_kind(Invoice.Kind.BALANCE)),
    ]


def year_overview(tenant, year):
    """Planned against real money for the live gigs dated in `year`, all incl. tax (F-76).

    Cancelled gigs are left out. There is no planned expense yet: spent is what was recorded.
    """
    gigs = Gig.objects.filter(tenant=tenant, date__year=year).exclude(status=Gig.Status.CANCELLED)
    rate = invoicing.vat_rate_for(tenant)
    planned = sum(
        (
            invoicing.money(price * (100 + rate) / 100)
            for price in gigs.values_list("price", flat=True)
        ),
        ZERO,
    )
    invoiced = Invoice.objects.filter(tenant=tenant, gig__in=gigs, status__in=INVOICED).aggregate(
        total=Sum("total_incl_tax")
    )["total"]
    received = Payment.objects.filter(tenant=tenant, invoice__gig__in=gigs).aggregate(
        total=Sum("amount")
    )["total"]
    spent = Expense.objects.filter(tenant=tenant, gig__in=gigs).aggregate(total=Sum("amount"))[
        "total"
    ]
    invoiced, received, spent = invoiced or ZERO, received or ZERO, spent or ZERO
    return {
        "gig_count": gigs.count(),
        "planned": planned,
        "invoiced": invoiced,
        "received": received,
        "spent": spent,
        "to_invoice": planned - invoiced,
        "to_collect": invoiced - received,
        "result": received - spent,
    }


def build_dashboard(tenant, today, period=DEFAULT_PERIOD):
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    invoiced, received = year_totals(tenant, today.year)
    awaiting = awaiting_payment(tenant, today)
    end = period_end(today, period)
    upcoming_count = _live_upcoming(tenant, today, end).count()
    return {
        "year": today.year,
        "period": period,
        "periods": PERIODS,
        "period_end": end,
        "alerts": alerts(tenant, today, awaiting),
        "active_shows": active_shows_count(tenant, today),
        "upcoming_count": upcoming_count,
        "upcoming_hidden": max(upcoming_count - NEXT_GIGS_LIMIT, 0),
        "overview": year_overview(tenant, today.year),
        "invoiced_year": invoiced,
        "received_year": received,
        "awaiting": awaiting,
        "awaiting_total": sum((row["remaining"] for row in awaiting), ZERO),
        "overdue_count": sum(1 for row in awaiting if row["overdue"]),
        "gigs_without_contract": list(gigs_without_contract(tenant, today)),
        "next_gigs": next_gigs(tenant, today, end),
        "has_gigs": Gig.objects.filter(tenant=tenant).exists(),
    }
