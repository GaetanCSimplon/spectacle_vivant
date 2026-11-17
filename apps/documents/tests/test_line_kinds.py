"""Spec v2 (PR 4): closed line kinds and units, the cession line of a quote, the balance invoice."""

import importlib
from decimal import Decimal

import pytest
from django.apps import apps as django_apps
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from .. import invoicing
from ..forms import DocumentLineForm
from ..models import KIND_UNITS, DocumentLine, Invoice, LineKind, LineUnit, Quote
from .test_billing_pdf import _gig, _text

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _kinds(document):
    return [line.kind for line in document.lines.all()]


# --- the closed list ----------------------------------------------------------------------------


def test_every_kind_has_units_and_every_unit_is_used_by_a_kind():
    assert set(KIND_UNITS) == set(LineKind)
    assert {u for units in KIND_UNITS.values() for u in units} == set(LineUnit)


@pytest.mark.parametrize(
    ("kind", "unit"),
    [
        (LineKind.CESSION, LineUnit.KM),
        (LineKind.ACCOMMODATION, LineUnit.FLAT),
        (LineKind.MEAL, LineUnit.NIGHT),
        (LineKind.COMMUNICATION, LineUnit.DAY),
    ],
)
def test_a_unit_that_does_not_fit_the_kind_is_refused(kind, unit):
    draft = invoicing.create_invoice(_gig(), Invoice.Kind.FULL)

    with pytest.raises(invoicing.InvoicingError):
        invoicing.add_line(draft, "X", 10, kind=kind, unit=unit)


@pytest.mark.parametrize(
    ("kind", "unit"),
    [(LineKind.TRANSPORT, LineUnit.KM), (LineKind.TECHNICAL, LineUnit.HOUR)],
)
def test_a_unit_that_fits_is_kept(kind, unit):
    draft = invoicing.create_invoice(_gig(), Invoice.Kind.FULL)

    line = invoicing.add_line(draft, "X", 10, kind=kind, unit=unit)

    assert (line.kind, line.unit) == (kind, unit)


def test_without_a_unit_the_first_one_of_the_kind_is_used():
    draft = invoicing.create_invoice(_gig(), Invoice.Kind.FULL)

    line = invoicing.add_line(draft, "Nuits", 80, quantity=2, kind=LineKind.ACCOMMODATION)

    assert line.unit == LineUnit.NIGHT


def test_changing_the_kind_of_a_line_resets_an_unit_that_no_longer_fits():
    draft = invoicing.create_invoice(_gig(), Invoice.Kind.FULL)
    line = invoicing.add_line(draft, "Route", 1, kind=LineKind.TRANSPORT, unit=LineUnit.KM)

    invoicing.update_line(line, "Nuit", 80, kind=LineKind.ACCOMMODATION)

    line.refresh_from_db()
    assert line.unit == LineUnit.NIGHT


# --- the cession line of a quote ----------------------------------------------------------------


def test_a_new_quote_starts_with_its_cession_line():
    quote = invoicing.create_quote(_gig())

    assert _kinds(quote) == [LineKind.CESSION]


def test_a_quote_has_one_cession_line_only():
    quote = invoicing.create_quote(_gig())

    with pytest.raises(invoicing.InvoicingError):
        invoicing.add_line(quote, "Encore", 10, kind=LineKind.CESSION)


def test_the_cession_line_of_a_quote_cannot_be_removed_or_turned_into_another_kind():
    quote = invoicing.create_quote(_gig())
    cession = quote.lines.get()

    with pytest.raises(invoicing.InvoicingError):
        invoicing.remove_line(cession)
    with pytest.raises(invoicing.InvoicingError):
        invoicing.update_line(cession, "X", 10, kind=LineKind.OTHER)

    assert quote.lines.count() == 1


def test_another_line_of_a_quote_cannot_become_a_cession():
    quote = invoicing.create_quote(_gig())
    extra = invoicing.add_line(quote, "Route", 10, kind=LineKind.TRANSPORT)

    with pytest.raises(invoicing.InvoicingError):
        invoicing.update_line(extra, "X", 10, kind=LineKind.CESSION)


