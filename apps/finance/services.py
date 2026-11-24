"""Payments, expenses and the balance of a gig (CLAUDE.md §6.2: Decimal only, cents exact).

Expected, invoiced and received amounts are three different figures and stay separate (F-57).
"""

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.documents import invoicing
from apps.documents.models import Invoice
from apps.gigs.models import Gig, GigMember

from .models import Expense, ExpenseClaim, Payment

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


def remaining_planned(planned_excl_tax, spent):
    """ "Reste prévu": the price (excl. tax) minus the expenses. The only place this is computed."""
    return planned_excl_tax - spent


def remaining_real(received, spent):
    """ "Reste réel": what was received minus what was spent. The only place this is computed."""
    return received - spent


@dataclass(frozen=True)
class GigBalance:
    """All amounts incl. tax so they can be compared (F-57); `planned_excl_tax` is the price."""

    planned_excl_tax: Decimal
    planned_incl_tax: Decimal
    invoiced: Decimal
    received: Decimal
    entered: Decimal  # expenses typed in for the date
    fees: Decimal  # gross pay of the team members of the date (not an expense row)
    fees_double_count: bool = False  # a "Cachets" expense exists next to the team fees
    fees_employer_cost: Decimal = ZERO  # estimation only: information, never added to `spent`

    @property
    def spent(self):
        return self.entered + self.fees

    @property
    def outstanding(self):
        return self.invoiced - self.received

    @property
    def remaining_planned(self):
        return remaining_planned(self.planned_excl_tax, self.spent)

    @property
    def result(self):
        return remaining_real(self.received, self.spent)


def team_fees_by_gig(tenant, gig_ids):
    """Gross pay of the team per gig id, cancelled gigs left out (owner only: private)."""
    rows = (
        GigMember.objects.filter(tenant=tenant, gig_id__in=gig_ids)
        .exclude(gig__status=Gig.Status.CANCELLED)
        .values("gig_id")
        .annotate(total=Sum("cachet_amount"))
    )
    return {row["gig_id"]: row["total"] for row in rows if row["total"]}


def gig_balance(gig, with_fees=True):
    """`with_fees=False` for a plain member: the pay of the team is private (owner only)."""
    rate = invoicing.vat_rate_for(gig.tenant)
    invoices = Invoice.objects.filter(gig=gig, tenant=gig.tenant, status__in=INVOICED)
    expenses = Expense.objects.filter(gig=gig, tenant=gig.tenant)
    fees = ZERO
    if with_fees and gig.status != Gig.Status.CANCELLED:
        fees = (
            GigMember.objects.filter(gig=gig, tenant=gig.tenant).aggregate(
                total=Sum("cachet_amount")
            )["total"]
            or ZERO
        )
    return GigBalance(
        planned_excl_tax=gig.price,
        planned_incl_tax=invoicing.money(gig.price * (100 + rate) / 100),
        invoiced=sum((i.total_incl_tax for i in invoices), ZERO),
        received=_total(Payment.objects.filter(invoice__gig=gig, tenant=gig.tenant)),
        entered=_total(expenses),
        fees=fees,
        fees_double_count=fees > 0 and expenses.filter(category=Expense.Category.FEES).exists(),
        fees_employer_cost=estimated_employer_cost(fees, gig.tenant.employer_cost_rate) or ZERO,
    )


def estimated_employer_cost(gross, rate):
    """Gross pay + reference rate, to the cent ("estimation" in the UI); None if no gross."""
    if gross is None:
        return None
    return invoicing.money(Decimal(gross) * (1 + Decimal(rate)))


# --- expenses --------------------------------------------------------------


def expense_split(expenses):
    """What the structure paid itself, what members advanced, and what it still owes them."""
    totals = expenses.aggregate(
        structure=Sum("amount", filter=Q(person__isnull=True)),
        members=Sum("amount", filter=Q(person__isnull=False)),
        to_reimburse=Sum("amount", filter=Q(person__isnull=False, reimbursed_on__isnull=True)),
    )
    return {key: value or ZERO for key, value in totals.items()}


def set_reimbursed(expense, done):
    """Mark a member's expense as paid back today, or take the mark off (a slip of the finger)."""
    if expense.person_id is None:
        raise ValueError("Only an expense made by a member can be reimbursed.")
    expense.reimbursed_on = timezone.localdate() if done else None
    expense.save(update_fields=["reimbursed_on"])


MAX_PENDING_CLAIMS = 20


class ClaimError(Exception):
    """A claim action is refused; the first argument is a message for the user."""


def submit_claim(claim):
    """Save a new claim of a team member, unless they already have too many waiting."""
    waiting = ExpenseClaim.objects.filter(
        tenant=claim.tenant, person=claim.person, status=ExpenseClaim.Status.PENDING
    ).count()
    if waiting >= MAX_PENDING_CLAIMS:
        raise ClaimError(
            _("Vous avez déjà %(n)s dépenses en attente : attendez qu'elles soient validées.")
            % {"n": MAX_PENDING_CLAIMS}
        )
    claim.save()
    return claim


def save_claim(claim, previous_receipt=""):
    """Save an edited pending claim; a receipt it no longer uses is removed from the storage."""
    claim.save()
    if previous_receipt and previous_receipt != claim.receipt_file.name:
        _delete_file(previous_receipt)


def withdraw_claim(claim):
    """The member takes a pending proposal back."""
    name = claim.receipt_file.name
    claim.delete()
    _delete_file(name)


@transaction.atomic
def accept_claim(claim):
    """The owner accepts: the proposal becomes an expense made by this member (to reimburse)."""
    claim = ExpenseClaim.objects.select_for_update().get(pk=claim.pk, tenant=claim.tenant)
    if not claim.is_pending:
        raise ClaimError(_("Cette proposition a déjà été traitée."))
    expense = Expense(
        tenant=claim.tenant,
        gig=claim.gig,
        category=claim.category,
        label=claim.label,
        amount=claim.amount,
        date=claim.date,
        person=claim.person,
    )
    if claim.receipt_file:
        expense.receipt_file = claim.receipt_file.name  # the file moves, it is not copied
    expense.save()
    claim.status = ExpenseClaim.Status.ACCEPTED
    claim.decided_at = timezone.now()
    claim.expense = expense
    claim.receipt_file = ""
    claim.save()
    return expense


@transaction.atomic
def refuse_claim(claim):
    claim = ExpenseClaim.objects.select_for_update().get(pk=claim.pk, tenant=claim.tenant)
    if not claim.is_pending:
        raise ClaimError(_("Cette proposition a déjà été traitée."))
    name = claim.receipt_file.name
    claim.status = ExpenseClaim.Status.REFUSED
    claim.decided_at = timezone.now()
    claim.receipt_file = ""  # nothing to keep once it is refused
    claim.save()
    transaction.on_commit(lambda: _delete_file(name))


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
