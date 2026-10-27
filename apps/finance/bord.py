"""The figures of the Bòrd page (see docs/produit/indicateurs-bord.md for every definition).

Reference dates: gig date (dates, planned), issue date (invoiced), reception date (received),
expense date (expenses), due date (late). "Still to collect" is a stock as of today: it only
follows the show filter, not the period. Everything is scoped to one tenant.
"""

import datetime
from dataclasses import dataclass

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Show
from apps.documents import invoicing
from apps.documents.models import Invoice, Quote
from apps.gigs.models import OPTION_WARNING_DAYS, Gig, GigMember

from .dashboard import awaiting_payment
from .models import Expense, ExpenseClaim, Payment
from .services import INVOICED, ZERO, expense_split

CONFIRMED = (Gig.Status.CONFIRMED, Gig.Status.SIGNED)
SOON_DAYS = 30
ATTENTION_LIMIT = 5

FIGURES = {
    "planned": _("Prévu (HT)"),
    "invoiced": _("Facturé (HT)"),
    "received": _("Encaissé (TTC)"),
}
DEFAULT_FIGURE = "planned"

STATUSES = {
    "pending": _("En attente"),
    "paid": _("Payé"),
    "cancelled": _("Annulé"),
}


@dataclass(frozen=True)
class Filters:
    """Period (both days included), optional show and the kind of figure to read."""

    start: datetime.date
    end: datetime.date
    show: Show | None = None
    figure: str = DEFAULT_FIGURE
    status: str = ""
    # "" = everyone, "structure" = what the structure paid, else the id of a team member.
    spender: str = ""


