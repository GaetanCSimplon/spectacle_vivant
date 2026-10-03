import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.documents import invoicing
from apps.documents.models import ImmutableDocument, Invoice

from .. import services
from ..factories import ExpenseFactory
from ..models import Payment
from ..services import PaymentError
from .helpers import issued_invoice, make_gig

pytestmark = pytest.mark.django_db

D = Decimal
TODAY = datetime.date(2026, 10, 3)
TRANSFER = Payment.Method.TRANSFER


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _invoice(price="1000.00"):
    return issued_invoice(make_gig(price=price))


def _pay(invoice, amount):
    return services.record_payment(invoice, amount, TODAY, TRANSFER)


# --- recording ----------------------------------------------------------------


def test_a_partial_payment_keeps_the_invoice_issued():
    invoice = _invoice()

    payment = _pay(invoice, "400.00")

    assert invoice.status == Invoice.Status.ISSUED
    assert payment.tenant == invoice.tenant
    assert services.paid_amount(invoice) == D("400.00")
    assert services.remaining_to_pay(invoice) == D("600.00")


def test_paying_the_total_marks_the_invoice_paid():
    invoice = _invoice()

    _pay(invoice, "400.00")
    _pay(invoice, "600.00")

    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID
    assert services.remaining_to_pay(invoice) == 0


def test_amounts_are_exact_to_the_cent():
    invoice = _invoice("100.10")

    _pay(invoice, "50.05")
    assert invoice.status == Invoice.Status.ISSUED
    _pay(invoice, "50.05")

    assert invoice.status == Invoice.Status.PAID


def test_an_amount_is_rounded_to_the_cent():
    invoice = _invoice()

    payment = _pay(invoice, "10.005")

    assert payment.amount == D("10.01")


def test_overpaying_is_refused_and_nothing_is_saved():
    invoice = _invoice()
    _pay(invoice, "900.00")

    with pytest.raises(PaymentError, match="dépasse"):
        _pay(invoice, "100.01")

    assert Payment.objects.count() == 1
    assert invoice.status == Invoice.Status.ISSUED


@pytest.mark.parametrize("amount", ["0", "0.00", "-5.00", "0.004"])
def test_a_zero_or_negative_amount_is_refused(amount):
    with pytest.raises(PaymentError):
        _pay(_invoice(), amount)

    assert not Payment.objects.exists()


def test_a_paid_invoice_takes_no_more_payment():
    invoice = _invoice()
    _pay(invoice, "1000.00")

    with pytest.raises(PaymentError):
        _pay(invoice, "1.00")


def test_a_draft_cannot_be_paid():
    draft = invoicing.create_invoice(make_gig(), Invoice.Kind.FULL)

    with pytest.raises(PaymentError, match="émise"):
        _pay(draft, "10.00")


def test_a_credit_note_cannot_be_paid():
    invoice = _invoice()
    note = invoicing.issue_invoice(invoicing.create_credit_note(invoice))

    with pytest.raises(PaymentError, match="avoir"):
        _pay(note, "10.00")
    assert services.remaining_to_pay(note) == 0


def test_a_cancelled_invoice_takes_no_payment():
    invoice = _invoice()
    invoicing.issue_invoice(invoicing.create_credit_note(invoice))
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.CANCELLED

    with pytest.raises(PaymentError):
        _pay(invoice, "10.00")


def test_the_database_refuses_a_non_positive_amount():
    invoice = _invoice()

    with pytest.raises(IntegrityError), transaction.atomic():
        Payment.objects.create(
            tenant=invoice.tenant, invoice=invoice, amount=0, date=TODAY, method=TRANSFER
        )


# --- editing and deleting -----------------------------------------------------


def test_lowering_a_payment_puts_a_paid_invoice_back_to_issued():
    invoice = _invoice()
    payment = _pay(invoice, "1000.00")

    services.update_payment(payment, "900.00", TODAY, Payment.Method.CHEQUE)

    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.ISSUED
    payment.refresh_from_db()
    assert payment.amount == D("900.00")
    assert payment.method == Payment.Method.CHEQUE


