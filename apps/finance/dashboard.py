"""What the home page shows (F-74): the year in money, what is still owed, what needs action.

Every figure is exact; rounding to whole euros is only done by the template (F-58).
"""

import datetime
from decimal import Decimal

from django.db.models import Count, DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.addressbook.services import pending_answers
from apps.catalog.models import Show
from apps.documents import invoicing
from apps.documents.models import Contract, Invoice
from apps.gigs import mail as gig_mail
from apps.gigs.models import OPTION_WARNING_DAYS, Gig
from apps.roadmaps.tour_requests import pending_requests

from .models import Expense, Payment
from .services import INVOICED, ZERO, team_fees_by_gig

NEXT_GIGS_LIMIT = 5


def _money_field():
    return DecimalField(max_digits=12, decimal_places=2)


def year_totals(tenant, year):
    """(invoiced, received) incl. tax over a calendar year (all years if None); credit notes < 0."""
    invoices = Invoice.objects.filter(tenant=tenant, status__in=INVOICED)
    payments = Payment.objects.filter(tenant=tenant)
    if year is not None:
        invoices = invoices.filter(issue_date__year=year)
        payments = payments.filter(date__year=year)
    invoiced = invoices.aggregate(total=Sum("total_incl_tax"))["total"]
    received = payments.aggregate(total=Sum("amount"))["total"]
    return invoiced or ZERO, received or ZERO


ALL_YEARS = "toutes"
YEARS_AHEAD = 2


def year_choices(tenant, today):
    """Years the home page can show: those with a date, this one and the next two (NAV-04)."""
    years = {today.year + offset for offset in range(YEARS_AHEAD + 1)}
    years.update(
        Gig.objects.filter(tenant=tenant).dates("date", "year").values_list("date__year", flat=True)
    )
    return sorted(years)


def parse_year(value, tenant, today):
    """The year asked for ("2027"); this year if unknown or not offered by `year_choices`."""
    try:
        year = int(value)
    except (TypeError, ValueError):
        return today.year
    return year if year in year_choices(tenant, today) else today.year


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
# A contract sent and still not signed after this many days is worth a reminder (DAT-07); after
# the second delay it is shown as urgent. Product choices, not legal deadlines.
CHASE_AFTER_DAYS = 7
CHASE_URGENT_DAYS = 14
# Three or more reminders of the same kind (contracts to write, to sign, receipts missing) become
# one line with a count: the list stays readable on a busy structure. Money and options stay
# one by one, they are urgent and few.
GROUP_FROM = 3


def _gig_label(gig):
    return f"{gig.date:%d/%m}"


def contracts_to_chase(tenant, today):
    """Contracts sent to the organiser a week ago or more and still not signed, oldest first.

    Cancelled dates and dates already played are left out. The mark "sent" is set by hand by the
    user (the app sends nothing), so this is the date they recorded.
    """
    cutoff = today - datetime.timedelta(days=CHASE_AFTER_DAYS)
    return list(
        Contract.objects.filter(
            tenant=tenant,
            status=Contract.Status.DRAFT,
            sent_at__isnull=False,
            sent_at__date__lte=cutoff,
            gig__status__in=(Gig.Status.OPTION, Gig.Status.CONFIRMED),
            gig__date__gte=today,
        )
        .select_related("gig__show", "gig__venue", "gig__promoter", "gig__tenant")
        .order_by("sent_at")
    )


