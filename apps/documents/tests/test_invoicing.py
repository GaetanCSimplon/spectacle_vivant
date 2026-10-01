import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.gigs.factories import GigFactory
from apps.tenants.factories import TenantFactory
from apps.tenants.models import Tenant

from .. import invoicing
from ..invoicing import InvoicingError
from ..models import (
    DocumentLine,
    DocumentSequence,
    ImmutableDocument,
    Invoice,
    Quote,
)

mark_isolation_tested(Invoice)
mark_isolation_tested(Quote)
mark_isolation_tested(DocumentLine)
mark_isolation_tested(DocumentSequence)

pytestmark = pytest.mark.django_db

YEAR = timezone.localdate().year
D = Decimal


def _gig(**tenant_fields):
    """A gig whose tenant and promoter have everything an invoice needs."""
    defaults = {
        "address": "1 rue des Arts, 69001 Lyon",
        "siret": "12345678900012",
        "vat_regime": Tenant.VatRegime.FRANCHISE,
        "iban": "FR1420041010050500013M02606",
    }
    defaults.update(tenant_fields)
    gig = GigFactory(
        price="1000.00",
        promoter__billing_address="3 place de la Mairie, 34000 Montpellier",
        **{f"tenant__{key}": value for key, value in defaults.items()},
    )
    gig.refresh_from_db()
    return gig


def _issued(gig=None, kind=Invoice.Kind.FULL, **kwargs):
    invoice = invoicing.create_invoice(gig or _gig(), kind, **kwargs)
    return invoicing.issue_invoice(invoice)


# --- amounts ---------------------------------------------------------------


class FakeLine:
    def __init__(self, quantity, price, vat):
        self.quantity, self.unit_price_excl_tax, self.vat_rate = D(quantity), D(price), D(vat)


def test_totals_of_a_single_line():
    assert invoicing.compute_totals([FakeLine(1, "500.00", "20")]) == (
        D("500.00"),
        D("100.00"),
        D("600.00"),
    )


def test_a_line_total_is_rounded_to_the_cent_half_up():
    # 3 x 0.335 = 1.005 -> 1.01 (and not 1.00 as banker's rounding would give)
    assert invoicing.compute_totals([FakeLine(3, "0.335", "0")])[0] == D("1.01")


def test_vat_is_computed_per_rate_on_the_sum_then_rounded():
    # Per line: 0.07 + 0.07 = 0.14. Per rate on the sum (0.66 x 10 %): 0.07.
    lines = [FakeLine(1, "0.33", "10"), FakeLine(1, "0.33", "10")]

    assert invoicing.compute_totals(lines) == (D("0.66"), D("0.07"), D("0.73"))


def test_several_vat_rates_are_added_up():
    lines = [FakeLine(1, "100.00", "5.5"), FakeLine(2, "50.00", "20")]

    ht, vat, ttc = invoicing.compute_totals(lines)

    assert (ht, vat, ttc) == (D("200.00"), D("25.50"), D("225.50"))


def test_no_lines_means_zero():
    assert invoicing.compute_totals([]) == (D("0.00"), D("0.00"), D("0.00"))


def test_a_negative_amount_mirrors_the_positive_one():
    positive = invoicing.compute_totals([FakeLine(1, "10.05", "5.5")])
    negative = invoicing.compute_totals([FakeLine(1, "-10.05", "5.5")])

    assert negative == tuple(-amount for amount in positive)


def test_a_tenant_without_vat_never_gets_a_line_with_vat():
    invoice = invoicing.create_invoice(_gig(), Invoice.Kind.FULL)

    line = invoicing.add_line(invoice, "Extra", "10.00", vat_rate="20")

    assert line.vat_rate == 0


def test_a_taxable_tenant_uses_its_rate_by_default_and_can_choose_another():
    gig = _gig(vat_regime="taxable", vat_rate="5.50", vat_number="FR12345678901")
    invoice = invoicing.create_invoice(gig, Invoice.Kind.FULL)

    other = invoicing.add_line(invoice, "Transport", "100.00", vat_rate="20")

    assert invoice.lines.first().vat_rate == D("5.50")
    assert other.vat_rate == D("20")
    invoice.refresh_from_db()
    assert invoice.total_excl_tax == D("1100.00")
    assert invoice.total_vat == D("75.00")
    assert invoice.total_incl_tax == D("1175.00")