def period_bounds(preset, today):
    """First and last day (included) of the current month, quarter or year; month by default."""
    if preset == "annee":
        return datetime.date(today.year, 1, 1), datetime.date(today.year, 12, 31)
    if preset == "trimestre":
        first_month = 3 * ((today.month - 1) // 3) + 1
        start = datetime.date(today.year, first_month, 1)
        month_after = first_month + 3
    else:
        start = today.replace(day=1)
        month_after = today.month + 1
    year = today.year + (month_after - 1) // 12
    end = datetime.date(year, (month_after - 1) % 12 + 1, 1) - datetime.timedelta(days=1)
    return start, end


def _gigs(tenant, filters):
    gigs = Gig.objects.filter(tenant=tenant, date__range=(filters.start, filters.end))
    return gigs.filter(show=filters.show) if filters.show else gigs


def date_counts(tenant, filters):
    """Confirmed (confirmed or signed), options and cancelled gigs of the period, apart."""
    gigs = _gigs(tenant, filters)
    return {
        "confirmed": gigs.filter(status__in=CONFIRMED).count(),
        "options": gigs.filter(status=Gig.Status.OPTION).count(),
        "cancelled": gigs.filter(status=Gig.Status.CANCELLED).count(),
    }


def _revenue_querysets(tenant, filters):
    """The confirmed gigs, issued invoices and payments of the period (and of the show)."""
    gigs = _gigs(tenant, filters)
    invoices = Invoice.objects.filter(
        tenant=tenant,
        status__in=INVOICED,
        issue_date__range=(filters.start, filters.end),
    )
    payments = Payment.objects.filter(tenant=tenant, date__range=(filters.start, filters.end))
    if filters.show:
        invoices = invoices.filter(gig__show=filters.show)
        payments = payments.filter(invoice__gig__show=filters.show)
    return gigs, invoices, payments


def revenue(tenant, filters):
    """Planned and invoiced (excl. tax), received (incl. tax), and the options apart.

    Options are not a revenue yet: `options_planned` is what would be added if they were
    confirmed. Cancelled gigs are never planned.
    """
    gigs, invoices, payments = _revenue_querysets(tenant, filters)
    planned = gigs.filter(status__in=CONFIRMED).aggregate(total=Sum("price"))["total"]
    options = gigs.filter(status=Gig.Status.OPTION).aggregate(total=Sum("price"))["total"]
    return {
        "planned": planned or ZERO,
        "options_planned": options or ZERO,
        "invoiced": invoices.aggregate(total=Sum("total_excl_tax"))["total"] or ZERO,
        "received": payments.aggregate(total=Sum("amount"))["total"] or ZERO,
    }


def _expense_rows(tenant, filters):
    rows = Expense.objects.filter(tenant=tenant, date__range=(filters.start, filters.end))
    if filters.show:
        rows = rows.filter(gig__show=filters.show)
    if filters.spender == "structure":
        rows = rows.filter(person__isnull=True)
    elif filters.spender:
        rows = rows.filter(person_id=filters.spender)
    return rows


def pending_claims(tenant):
    """Expenses declared by team members and not yet accepted or refused (whatever the date)."""
    claims = list(
        ExpenseClaim.objects.filter(tenant=tenant, status=ExpenseClaim.Status.PENDING)
        .select_related("person", "gig__show")
        .order_by("created_at", "id")
    )
    return {"rows": claims, "total": sum((claim.amount for claim in claims), ZERO)}


def to_reimburse(tenant):
    """What the structure still owes its members, whatever the period: one row per member."""
    rows = (
        Expense.objects.filter(tenant=tenant, person__isnull=False, reimbursed_on__isnull=True)
        .values("person_id", "person__first_name", "person__last_name")
        .annotate(total=Sum("amount"))
        .order_by("person__last_name", "person__first_name")
    )
    people = [
        {
            "person_id": row["person_id"],
            "name": f"{row['person__first_name']} {row['person__last_name']}".strip(),
            "total": row["total"],
        }
        for row in rows
    ]
    return {"people": people, "total": sum((row["total"] for row in people), ZERO)}


def expenses(tenant, filters):
    """Expenses recorded in the period, by category (money really spent, as typed in)."""
    rows = _expense_rows(tenant, filters)
    by_category = [
        {"category": Expense.Category(row["category"]).label, "total": row["total"]}
        for row in rows.values("category").annotate(total=Sum("amount")).order_by("-total")
    ]
    largest = by_category[0]["total"] if by_category else ZERO
    for row in by_category:  # bar length, relative to the largest category
        row["percent"] = int(row["total"] * 100 / largest) if largest else 0
    return {
        "total": sum((row["total"] for row in by_category), ZERO),
        "by_category": by_category,
        "split": expense_split(rows),
    }


MAX_MONTHS = 36


def _months(start, end):
    """First day of every month from `start` to `end` (the last MAX_MONTHS at most)."""
    months, day = [], start.replace(day=1)
    while day <= end:
        months.append(day)
        day = (day + datetime.timedelta(days=32)).replace(day=1)
    return months[-MAX_MONTHS:]


def monthly_series(tenant, filters):
    """Revenue (of the chosen figure, by its own reference date) and expenses, month by month."""
    gigs, invoices, payments = _revenue_querysets(tenant, filters)
    revenue_rows = {
        "planned": gigs.filter(status__in=CONFIRMED).annotate(month=TruncMonth("date")),
        "invoiced": invoices.annotate(month=TruncMonth("issue_date")),
        "received": payments.annotate(month=TruncMonth("date")),
    }[filters.figure]
    amount_field = {"planned": "price", "invoiced": "total_excl_tax", "received": "amount"}[
        filters.figure
    ]
    spent = _expense_rows(tenant, filters)
    revenue_by_month = {
        row["month"]: row["total"]
        for row in revenue_rows.values("month").annotate(total=Sum(amount_field))
    }
    expenses_by_month = {
        row["month"]: row["total"]
        for row in spent.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
    }
    return [
        {
            "month": month,
            "label": f"{month:%m/%y}",
            "revenue": revenue_by_month.get(month, ZERO),
            "expenses": expenses_by_month.get(month, ZERO),
        }
        for month in _months(filters.start, filters.end)
    ]


def _nice_ceiling(value):
    """The smallest 1, 2, 5 or 10 times a power of ten that is at least `value` (min 1)."""
    if value <= 1:
        return 1
    magnitude = 10 ** (len(str(int(value))) - 1)
    for factor in (1, 2, 5, 10):
        if value <= factor * magnitude:
            return factor * magnitude
    return 10 * magnitude


def _money_label(value):
    return f"{int(value):,}".replace(",", "\u202f") + " €"


def monthly_chart(series, width=720, height=260):
    """Geometry of the grouped bars (revenue then expenses for each month), ready for an SVG.

    A negative month (credit notes) is drawn as an empty bar: the table next to the chart
    always gives the true figure.
    """
    left, right, top, bottom = 64, 8, 12, 30
    plot_w, plot_h = width - left - right, height - top - bottom
    ceiling = _nice_ceiling(
        max([row[key] for row in series for key in ("revenue", "expenses")] + [0])
    )
    group = plot_w / max(len(series), 1)
    bar_w = min(group * 0.38, 28)
    step = max(1, -(-len(series) // 12))  # at most about twelve month labels

    def bar(value, x):
        h = float(max(value, 0)) / ceiling * plot_h
        return {
            "x": round(x, 1),
            "y": round(top + plot_h - h, 1),
            "w": round(bar_w, 1),
            "h": round(h, 1),
        }

    groups = []
    for index, row in enumerate(series):
        centre = left + group * (index + 0.5)
        groups.append(
            {
                "label": row["label"],
                "show_label": index % step == 0,
                "label_x": round(centre, 1),
                "revenue": bar(row["revenue"], centre - bar_w - 1),
                "expenses": bar(row["expenses"], centre + 1),
            }
        )
    ticks = [
        {"y": round(top + plot_h - plot_h * fraction, 1), "label": _money_label(ceiling * fraction)}
        for fraction in (0, 0.5, 1)
    ]
    return {
        "width": width,
        "height": height,
        "left": left,
        "right_x": width - right,
        "label_y": height - 10,
        "groups": groups,
        "ticks": ticks,
        "has_data": any(row["revenue"] or row["expenses"] for row in series),
    }


def balance(revenue_totals, expense_totals, figure):
    """The chosen kind of revenue minus the recorded expenses. Never called "trésorerie"."""
    return revenue_totals[figure] - expense_totals["total"]


def receivables(tenant, today, show=None):
    """What is still to collect incl. tax on issued invoices, and how much of it is late."""
    rows = awaiting_payment(tenant, today)
    if show:
        rows = [row for row in rows if row["gig"].show_id == show.pk]
    return {
        "remaining": sum((row["remaining"] for row in rows), ZERO),
        "late": sum((row["remaining"] for row in rows if row["overdue"]), ZERO),
        "rows": rows,
    }


def people_mobilised(tenant, filters):
    """Distinct people travelling on the confirmed gigs of the period.

    A person picked from the team counts once however many gigs they play; a name typed by
    hand counts once too, unless it is the name of a team member already counted.
    """
    members = GigMember.objects.filter(
        tenant=tenant, gig__in=_gigs(tenant, filters).filter(status__in=CONFIRMED)
    )
    linked = {m.person_id for m in members if m.person_id}
    linked_names = {m.name.strip().casefold() for m in members if m.person_id}
    free_names = {
        m.name.strip().casefold()
        for m in members
        if not m.person_id and m.name.strip().casefold() not in linked_names
    }
    return len(linked) + len(free_names)


def _planned_incl_tax(gig):
    rate = invoicing.vat_rate_for(gig.tenant)
    return invoicing.money(gig.price * (100 + rate) / 100)


def operations(tenant, filters, limit=None):
    """One row per gig of the period: credit (the chosen figure), debit (its expenses), status
    and documents.

    Amounts are per gig, whatever the date of the invoice or of the payment. Status: cancelled
    = cancelled gig; paid = fully invoiced and every invoice settled; pending = the rest.
    """
    gigs = list(
        _gigs(tenant, filters)
        .select_related("show", "promoter", "venue", "tenant", "contract")
        .order_by("-date", "-pk")
    )
    ids = [gig.pk for gig in gigs]
    invoices = list(
        Invoice.objects.filter(tenant=tenant, gig_id__in=ids, status__in=INVOICED).order_by(
            "number"
        )
    )
    quotes = Quote.objects.filter(tenant=tenant, gig_id__in=ids, status=Quote.Status.ISSUED)
    paid_by_gig = {}
    for row in (
        Payment.objects.filter(tenant=tenant, invoice__gig_id__in=ids)
        .values("invoice__gig_id")
        .annotate(total=Sum("amount"))
    ):
        paid_by_gig[row["invoice__gig_id"]] = row["total"]

    spent_rows = Expense.objects.filter(tenant=tenant, gig_id__in=ids)
    if filters.spender == "structure":
        spent_rows = spent_rows.filter(person__isnull=True)
    elif filters.spender:
        spent_rows = spent_rows.filter(person_id=filters.spender)
    spent_by_gig = {
        row["gig_id"]: row["total"]
        for row in spent_rows.values("gig_id").annotate(total=Sum("amount"))
    }

    rows = []
    for gig in gigs:
        mine = [i for i in invoices if i.gig_id == gig.pk]
        invoiced_excl = sum((i.total_excl_tax for i in mine), ZERO)
        invoiced_incl = sum((i.total_incl_tax for i in mine), ZERO)
        received = paid_by_gig.get(gig.pk, ZERO)
        if gig.status == Gig.Status.CANCELLED:
            status = "cancelled"
        elif invoiced_incl >= _planned_incl_tax(gig) and received >= invoiced_incl:
            status = "paid"
        else:
            status = "pending"
        documents = []
        contract = getattr(gig, "contract", None)
        if contract is not None:
            documents.append(
                {
                    "label": _("Contrat"),
                    "url": reverse("documents:contract-history", args=[gig.pk]),
                }
            )
        for quote in (q for q in quotes if q.gig_id == gig.pk):
            documents.append(
                {
                    "label": f"{_('Devis')} {quote.number}",
                    "url": reverse("documents:document-detail", args=[gig.pk, "devis", quote.pk]),
                }
            )
        for invoice in mine:
            documents.append(
                {
                    "label": f"{invoice.get_kind_display()} {invoice.number}",
                    "url": reverse(
                        "documents:document-detail", args=[gig.pk, "factures", invoice.pk]
                    ),
                }
            )
        amount = {"planned": gig.price, "invoiced": invoiced_excl, "received": received}[
            filters.figure
        ]
        rows.append(
            {
                "gig": gig,
                "date": gig.date,
                "label": gig.show.title,
                "amount": amount,  # the credit: the figure chosen in the filters
                "debit": spent_by_gig.get(gig.pk, ZERO),  # every expense of the date
                "status": status,
                "documents": documents,
            }
        )
    if filters.status:
        rows = [row for row in rows if row["status"] == filters.status]
    return rows[:limit] if limit else rows


def upcoming(tenant, filters, today, limit=5):
    """The next live gigs from today on (options included, cancelled left out).

    Only the show filter applies: "next" does not depend on the chosen period.
    """
    gigs = Gig.objects.filter(tenant=tenant, date__gte=today).exclude(status=Gig.Status.CANCELLED)
    if filters.show:
        gigs = gigs.filter(show=filters.show)
    return list(gigs.select_related("show", "venue", "promoter").order_by("date", "pk")[:limit])


def _gig_text(gig):
    return f"{gig.date:%d/%m/%Y} — {gig.show.title}"


def attention(tenant, today):
    """ "À traiter maintenant": (the five most urgent items, how many there are in all).

    Each item says what, for which date or invoice, by when, how much, what to do and why.
    Thresholds are product choices (30 days, 7 days), not legal deadlines.
    """
    items = []
    soon = today + datetime.timedelta(days=SOON_DAYS)

    for row in awaiting_payment(tenant, today):
        if row["overdue"]:
            invoice = row["invoice"]
            items.append(
                {
                    "rank": 0,
                    "text": _("Facture %(number)s non réglée") % {"number": invoice.number},
                    "subject": _gig_text(row["gig"]),
                    "due": invoice.due_date,
                    "amount": row["remaining"],
                    "action": _("Enregistrer le paiement"),
                    "url": reverse("finance:page", args=[row["gig"].pk]),
                    "reason": _(
                        "Échéance dépassée de %(n)s jour(s), il reste de l'argent à encaisser."
                    )
                    % {"n": row["late_days"]},
                }
            )

    upcoming = Gig.objects.filter(
        tenant=tenant, status__in=CONFIRMED, date__gte=today, date__lte=soon
    ).select_related("show")
    for gig in upcoming.order_by("date"):
        if gig.status == Gig.Status.CONFIRMED:
            items.append(
                {
                    "rank": 1,
                    "text": _("Contrat à faire signer"),
                    "subject": _gig_text(gig),
                    "due": gig.date,
                    "amount": None,
                    "action": _("Ouvrir le contrat"),
                    "url": reverse("documents:contract-history", args=[gig.pk]),
                    "reason": _("Date confirmée dans moins de %(n)s jours, contrat non signé.")
                    % {"n": SOON_DAYS},
                }
            )
        if gig.deposit_due_on is None and gig.balance_due_on is None:
            items.append(
                {
                    "rank": 1,
                    "text": _("Échéances de paiement à renseigner"),
                    "subject": _gig_text(gig),
                    "due": gig.date,
                    "amount": None,
                    "action": _("Renseigner les échéances"),
                    "url": reverse("gigs:terms", args=[gig.pk]),
                    "reason": _("Date confirmée dans moins de %(n)s jours, aucune échéance.")
                    % {"n": SOON_DAYS},
                }
            )

    options = Gig.objects.filter(
        tenant=tenant,
        status=Gig.Status.OPTION,
        option_expires_on__isnull=False,
        option_expires_on__lte=today + datetime.timedelta(days=OPTION_WARNING_DAYS),
    ).select_related("show")
    for gig in options.order_by("option_expires_on"):
        left = (gig.option_expires_on - today).days
        items.append(
            {
                "rank": 2,
                "text": _("Option à confirmer ou libérer"),
                "subject": _gig_text(gig),
                "due": gig.option_expires_on,
                "amount": None,
                "action": _("Ouvrir la date"),
                "url": reverse("gigs:detail", args=[gig.pk]),
                "reason": _("L'option est expirée depuis %(n)s jour(s).") % {"n": -left}
                if left < 0
                else _("L'option expire dans %(n)s jour(s).") % {"n": left},
            }
        )

    items.sort(key=lambda item: (item["rank"], item["due"] or datetime.date.max))
    return items[:ATTENTION_LIMIT], len(items)


def incomplete_dates(tenant, filters):
    """Confirmed gigs of the period that still lack a signed contract or any payment term."""
    gigs = _gigs(tenant, filters).filter(status__in=CONFIRMED)
    return sum(
        1
        for gig in gigs
        if gig.status == Gig.Status.CONFIRMED
        or (gig.deposit_due_on is None and gig.balance_due_on is None)
    )


def summary(tenant, filters, today):
    """Everything the page shows, in one dict."""
    revenue_totals = revenue(tenant, filters)
    expense_totals = expenses(tenant, filters)
    attention_items, attention_total = attention(tenant, today)
    monthly = monthly_series(tenant, filters)
    return {
        "filters": filters,
        "dates": date_counts(tenant, filters),
        "revenue": revenue_totals,
        "expenses": expense_totals,
        "to_reimburse": to_reimburse(tenant),
        "claims": pending_claims(tenant),
        "balance": balance(revenue_totals, expense_totals, filters.figure),
        "receivables": receivables(tenant, today, filters.show),
        "people": people_mobilised(tenant, filters),
        "incomplete_dates": incomplete_dates(tenant, filters),
        "attention": attention_items,
        "attention_total": attention_total,
        "operations": operations(tenant, filters),
        "upcoming": upcoming(tenant, filters, today),
        "monthly": monthly,
        "chart": monthly_chart(monthly),
    }