def test_the_cession_line_can_still_change_its_price_and_unit():
    quote = invoicing.create_quote(_gig())
    cession = quote.lines.get()

    invoicing.update_line(cession, "Cession", 900, quantity=2, unit=LineUnit.PERFORMANCE)

    cession.refresh_from_db()
    assert cession.unit == LineUnit.PERFORMANCE and cession.unit_price_excl_tax == Decimal("900")


def test_a_quote_that_does_not_start_with_a_cession_is_not_issued():
    quote = invoicing.create_quote(_gig())
    DocumentLine.objects.filter(quote=quote).update(kind=LineKind.OTHER)

    with pytest.raises(invoicing.InvoicingError):
        invoicing.issue_quote(Quote.objects.get(pk=quote.pk))

    assert Quote.objects.get(pk=quote.pk).status == Quote.Status.DRAFT


# --- the balance invoice ------------------------------------------------------------------------


def test_a_deposit_bills_a_share_of_the_cession():
    gig = _gig()
    gig.deposit_percent = 30
    gig.save()

    deposit = invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT)

    line = deposit.lines.get()
    assert line.kind == LineKind.CESSION and line.unit_price_excl_tax == Decimal("300.00")


def test_a_balance_shows_the_whole_cession_then_takes_off_the_deposit():
    gig = _gig()
    gig.deposit_percent = 30
    gig.save()
    deposit = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT))

    balance = invoicing.create_invoice(gig, Invoice.Kind.BALANCE)

    cession, deducted = balance.lines.all()
    assert cession.kind == LineKind.CESSION and cession.unit_price_excl_tax == Decimal("1000.00")
    assert deducted.kind == LineKind.DEPOSIT_DEDUCTED
    assert deducted.unit_price_excl_tax == Decimal("-300.00")
    assert deposit.number in deducted.label
    assert balance.total_excl_tax == Decimal("700.00")


def test_a_balance_without_any_deposit_is_the_cession_alone():
    balance = invoicing.create_invoice(_gig(), Invoice.Kind.BALANCE)

    assert _kinds(balance) == [LineKind.CESSION]


def test_a_credited_deposit_is_not_taken_off_again():
    gig = _gig()
    deposit = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT))
    invoicing.issue_invoice(invoicing.create_credit_note(deposit))

    balance = invoicing.create_invoice(gig, Invoice.Kind.BALANCE)

    assert _kinds(balance) == [LineKind.CESSION]


def test_a_credit_note_keeps_the_kind_and_unit_of_the_lines_it_cancels():
    gig = _gig()
    invoice = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    invoicing.add_line(
        invoice, "Route", 50, quantity=100, kind=LineKind.TRANSPORT, unit=LineUnit.KM
    )
    invoice = invoicing.issue_invoice(invoice)

    note = invoicing.create_credit_note(invoice)

    assert [(line.kind, line.unit) for line in note.lines.all()] == [
        (LineKind.CESSION, LineUnit.FLAT),
        (LineKind.TRANSPORT, LineUnit.KM),
    ]


# --- the PDF ------------------------------------------------------------------------------------


def test_the_pdf_shows_the_unit_of_each_line():
    gig = _gig()
    invoice = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    invoicing.add_line(
        invoice, "Route", 0.5, quantity=120, kind=LineKind.TRANSPORT, unit=LineUnit.KM
    )
    invoicing.add_line(invoice, "Hôtel", 80, quantity=2, kind=LineKind.ACCOMMODATION)

    text = _text(invoice)

    assert "120.00 km" in text or "120,00 km" in text
    assert "nuit(s)" in text and "forfait" in text


# --- the form -----------------------------------------------------------------------------------


def _form(data, document=None, line=None):
    document = document or invoicing.create_invoice(_gig(), Invoice.Kind.FULL)
    base = {"label": "X", "quantity": "1", "unit_price_excl_tax": "10"}
    return DocumentLineForm({**base, **data}, document=document, line=line)


def test_the_form_refuses_an_unit_that_does_not_fit_the_kind():
    form = _form({"kind": "meal", "unit": "km"})

    assert not form.is_valid() and "unit" in form.errors