def test_removing_a_line_updates_the_totals():
    invoice = invoicing.create_invoice(_gig(), Invoice.Kind.FULL)
    extra = invoicing.add_line(invoice, "Extra", "50.00")

    invoicing.remove_line(extra)

    invoice.refresh_from_db()
    assert invoice.total_excl_tax == D("1000.00")


# --- suggestions -----------------------------------------------------------


def test_deposit_suggestion_uses_the_gigs_percentage():
    gig = _gig()

    invoice = invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT)

    assert invoice.total_excl_tax == D("300.00")
    assert "Acompte de 30 %" in invoice.lines.first().label


def test_deposit_percentage_can_differ_per_gig_and_keeps_the_cents():
    gig = _gig()
    gig.deposit_percent = D("33.33")
    gig.save()

    invoice = invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT)

    assert invoice.total_excl_tax == D("333.30")
    assert "33,33 %" in invoice.lines.first().label or "33.33 %" in invoice.lines.first().label


def test_balance_suggestion_is_what_is_left_after_the_issued_deposit():
    gig = _gig()
    invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT))

    balance = invoicing.create_invoice(gig, Invoice.Kind.BALANCE)

    assert balance.total_excl_tax == D("700.00")


def test_a_draft_deposit_is_not_counted_as_invoiced():
    gig = _gig()
    invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT)

    balance = invoicing.create_invoice(gig, Invoice.Kind.BALANCE)

    assert balance.total_excl_tax == D("1000.00")


def test_nothing_left_to_invoice_suggests_zero():
    gig = _gig()
    _issued(gig)

    balance = invoicing.create_invoice(gig, Invoice.Kind.BALANCE)

    assert balance.total_excl_tax == D("0.00")


def test_a_credit_note_gives_the_amount_back_to_invoice():
    gig = _gig()
    invoice = _issued(gig)
    invoicing.issue_invoice(invoicing.create_credit_note(invoice))

    again = invoicing.create_invoice(gig, Invoice.Kind.FULL)

    assert again.total_excl_tax == D("1000.00")


def test_a_credit_note_cannot_be_created_directly():
    with pytest.raises(InvoicingError):
        invoicing.create_invoice(_gig(), Invoice.Kind.CREDIT_NOTE)


# --- issuing and snapshots -------------------------------------------------


def test_issuing_numbers_and_freezes_the_invoice():
    invoice = _issued()

    assert invoice.number == f"F-{YEAR}-0001"
    assert invoice.status == Invoice.Status.ISSUED
    assert invoice.issue_date == timezone.localdate()
    assert invoice.due_date == invoice.issue_date + datetime.timedelta(days=30)
    assert invoice.total_incl_tax == D("1000.00")
    saved = Invoice.objects.get(pk=invoice.pk)
    assert saved.number == invoice.number


def test_issuing_copies_the_legal_data_and_later_edits_do_not_change_it():
    gig = _gig()
    invoice = _issued(gig)
    gig.tenant.name = "Nouveau nom"
    gig.tenant.siret = "99999999999999"
    gig.tenant.save()
    gig.promoter.billing_address = "Ailleurs"
    gig.promoter.save()

    saved = Invoice.objects.get(pk=invoice.pk)

    assert saved.issuer_snapshot["name"] != "Nouveau nom"
    assert saved.issuer_snapshot["siret"] == "12345678900012"
    assert saved.issuer_snapshot["iban"] == "FR1420041010050500013M02606"
    assert saved.customer_snapshot["billing_address"] == "3 place de la Mairie, 34000 Montpellier"


def test_issuing_needs_at_least_one_line():
    invoice = invoicing.create_invoice(_gig(), Invoice.Kind.FULL, lines=[])

    with pytest.raises(InvoicingError):
        invoicing.issue_invoice(invoice)


def test_issuing_lists_what_is_missing():
    gig = GigFactory(price="100.00", tenant__vat_regime="taxable")
    invoice = invoicing.create_invoice(gig, Invoice.Kind.FULL)

    with pytest.raises(InvoicingError) as error:
        invoicing.issue_invoice(invoice)

    message = str(error.value.args[0])
    for item in (
        "adresse de votre structure",
        "SIRET",
        "numéro de TVA",
        "taux de TVA",
        "adresse de facturation",
    ):
        assert item in message
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.DRAFT
    assert invoice.number == ""
    assert not DocumentSequence.objects.exists()