def _chase_alert(contract, today):
    gig = contract.gig
    sent_on = timezone.localtime(contract.sent_at).date()
    waiting = (today - sent_on).days
    return {
        "level": "red" if waiting >= CHASE_URGENT_DAYS else "amber",
        "text": _("Date du %(date)s : contrat envoyé il y a %(n)s jours, pas encore signé")
        % {"date": _gig_label(gig), "n": waiting},
        "url": reverse("documents:contract-history", args=[gig.pk]),
        "action": {
            "label": _("Relancer"),
            "mailto": gig_mail.reminder_mail(gig, sent_on)["mailto"],
        },
    }


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

    no_contract = list(gigs_without_contract(tenant, today))
    if len(no_contract) >= GROUP_FROM:
        soonest = no_contract[0]  # ordered by date
        found.append(
            {
                "level": "amber",
                "text": _("%(n)s dates confirmées sans contrat (la plus proche : %(date)s)")
                % {"n": len(no_contract), "date": _gig_label(soonest)},
                "url": reverse("documents:contract-history", args=[soonest.pk]),
            }
        )
    else:
        for gig in no_contract:
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
    unsigned = list(unsigned)
    if len(unsigned) >= GROUP_FROM:
        soonest = unsigned[0]
        found.append(
            {
                "level": "amber",
                "text": _(
                    "%(n)s contrats à faire signer d'ici %(days)s jours (le plus proche : %(date)s)"
                )
                % {"n": len(unsigned), "days": UNSIGNED_CONTRACT_DAYS, "date": _gig_label(soonest)},
                "url": reverse("documents:contract-history", args=[soonest.pk]),
            }
        )
    else:
        for gig in unsigned:
            found.append(
                {
                    "level": "amber",
                    "text": _("Date du %(date)s : contrat à faire signer (dans %(n)s jour(s))")
                    % {"date": _gig_label(gig), "n": (gig.date - today).days},
                    "url": reverse("documents:contract-history", args=[gig.pk]),
                }
            )

    to_chase = contracts_to_chase(tenant, today)
    if len(to_chase) >= GROUP_FROM:
        oldest = to_chase[0]
        found.append(
            {
                "level": "amber",
                "text": _("%(n)s contrats envoyés depuis plus de %(days)s jours, pas signés")
                % {"n": len(to_chase), "days": CHASE_AFTER_DAYS},
                "url": reverse("documents:contract-history", args=[oldest.gig_id]),
            }
        )
    else:
        found += [_chase_alert(contract, today) for contract in to_chase]

    no_receipt = (
        Expense.objects.filter(tenant=tenant, receipt_file="")
        .values("gig_id", "gig__date")
        .annotate(n=Count("pk"))
        .order_by("-gig__date")
    )
    no_receipt = list(no_receipt)
    if len(no_receipt) >= GROUP_FROM:
        latest = no_receipt[0]  # ordered from the most recent date
        found.append(
            {
                "level": "amber",
                "text": _(
                    "%(n)s dépenses sans justificatif, sur %(dates)s dates "
                    "(la plus récente : %(date)s)"
                )
                % {
                    "n": sum(row["n"] for row in no_receipt),
                    "dates": len(no_receipt),
                    "date": f"{latest['gig__date']:%d/%m}",
                },
                "url": reverse("finance:page", args=[latest["gig_id"]]),
            }
        )
    else:
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

    for tour_request in pending_requests(tenant):
        found.append(
            {
                "level": "amber",
                "text": _("Date du %(date)s : l'organisateur a répondu à la régie de tournée")
                % {"date": f"{tour_request.gig.date:%d/%m}"},
                "url": reverse("roadmaps:tour-request-review", args=[tour_request.gig_id]),
            }
        )

    found.sort(key=lambda alert: alert["level"] != "red")  # stable: red first
    return {
        "items": found[:ALERT_LIMIT],
        "hidden": max(len(found) - ALERT_LIMIT, 0),
        "urgent": sum(1 for alert in found if alert["level"] == "red"),
    }


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


def year_overview(tenant, year, with_fees=False):
    """Planned against real money for the live gigs dated in `year`, all incl. tax (F-76).

    Cancelled gigs are left out. There is no planned expense yet: spent is what was recorded.
    """
    gigs = Gig.objects.filter(tenant=tenant).exclude(status=Gig.Status.CANCELLED)
    if year is not None:
        gigs = gigs.filter(date__year=year)
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
    if with_fees:  # team pay (owner only), as in the Budget of a date
        spent += sum(team_fees_by_gig(tenant, gigs.values_list("pk", flat=True)).values(), ZERO)
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


def build_dashboard(
    tenant, today, period=DEFAULT_PERIOD, year=None, all_years=False, with_fees=False
):
    """`year` is the year of the balance card (this year if None); `all_years` shows them all."""
    if period not in PERIODS:
        period = DEFAULT_PERIOD
    shown_year = None if all_years else (year or today.year)
    invoiced, received = year_totals(tenant, shown_year)
    awaiting = awaiting_payment(tenant, today)
    end = period_end(today, period)
    upcoming_count = _live_upcoming(tenant, today, end).count()
    return {
        "year": shown_year,
        "year_choices": year_choices(tenant, today),
        "all_years": all_years,
        "period": period,
        "periods": PERIODS,
        "period_end": end,
        "alerts": alerts(tenant, today, awaiting),
        "active_shows": active_shows_count(tenant, today),
        "upcoming_count": upcoming_count,
        "upcoming_hidden": max(upcoming_count - NEXT_GIGS_LIMIT, 0),
        "overview": year_overview(tenant, shown_year, with_fees),
        "invoiced_year": invoiced,
        "received_year": received,
        "awaiting": awaiting,
        "awaiting_total": sum((row["remaining"] for row in awaiting), ZERO),
        "overdue_count": sum(1 for row in awaiting if row["overdue"]),
        "gigs_without_contract": list(gigs_without_contract(tenant, today)),
        "next_gigs": next_gigs(tenant, today, end),
        "has_gigs": Gig.objects.filter(tenant=tenant).exists(),
    }
