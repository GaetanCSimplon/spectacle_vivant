"""Payments, expenses and the balance of a gig (CLAUDE.md §6.2: Decimal only, cents exact).

Expected, invoiced and received amounts are three different figures and stay separate (F-57).
"""

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from apps.documents import invoicing
from apps.documents.models import Invoice

from .models import Expense, Payment

ZERO = invoicing.ZERO
PAYABLE = (Invoice.Status.ISSUED, Invoice.Status.PAID)
# What counts as invoiced: everything issued, credit notes included (they are negative).
INVOICED = (Invoice.Status.ISSUED, Invoice.Status.PAID, Invoice.Status.CANCELLED)


class PaymentError(Exception):
    """A payment action is refused; the first argument is a message for the user."""


def _total(queryset):
    return queryset.aggregate(total=Sum("amount"))["total"] or ZERO


def paid_amount(invoice):
    return _total(Payment.objects.filter(invoice=invoice, tenant=invoice.tenant))


def remaining_to_pay(invoice):
    """What is still due on an invoice (incl. tax); zero when settled or not payable."""
    if invoice.kind == Invoice.Kind.CREDIT_NOTE or invoice.status not in PAYABLE:
        return ZERO
    return max(invoice.total_incl_tax - paid_amount(invoice), ZERO)


# --- payments --------------------------------------------------------------


def _lock(invoice):
    return Invoice.objects.select_for_update().get(pk=invoice.pk, tenant=invoice.tenant)


def _require_payable(invoice):
    if invoice.kind == Invoice.Kind.CREDIT_NOTE:
        raise PaymentError(_("On n'enregistre pas de paiement sur un avoir."))
    if invoice.status not in PAYABLE:
        raise PaymentError(_("Seule une facture émise peut recevoir un paiement."))


def _check_amount(invoice, amount, other_payments_total):
    amount = invoicing.money(amount)
    if amount <= ZERO:
        raise PaymentError(_("Le montant doit être supérieur à zéro."))
    if amount > invoice.total_incl_tax - other_payments_total:
        raise PaymentError(_("Le paiement dépasse le reste à payer de la facture."))
    return amount


def _sync_status(invoice):
    """RG-09: `paid` exactly when the payments reach the total, back to `issued` otherwise."""
    if invoice.status not in PAYABLE:
        return
    settled = paid_amount(invoice) >= invoice.total_incl_tax
    status = Invoice.Status.PAID if settled else Invoice.Status.ISSUED
    if status != invoice.status:
        invoice.status = status
        invoice.save(update_fields=["status"])


def record_payment(invoice, amount, date, method):
    with transaction.atomic():
        locked = _lock(invoice)
        _require_payable(locked)
        amount = _check_amount(locked, amount, paid_amount(locked))
        payment = Payment.objects.create(
            tenant=locked.tenant, invoice=locked, amount=amount, date=date, method=method
        )
        _sync_status(locked)
    invoice.refresh_from_db(fields=["status"])
    return payment


def update_payment(payment, amount, date, method):
    with transaction.atomic():
        locked = _lock(payment.invoice)
        _require_payable(locked)
        others = paid_amount(locked) - payment.amount
        payment.amount = _check_amount(locked, amount, others)
        payment.date = date
        payment.method = method
        payment.save()
        _sync_status(locked)
    payment.invoice.refresh_from_db(fields=["status"])
    return payment


def delete_payment(payment):
    with transaction.atomic():
        locked = _lock(payment.invoice)
        payment.delete()
        _sync_status(locked)
    payment.invoice.refresh_from_db(fields=["status"])


# --- balance of a gig ------------------------------------------------------


@dataclass(frozen=True)
class GigBalance:
    """All amounts incl. tax so they can be compared (F-57); `planned_excl_tax` is the price."""

    planned_excl_tax: Decimal
    planned_incl_tax: Decimal
    invoiced: Decimal
    received: Decimal
    spent: Decimal

    @property
    def outstanding(self):
        return self.invoiced - self.received

    @property
    def result(self):
        return self.received - self.spent


def gig_balance(gig):
    rate = invoicing.vat_rate_for(gig.tenant)
    invoices = Invoice.objects.filter(gig=gig, tenant=gig.tenant, status__in=INVOICED)
    return GigBalance(
        planned_excl_tax=gig.price,
        planned_incl_tax=invoicing.money(gig.price * (100 + rate) / 100),
        invoiced=sum((i.total_incl_tax for i in invoices), ZERO),
        received=_total(Payment.objects.filter(invoice__gig=gig, tenant=gig.tenant)),
        spent=_total(Expense.objects.filter(gig=gig, tenant=gig.tenant)),
    )


# --- expenses --------------------------------------------------------------


def _delete_file(name):
    if name:
        Expense._meta.get_field("receipt_file").storage.delete(name)


def save_expense(expense, previous_receipt=""):
    """Save an expense; a receipt it no longer uses is removed from the storage."""
    expense.save()
    if previous_receipt and previous_receipt != expense.receipt_file.name:
        _delete_file(previous_receipt)


def delete_expense(expense):
    name = expense.receipt_file.name
    expense.delete()
    _delete_file(name)