def test_the_form_fills_kind_and_unit_when_left_empty():
    form = _form({})

    assert form.is_valid()
    assert (form.cleaned_data["kind"], form.cleaned_data["unit"]) == (LineKind.OTHER, LineUnit.FLAT)


def test_the_deducted_deposit_cannot_be_chosen_by_hand():
    form = _form({"kind": "deposit_deducted"})

    assert not form.is_valid() and "kind" in form.errors


def test_a_quote_form_does_not_offer_the_cession():
    quote = invoicing.create_quote(_gig())

    form = _form({"kind": "cession"}, document=quote)

    assert not form.is_valid() and "kind" in form.errors


def test_the_unit_options_carry_the_kinds_that_allow_them():
    html = str(
        DocumentLineForm(document=invoicing.create_invoice(_gig(), Invoice.Kind.FULL))["unit"]
    )

    assert 'data-kinds="cession transport technical communication other discount' in html
    assert "x-effect" in html


# --- the screens --------------------------------------------------------------------------------


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def test_adding_a_transport_line_in_km_from_the_page(client):
    tenant = _login(client)
    gig = _gig(tenant)
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)

    client.post(
        reverse("documents:line-add", args=[gig.pk, "factures", draft.pk]),
        {
            "kind": "transport",
            "label": "Route",
            "quantity": "120",
            "unit": "km",
            "unit_price_excl_tax": "0.50",
        },
    )

    line = draft.lines.get(kind=LineKind.TRANSPORT)
    assert line.unit == LineUnit.KM and line.unit_price_excl_tax == Decimal("0.50")


def test_a_discount_is_typed_positive_and_stored_negative(client):
    tenant = _login(client)
    gig = _gig(tenant)
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    url = reverse("documents:line-add", args=[gig.pk, "factures", draft.pk])

    client.post(
        url,
        {"kind": "discount", "label": "Geste", "quantity": "1", "unit_price_excl_tax": "100"},
    )

    discount = draft.lines.get(kind=LineKind.DISCOUNT)
    draft.refresh_from_db()
    assert discount.unit_price_excl_tax == Decimal("-100.00")
    assert draft.total_excl_tax == Decimal("900.00")


def test_the_edit_form_of_a_discount_shows_the_amount_without_its_sign(client):
    tenant = _login(client)
    gig = _gig(tenant)
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    discount = invoicing.add_line(draft, "Geste", -100, kind=LineKind.DISCOUNT)

    page = client.get(
        reverse("documents:line-edit", args=[gig.pk, "factures", draft.pk, discount.pk])
    ).content.decode()

    assert 'value="100.00"' in page


def test_the_cession_of_a_quote_has_no_remove_error_hidden_in_the_page(client):
    tenant = _login(client)
    gig = _gig(tenant)
    quote = invoicing.create_quote(gig)
    cession = quote.lines.get()

    response = client.post(
        reverse("documents:line-remove", args=[gig.pk, "devis", quote.pk, cession.pk]), follow=True
    )

    assert quote.lines.count() == 1
    assert "ne peut pas être supprimée" in response.content.decode()


def test_the_page_names_the_kind_and_the_unit_of_a_line(client):
    tenant = _login(client)
    gig = _gig(tenant)
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)

    page = client.get(
        reverse("documents:document-detail", args=[gig.pk, "factures", draft.pk])
    ).content.decode()

    assert "Cession du spectacle" in page and "forfait" in page


# --- the migration ------------------------------------------------------------------------------


def test_the_migration_marks_the_first_line_of_each_document_as_the_cession():
    migration = importlib.import_module("apps.documents.migrations.0014_line_kind_and_unit")
    gig = _gig()
    quote = invoicing.create_quote(gig)
    invoicing.add_line(quote, "Route", 10, kind=LineKind.TRANSPORT)
    invoice = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    invoicing.add_line(invoice, "Hôtel", 10)
    DocumentLine.objects.update(kind=LineKind.OTHER)

    migration.label_existing_lines(django_apps, None)

    assert _kinds(quote) == [LineKind.CESSION, LineKind.OTHER]
    assert _kinds(invoice) == [LineKind.CESSION, LineKind.OTHER]
