"""What the home page shows (F-74): the year in money, what is still owed, what needs action.

Every figure is exact; rounding to whole euros is only done by the template (F-58).
"""

from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _

from apps.documents import invoicing
from apps.documents.models import Invoice
from apps.gigs.models import Gig

from .models import Payment
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


def next_gigs(tenant, today):
    gigs = list(
        Gig.objects.filter(tenant=tenant, date__gte=today)
        .exclude(status=Gig.Status.CANCELLED)
        .select_related("show", "venue", "promoter", "tenant")
        .order_by("date")[:NEXT_GIGS_LIMIT]
    )
    for gig in gigs:
        gig.payment_lines = gig_payment_lines(gig)
    return gigs


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


def build_dashboard(tenant, today):
    invoiced, received = year_totals(tenant, today.year)
    awaiting = awaiting_payment(tenant, today)
    return {
        "year": today.year,
        "invoiced_year": invoiced,
        "received_year": received,
        "awaiting": awaiting,
        "awaiting_total": sum((row["remaining"] for row in awaiting), ZERO),
        "overdue_count": sum(1 for row in awaiting if row["overdue"]),
        "gigs_without_contract": list(gigs_without_contract(tenant, today)),
        "next_gigs": next_gigs(tenant, today),
        "has_gigs": Gig.objects.filter(tenant=tenant).exists(),
    }