def test_an_issued_invoice_cannot_be_issued_again():
    invoice = _issued()

    with pytest.raises(InvoicingError):
        invoicing.issue_invoice(invoice)

    assert DocumentSequence.objects.get().last_number == 1


# --- numbering (RG-05) -----------------------------------------------------


def test_numbers_follow_each_other_per_tenant():
    gig = _gig()

    numbers = [_issued(gig).number for _ in range(3)]

    assert numbers == [f"F-{YEAR}-0001", f"F-{YEAR}-0002", f"F-{YEAR}-0003"]


def test_each_tenant_has_its_own_numbering():
    _issued()

    assert _issued().number == f"F-{YEAR}-0001"


def test_numbering_restarts_each_year_and_keeps_the_old_one():
    tenant = TenantFactory()
    DocumentSequence.objects.create(tenant=tenant, kind="invoice", year=YEAR - 1, last_number=57)

    assert invoicing.next_document_number(tenant, "invoice") == f"F-{YEAR}-0001"
    assert DocumentSequence.objects.get(tenant=tenant, year=YEAR - 1).last_number == 57


def test_invoices_and_quotes_have_separate_series():
    gig = _gig()
    _issued(gig)

    quote = invoicing.issue_quote(invoicing.create_quote(gig))

    assert quote.number == f"D-{YEAR}-0001"


def test_a_failure_while_issuing_gives_the_number_back():
    gig = _gig()
    first = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    original = invoicing.build_customer_snapshot

    def boom(promoter):
        raise RuntimeError

    invoicing.build_customer_snapshot = boom
    try:
        with pytest.raises(RuntimeError):
            invoicing.issue_invoice(first)
    finally:
        invoicing.build_customer_snapshot = original

    first.refresh_from_db()
    assert first.number == ""
    assert _issued(gig).number == f"F-{YEAR}-0001"


def test_two_invoices_cannot_share_a_number_for_a_tenant():
    invoice = _issued()
    other = invoicing.create_invoice(invoice.gig, Invoice.Kind.FULL)

    with pytest.raises(IntegrityError), transaction.atomic():
        Invoice.objects.filter(pk=other.pk).update(number=invoice.number)


# --- immutability (RG-06) --------------------------------------------------


def test_an_issued_invoice_cannot_be_modified():
    invoice = _issued()
    invoice.total_excl_tax = D("1.00")

    with pytest.raises(ImmutableDocument):
        invoice.save()
    with pytest.raises(ImmutableDocument):
        invoice.save(update_fields=["total_excl_tax"])

    assert Invoice.objects.get(pk=invoice.pk).total_excl_tax == D("1000.00")


def test_an_issued_invoice_cannot_go_back_to_draft_or_be_deleted():
    invoice = _issued()

    invoice.status = Invoice.Status.DRAFT
    with pytest.raises(ImmutableDocument):
        invoice.save(update_fields=["status"])
    invoice.status = Invoice.Status.ISSUED
    with pytest.raises(ImmutableDocument):
        invoice.delete()

    assert Invoice.objects.filter(pk=invoice.pk, status="issued").exists()


def test_the_lines_of_an_issued_invoice_cannot_change():
    invoice = _issued()
    line = invoice.lines.get()

    line.unit_price_excl_tax = D("1.00")
    with pytest.raises(ImmutableDocument):
        line.save()
    with pytest.raises(ImmutableDocument):
        line.delete()
    with pytest.raises(InvoicingError):
        invoicing.add_line(invoice, "Sneaky", "1.00")
    with pytest.raises(InvoicingError):
        invoicing.remove_line(line)

    assert invoice.lines.get().unit_price_excl_tax == D("1000.00")


def test_an_issued_quote_is_frozen_too():
    quote = invoicing.issue_quote(invoicing.create_quote(_gig()))
    quote.total_excl_tax = D("1.00")

    with pytest.raises(ImmutableDocument):
        quote.save()
    with pytest.raises(ImmutableDocument):
        quote.delete()
    assert quote.valid_until == quote.issue_date + datetime.timedelta(days=30)


def test_a_draft_can_still_be_edited_and_deleted():
    invoice = invoicing.create_invoice(_gig(), Invoice.Kind.FULL)
    invoicing.add_line(invoice, "Extra", "10.00")

    invoice.delete()

    assert not Invoice.objects.exists()
    assert not DocumentLine.objects.exists()