def test_raising_a_payment_can_settle_the_invoice():
    invoice = _invoice()
    payment = _pay(invoice, "400.00")

    services.update_payment(payment, "1000.00", TODAY, TRANSFER)

    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID


def test_editing_cannot_overpay_counting_the_other_payments():
    invoice = _invoice()
    _pay(invoice, "600.00")
    payment = _pay(invoice, "100.00")

    with pytest.raises(PaymentError, match="dépasse"):
        services.update_payment(payment, "400.01", TODAY, TRANSFER)

    payment.refresh_from_db()
    assert payment.amount == D("100.00")


def test_editing_the_same_amount_is_fine_on_a_paid_invoice():
    invoice = _invoice()
    payment = _pay(invoice, "1000.00")

    services.update_payment(payment, "1000.00", datetime.date(2026, 10, 4), TRANSFER)

    assert invoice.status == Invoice.Status.PAID


def test_deleting_a_payment_reopens_a_paid_invoice():
    invoice = _invoice()
    payment = _pay(invoice, "1000.00")

    services.delete_payment(payment)

    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.ISSUED
    assert not Payment.objects.exists()


def test_a_paid_invoice_stays_immutable():
    invoice = _invoice()
    _pay(invoice, "1000.00")
    invoice.refresh_from_db()
    invoice.total_excl_tax = D("1.00")

    with pytest.raises(ImmutableDocument):
        invoice.save()


def test_a_paid_invoice_can_still_be_credited_and_stays_counted_as_invoiced():
    gig = make_gig(price="1000.00")
    invoice = issued_invoice(gig)
    _pay(invoice, "1000.00")
    invoice.refresh_from_db()

    assert invoicing.invoiced_excl_tax(gig) == D("1000.00")
    assert invoicing.creditable_amount(invoice) == D("1000.00")
    note = invoicing.issue_invoice(invoicing.create_credit_note(invoice))
    assert note.status == Invoice.Status.ISSUED
    assert invoicing.invoiced_excl_tax(gig) == 0


# --- balance of a gig ---------------------------------------------------------


def test_balance_keeps_planned_invoiced_and_received_apart():
    gig = make_gig(price="1000.00")
    invoice = issued_invoice(gig, Invoice.Kind.DEPOSIT)  # 30 %
    _pay(invoice, "100.00")
    ExpenseFactory(gig=gig, amount="40.50")
    ExpenseFactory(gig=gig, amount="9.50")

    balance = services.gig_balance(gig)

    assert balance.planned_excl_tax == D("1000.00")
    assert balance.planned_incl_tax == D("1000.00")  # franchise: no VAT
    assert balance.invoiced == D("300.00")
    assert balance.received == D("100.00")
    assert balance.outstanding == D("200.00")
    assert balance.spent == D("50.00")
    assert balance.result == D("50.00")


def test_balance_planned_amount_includes_vat_for_a_taxable_tenant():
    gig = make_gig(price="1000.00", vat_regime="taxable", vat_rate="20.00")

    assert services.gig_balance(gig).planned_incl_tax == D("1200.00")


def test_balance_counts_credit_notes_as_negative_invoicing():
    gig = make_gig(price="1000.00")
    invoice = issued_invoice(gig)
    invoicing.issue_invoice(invoicing.create_credit_note(invoice))

    assert services.gig_balance(gig).invoiced == 0


def test_balance_ignores_drafts():
    gig = make_gig()
    invoicing.create_invoice(gig, Invoice.Kind.FULL)

    assert services.gig_balance(gig).invoiced == 0


def test_an_empty_balance_is_zero():
    balance = services.gig_balance(make_gig())

    assert (balance.invoiced, balance.received, balance.spent, balance.result) == (0, 0, 0, 0)


def test_the_database_refuses_a_non_positive_expense():
    with pytest.raises(IntegrityError), transaction.atomic():
        ExpenseFactory(amount=0)
