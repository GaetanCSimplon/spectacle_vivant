"""The "Documents" tab: every issued document of a tenant in one list.

Only documents that are final show up: issued quotes, invoices and credit notes, and signed
contracts. Drafts are left out (a draft quote or invoice has no number and no stored PDF).
"""

import datetime
from dataclasses import dataclass
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Contract, Invoice, Quote


class DocType:
    CONTRACT = "contract"
    QUOTE = "quote"
    INVOICE = "invoice"
    CREDIT_NOTE = "credit_note"

    CHOICES = [
        (CONTRACT, _("Contrats")),
        (QUOTE, _("Devis")),
        (INVOICE, _("Factures")),
        (CREDIT_NOTE, _("Avoirs")),
    ]
    LABELS = {
        CONTRACT: _("Contrat de cession"),
        QUOTE: _("Devis"),
        INVOICE: _("Facture"),
        CREDIT_NOTE: _("Avoir"),
    }


@dataclass
class LibraryRow:
    doc_type: str
    number: str
    date: datetime.date
    gig: object
    customer: str
    amount_incl_tax: Decimal | None
    status: str
    detail_url: str
    download_url: str

    @property
    def type_label(self):
        return DocType.LABELS[self.doc_type]


def _billing_row(document, doc_type, url_kind):
    kwargs = {"gig_id": document.gig_id, "doc_type": url_kind, "pk": document.pk}
    return LibraryRow(
        doc_type=doc_type,
        number=document.number,
        date=document.issue_date,
        gig=document.gig,
        customer=document.customer_snapshot.get("name") or document.gig.promoter.name,
        amount_incl_tax=document.total_incl_tax,
        status=document.get_status_display(),
        detail_url=reverse("documents:document-detail", kwargs=kwargs),
        download_url=reverse("documents:document-pdf", kwargs=kwargs),
    )


def _contract_row(contract):
    gig = contract.gig
    if contract.signed_pdf:
        download_url = reverse("documents:contract-signed-pdf", kwargs={"gig_id": gig.pk})
    else:
        number = contract.signed_version.number
        download_url = reverse(
            "documents:contract-version-download", kwargs={"gig_id": gig.pk, "number": number}
        )
    return LibraryRow(
        doc_type=DocType.CONTRACT,
        number=contract.reference,
        date=timezone.localtime(contract.signed_at).date(),
        gig=gig,
        customer=gig.promoter.name,
        amount_incl_tax=None,
        status=contract.get_status_display(),
        detail_url=reverse("documents:contract-history", kwargs={"gig_id": gig.pk}),
        download_url=download_url,
    )


def issued_documents(tenant, types=(), start=None, end=None, shows=()):
    """The issued documents of `tenant`, newest first.

    `types` (DocType values), `shows` (Show objects) and the days `start`/`end` (both included)
    are optional: an empty one filters nothing.
    """
    wanted = set(types) or {value for value, _label in DocType.CHOICES}
    rows = []

    def narrow(queryset, date_field):
        queryset = queryset.filter(tenant=tenant)
        if shows:
            queryset = queryset.filter(gig__show__in=shows)
        if start:
            queryset = queryset.filter(**{f"{date_field}__gte": start})
        if end:
            queryset = queryset.filter(**{f"{date_field}__lte": end})
        return queryset

    invoice_types = wanted & {DocType.INVOICE, DocType.CREDIT_NOTE}
    if invoice_types:
        invoices = narrow(
            Invoice.objects.exclude(status=Invoice.Status.DRAFT).select_related("gig__promoter"),
            "issue_date",
        )
        for invoice in invoices:
            is_credit_note = invoice.kind == Invoice.Kind.CREDIT_NOTE
            doc_type = DocType.CREDIT_NOTE if is_credit_note else DocType.INVOICE
            if doc_type in wanted:
                rows.append(_billing_row(invoice, doc_type, "factures"))
    if DocType.QUOTE in wanted:
        quotes = narrow(
            Quote.objects.exclude(status=Quote.Status.DRAFT).select_related("gig__promoter"),
            "issue_date",
        )
        rows += [_billing_row(quote, DocType.QUOTE, "devis") for quote in quotes]
    if DocType.CONTRACT in wanted:
        # `signed_at` is a moment: the period is read in the local day (Europe/Paris).
        contracts = narrow(
            Contract.objects.filter(
                status=Contract.Status.SIGNED, signed_version__isnull=False
            ).select_related("gig__promoter", "signed_version"),
            "signed_at__date",
        )
        rows += [_contract_row(contract) for contract in contracts]

    rows.sort(key=lambda row: (row.date, row.number), reverse=True)
    return rows