# --- credit notes ----------------------------------------------------------


def test_a_credit_note_mirrors_the_invoice_and_shares_its_number_series():
    invoice = _issued(_gig(vat_regime="taxable", vat_rate="20", vat_number="FR1"))

    note = invoicing.issue_invoice(invoicing.create_credit_note(invoice))

    assert note.kind == Invoice.Kind.CREDIT_NOTE
    assert note.credit_note_of == invoice
    assert note.number == f"F-{YEAR}-0002"
    assert (note.total_excl_tax, note.total_vat, note.total_incl_tax) == (
        D("-1000.00"),
        D("-200.00"),
        D("-1200.00"),
    )
    assert note.due_date is None


def test_a_full_credit_note_cancels_the_invoice():
    invoice = _issued()

    invoicing.issue_invoice(invoicing.create_credit_note(invoice))

    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.CANCELLED


def test_a_partial_credit_note_keeps_the_invoice_issued():
    invoice = _issued()
    note = invoicing.create_credit_note(invoice)
    invoicing.remove_line(note.lines.get())
    invoicing.add_line(note, "Remise", "-100.00")

    invoicing.issue_invoice(note)

    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.ISSUED
    assert note.total_incl_tax == D("-100.00")


def test_credit_notes_cannot_exceed_the_invoice():
    invoice = _issued()
    first = invoicing.create_credit_note(invoice)
    second = invoicing.create_credit_note(invoice)
    invoicing.issue_invoice(first)

    with pytest.raises(InvoicingError):
        invoicing.issue_invoice(second)

    second.refresh_from_db()
    assert second.status == Invoice.Status.DRAFT
    assert second.number == ""


def test_a_credit_note_must_be_negative():
    invoice = _issued()
    note = invoicing.create_credit_note(invoice)
    invoicing.remove_line(note.lines.get())
    invoicing.add_line(note, "Oops", "5.00")

    with pytest.raises(InvoicingError):
        invoicing.issue_invoice(note)


def test_only_an_issued_invoice_can_get_a_credit_note():
    draft = invoicing.create_invoice(_gig(), Invoice.Kind.FULL)
    note = invoicing.issue_invoice(invoicing.create_credit_note(_issued()))

    with pytest.raises(InvoicingError):
        invoicing.create_credit_note(draft)
    with pytest.raises(InvoicingError):
        invoicing.create_credit_note(note)


def test_the_database_requires_a_link_for_credit_notes_and_only_for_them():
    gig = _gig()

    with pytest.raises(IntegrityError), transaction.atomic():
        Invoice.objects.create(tenant=gig.tenant, gig=gig, kind="credit_note")
    with pytest.raises(IntegrityError), transaction.atomic():
        Invoice.objects.create(tenant=gig.tenant, gig=gig, kind="full", credit_note_of=_issued(gig))


def test_a_line_belongs_to_exactly_one_document():
    gig = _gig()
    invoice = invoicing.create_invoice(gig, Invoice.Kind.FULL, lines=[])
    quote = invoicing.create_quote(gig, lines=[])

    with pytest.raises(IntegrityError), transaction.atomic():
        DocumentLine.objects.create(
            tenant=gig.tenant, label="x", unit_price_excl_tax=1, invoice=invoice, quote=quote
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        DocumentLine.objects.create(tenant=gig.tenant, label="x", unit_price_excl_tax=1)


# --- tenants ---------------------------------------------------------------


def test_documents_belong_to_the_gigs_tenant_and_do_not_mix():
    gig_a, gig_b = _gig(), _gig()
    invoice_a = _issued(gig_a)
    _issued(gig_b)
    quote_a = invoicing.issue_quote(invoicing.create_quote(gig_a))

    assert invoice_a.tenant == gig_a.tenant
    assert quote_a.tenant == gig_a.tenant
    assert list(Invoice.objects.filter(tenant=gig_a.tenant)) == [invoice_a]
    assert list(Quote.objects.filter(tenant=gig_a.tenant)) == [quote_a]
    assert DocumentLine.objects.filter(tenant=gig_a.tenant).count() == 2
    assert DocumentSequence.objects.filter(tenant=gig_a.tenant).count() == 2
    assert {line.tenant for line in DocumentLine.objects.filter(invoice=invoice_a)} == {
        gig_a.tenant
    }
