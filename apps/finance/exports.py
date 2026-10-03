"""CSV exports for the accountant or Excel (F-75): `;` separated, UTF-8 with BOM, French style.

Amounts keep their cents and use a decimal comma, dates are dd/mm/yyyy. Text coming from users
is neutralised against spreadsheet formulas (a cell starting with `=` would be executed).
"""

import csv
from decimal import Decimal

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse

from apps.documents.models import Invoice

from .models import Expense, Payment
from .services import PAYABLE, ZERO

BOM = "﻿"
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def text(value):
    """A user text as a safe cell."""
    value = str(value or "")
    return "'" + value if value.startswith(FORMULA_STARTS) else value


def amount(value):
    return f"{Decimal(value):.2f}".replace(".", ",")


def day(value):
    return value.strftime("%d/%m/%Y") if value else ""


def invoices_rows(tenant, start, end):
    header = [
        "Numéro",
        "Type",
        "Statut",
        "Date d'émission",
        "Échéance",
        "Spectacle",
        "Date du spectacle",
        "Client",
        "Total HT",
        "TVA",
        "Total TTC",
        "Encaissé",
        "Reste à payer",
    ]
    invoices = (
        Invoice.objects.filter(tenant=tenant, issue_date__range=(start, end))
        .exclude(status=Invoice.Status.DRAFT)
        .select_related("gig__show")
        .annotate(
            paid=Coalesce(
                Sum("payments__amount"),
                Value(ZERO),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        .order_by("issue_date", "number")
    )
    rows = []
    for invoice in invoices:
        payable = invoice.kind != Invoice.Kind.CREDIT_NOTE and invoice.status in PAYABLE
        remaining = max(invoice.total_incl_tax - invoice.paid, ZERO) if payable else ZERO
        rows.append(
            [
                text(invoice.number),
                invoice.get_kind_display(),
                invoice.get_status_display(),
                day(invoice.issue_date),
                day(invoice.due_date),
                text(invoice.gig.show.title),
                day(invoice.gig.date),
                text(invoice.customer_snapshot.get("name")),  # frozen at issue time
                amount(invoice.total_excl_tax),
                amount(invoice.total_vat),
                amount(invoice.total_incl_tax),
                amount(invoice.paid),
                amount(remaining),
            ]
        )
    return header, rows


def payments_rows(tenant, start, end):
    header = [
        "Date",
        "Mode",
        "Montant",
        "Facture",
        "Client",
        "Spectacle",
        "Date du spectacle",
    ]
    payments = (
        Payment.objects.filter(tenant=tenant, date__range=(start, end))
        .select_related("invoice__gig__show")
        .order_by("date", "id")
    )
    rows = [
        [
            day(p.date),
            p.get_method_display(),
            amount(p.amount),
            text(p.invoice.number),
            text(p.invoice.customer_snapshot.get("name")),
            text(p.invoice.gig.show.title),
            day(p.invoice.gig.date),
        ]
        for p in payments
    ]
    return header, rows


def expenses_rows(tenant, start, end):
    header = [
        "Date",
        "Catégorie",
        "Libellé",
        "Montant",
        "Spectacle",
        "Date du spectacle",
        "Justificatif",
    ]
    expenses = (
        Expense.objects.filter(tenant=tenant, date__range=(start, end))
        .select_related("gig__show")
        .order_by("date", "id")
    )
    rows = [
        [
            day(e.date),
            e.get_category_display(),
            text(e.label),
            amount(e.amount),
            text(e.gig.show.title),
            day(e.gig.date),
            "oui" if e.receipt_file else "non",
        ]
        for e in expenses
    ]
    return header, rows


# url slug -> (file name, builder)
EXPORTS = {
    "factures": ("factures", invoices_rows),
    "recettes": ("recettes", payments_rows),
    "depenses": ("depenses", expenses_rows),
}


def csv_response(kind, tenant, start, end):
    name, builder = EXPORTS[kind]
    header, rows = builder(tenant, start, end)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{name}-{start}_{end}.csv"'
    response.write(BOM)
    writer = csv.writer(response, delimiter=";", lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return response
