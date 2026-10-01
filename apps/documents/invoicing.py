"""Quotes, invoices and credit notes: amounts, numbering, issuing.

All the money rules live here (CLAUDE.md §6.2): `Decimal` only, cents exact, numbers
without gaps, an issued document never changes, legal data copied at issue time.
"""

import datetime
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import Tenant

from .models import DocumentLine, DocumentSequence, Invoice, Quote

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
PAYMENT_DELAY_DAYS = 30
QUOTE_VALIDITY_DAYS = 30


class InvoicingError(Exception):
    """A quote or invoice action is refused; the first argument is a message for the user."""


def money(value):
    """Round to the cent, half up (away from zero, so a credit note mirrors its invoice)."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


# --- amounts ---------------------------------------------------------------


def line_total(line):
    return money(Decimal(line.quantity) * Decimal(line.unit_price_excl_tax))


def compute_totals(lines):
    """(total excl. tax, total VAT, total incl. tax) of lines.

    VAT is computed once per rate on the sum of the lines at that rate, then rounded,
    which is how an invoice is normally checked by hand.
    """
    by_rate = defaultdict(lambda: ZERO)
    for line in lines:
        by_rate[Decimal(line.vat_rate)] += line_total(line)
    total_excl_tax = sum(by_rate.values(), ZERO)
    total_vat = sum((money(base * rate / 100) for rate, base in by_rate.items()), ZERO)
    return total_excl_tax, total_vat, total_excl_tax + total_vat


def refresh_totals(document):
    """Recompute and store the totals of a draft from its lines."""
    lines = list(document.lines.all())
    document.total_excl_tax, document.total_vat, document.total_incl_tax = compute_totals(lines)
    document.save(update_fields=["total_excl_tax", "total_vat", "total_incl_tax"])


def vat_rate_for(tenant, requested=None):
    """A tenant that does not charge VAT never has a line with VAT."""
    if tenant.vat_regime != Tenant.VatRegime.TAXABLE:
        return ZERO
    if requested is not None:
        return Decimal(requested)
    return Decimal(tenant.vat_rate) if tenant.vat_rate is not None else ZERO


# --- lines of a draft ------------------------------------------------------


def _require_draft(document):
    if not document.is_draft:
        raise InvoicingError(_("Seul un brouillon peut être modifié."))


def add_line(document, label, unit_price_excl_tax, quantity=1, vat_rate=None):
    _require_draft(document)
    with transaction.atomic():
        position = document.lines.count()
        line = DocumentLine(
            tenant=document.tenant,
            position=position,
            label=label,
            quantity=Decimal(quantity),
            unit_price_excl_tax=money(unit_price_excl_tax),
            vat_rate=vat_rate_for(document.tenant, vat_rate),
        )
        setattr(line, "invoice" if isinstance(document, Invoice) else "quote", document)
        line.save()
        refresh_totals(document)
    return line


def update_line(line, label, unit_price_excl_tax, quantity=1, vat_rate=None):
    document = line.parent
    _require_draft(document)
    with transaction.atomic():
        line.label = label
        line.quantity = Decimal(quantity)
        line.unit_price_excl_tax = money(unit_price_excl_tax)
        line.vat_rate = vat_rate_for(document.tenant, vat_rate)
        line.save()
        refresh_totals(document)
    return line


def remove_line(line):
    document = line.parent
    _require_draft(document)
    with transaction.atomic():
        line.delete()
        refresh_totals(document)


# --- creating drafts -------------------------------------------------------


def invoiced_excl_tax(gig):
    """Excl. tax total already invoiced for a gig (credit notes count as negative)."""
    issued = Invoice.objects.filter(
        gig=gig, tenant=gig.tenant, status__in=[Invoice.Status.ISSUED, Invoice.Status.CANCELLED]
    )
    return sum((invoice.total_excl_tax for invoice in issued), ZERO)


def suggest_lines(gig, kind):
    """Lines proposed for a new invoice: the deposit, or what is left to invoice.

    Only a suggestion: every line stays editable in the draft.
    """
    price = money(gig.price)
    percent = Decimal(str(gig.deposit_percent))
    remaining = max(price - invoiced_excl_tax(gig), ZERO)
    title = f"« {gig.show.title} » — {gig.date:%d/%m/%Y}"
    if kind == Invoice.Kind.DEPOSIT:
        amount = min(money(price * percent / 100), remaining)
        label = _("Acompte de %(percent)s %% — cession du spectacle %(title)s") % {
            "percent": f"{percent:.2f}".rstrip("0").rstrip("."),
            "title": title,
        }
    else:
        amount = remaining
        label = _("Cession du spectacle %(title)s") % {"title": title}
        if kind == Invoice.Kind.BALANCE:
            label = _("Solde — cession du spectacle %(title)s") % {"title": title}
    return [{"label": str(label), "unit_price_excl_tax": amount, "quantity": 1}]


def _create_with_lines(model, gig, lines, **fields):
    with transaction.atomic():
        document = model.objects.create(gig=gig, tenant=gig.tenant, **fields)
        for line in lines:
            add_line(document, **line)
    return document


def create_invoice(gig, kind, lines=None):
    """A draft invoice for a gig; without `lines`, the suggested ones are used."""
    if kind == Invoice.Kind.CREDIT_NOTE:
        raise InvoicingError(_("Un avoir se crée depuis la facture à corriger."))
    return _create_with_lines(
        Invoice, gig, suggest_lines(gig, kind) if lines is None else lines, kind=kind
    )


def create_quote(gig, lines=None):
    if lines is None:
        lines = [
            {
                "label": _("Cession du spectacle « %(title)s » — %(date)s")
                % {"title": gig.show.title, "date": f"{gig.date:%d/%m/%Y}"},
                "unit_price_excl_tax": gig.price,
            }
        ]
    return _create_with_lines(Quote, gig, lines)


def create_credit_note(invoice):
    """A draft credit note copying the lines of an issued invoice, with negative prices.

    It can be edited before issuing, for example to credit only part of the invoice.
    """
    if invoice.kind == Invoice.Kind.CREDIT_NOTE or invoice.status != Invoice.Status.ISSUED:
        raise InvoicingError(_("Seule une facture émise peut recevoir un avoir."))
    lines = [
        {
            "label": line.label,
            "quantity": line.quantity,
            "unit_price_excl_tax": -line.unit_price_excl_tax,
            "vat_rate": line.vat_rate,
        }
        for line in invoice.lines.all()
    ]
    return _create_with_lines(
        Invoice, invoice.gig, lines, kind=Invoice.Kind.CREDIT_NOTE, credit_note_of=invoice
    )


# --- issuing ---------------------------------------------------------------


def next_document_number(tenant, kind):
    """Next number of the year, e.g. F-2026-0007 (invoices and credit notes) or D-2026-0003.

    Must run in the transaction that issues the document: the sequence row is locked,
    and a rollback gives the number back, so there is never a gap (RG-05).
    """
    year = timezone.localdate().year
    DocumentSequence.objects.get_or_create(tenant=tenant, kind=kind, year=year)
    sequence = DocumentSequence.objects.select_for_update().get(tenant=tenant, kind=kind, year=year)
    sequence.last_number += 1
    sequence.save(update_fields=["last_number"])
    prefix = "F" if kind == DocumentSequence.Kind.INVOICE else "D"
    return f"{prefix}-{year}-{sequence.last_number:04d}"


def missing_issue_requirements(document):
    """What the user still has to fill in before the document can be issued."""
    tenant, promoter = document.tenant, document.gig.promoter
    missing = []
    if not tenant.address:
        missing.append(_("l'adresse de votre structure"))
    if not tenant.siret:
        missing.append(_("le SIRET de votre structure"))
    if tenant.vat_regime == Tenant.VatRegime.TAXABLE:
        if not tenant.vat_number:
            missing.append(_("votre numéro de TVA"))
        if tenant.vat_rate is None:
            missing.append(_("votre taux de TVA"))
    if not promoter.billing_address:
        missing.append(_("l'adresse de facturation de l'organisateur"))
    return missing


def build_issuer_snapshot(tenant):
    return {
        "name": tenant.name,
        "legal_form": tenant.legal_form,
        "address": tenant.address,
        "siret": tenant.siret,
        "vat_regime": tenant.vat_regime,
        "vat_number": tenant.vat_number,
        "iban": tenant.iban,
        "licence_number": tenant.licence_number,
        "representative_name": tenant.representative_name,
        "representative_role": tenant.representative_role,
    }


def build_customer_snapshot(promoter):
    return {
        "name": promoter.name,
        "billing_address": promoter.billing_address,
        "siret": promoter.siret,
        "email": promoter.email,
    }


def _lock(document):
    return type(document).objects.select_for_update().get(pk=document.pk, tenant=document.tenant)


def _issue(document):
    """Common part of issuing, to run inside a transaction on the locked document."""
    if not document.is_draft:
        raise InvoicingError(_("Ce document est déjà émis."))
    if not document.lines.exists():
        raise InvoicingError(_("Ajoutez au moins une ligne avant d'émettre."))
    missing = missing_issue_requirements(document)
    if missing:
        raise InvoicingError(
            _("Complétez d'abord : %(items)s.") % {"items": ", ".join(str(m) for m in missing)}
        )
    refresh_totals(document)
    document.issuer_snapshot = build_issuer_snapshot(document.tenant)
    document.customer_snapshot = build_customer_snapshot(document.gig.promoter)
    document.issue_date = timezone.localdate()


def issue_invoice(invoice):
    """Give the invoice (or credit note) its number, freeze its data and issue it."""
    with transaction.atomic():
        locked = _lock(invoice)
        original = None
        if locked.kind == Invoice.Kind.CREDIT_NOTE:
            original = _lock(locked.credit_note_of)
        _issue(locked)
        if original is not None:
            _check_credit_note(locked, original)
        else:
            locked.due_date = locked.due_date or locked.issue_date + datetime.timedelta(
                days=PAYMENT_DELAY_DAYS
            )
        locked.number = next_document_number(locked.tenant, DocumentSequence.Kind.INVOICE)
        locked.status = Invoice.Status.ISSUED
        locked.save()
        if original is not None and original.total_incl_tax + _credited(original) == ZERO:
            original.status = Invoice.Status.CANCELLED
            original.save(update_fields=["status"])
    _copy_state(invoice, locked)
    return invoice


def _credited(original):
    """Sum (negative) of the issued credit notes of an invoice."""
    notes = original.credit_notes.filter(status=Invoice.Status.ISSUED)
    return sum((note.total_incl_tax for note in notes), ZERO)


def creditable_amount(invoice):
    """What a new credit note could still give back (incl. tax), zero if nothing."""
    if invoice.kind == Invoice.Kind.CREDIT_NOTE or invoice.status != Invoice.Status.ISSUED:
        return ZERO
    return invoice.total_incl_tax + _credited(invoice)


def _check_credit_note(note, original):
    if original.status != Invoice.Status.ISSUED:
        raise InvoicingError(_("La facture d'origine n'est plus créditable."))
    if note.total_incl_tax >= ZERO:
        raise InvoicingError(_("Le montant d'un avoir doit être négatif."))
    if original.total_incl_tax + _credited(original) + note.total_incl_tax < ZERO:
        raise InvoicingError(_("Cet avoir dépasse le montant de la facture d'origine."))


def issue_quote(quote):
    with transaction.atomic():
        locked = _lock(quote)
        _issue(locked)
        locked.valid_until = locked.valid_until or locked.issue_date + datetime.timedelta(
            days=QUOTE_VALIDITY_DAYS
        )
        locked.number = next_document_number(locked.tenant, DocumentSequence.Kind.QUOTE)
        locked.status = Quote.Status.ISSUED
        locked.save()
    _copy_state(quote, locked)
    return quote


def _copy_state(target, source):
    """Bring the caller's object up to date with what was saved on the locked copy."""
    target.__dict__.update({k: v for k, v in source.__dict__.items() if k != "_state"})
