"""Radar rules from the quote and invoice specification (RAD-40 to RAD-44)."""

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.documents import invoicing
from apps.documents.models import Invoice, Quote
from apps.documents.tests.test_billing_pdf import _gig
from apps.radar import rules

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _codes(found):
    return [f.code for f in found]


def _promoter(gig, **fields):
    for name, value in fields.items():
        setattr(gig.promoter, name, value)
    gig.promoter.save()


# --- RAD-40: SIREN of a professional client ------------------------------------------------------


def test_rad_40_asks_for_the_siret_of_a_professional_client():
    gig = _gig()

    finding = rules.rad_40_no_siren(gig, datetime.date(2027, 3, 1))

    assert finding.code == "RAD-40" and finding.severity == rules.FIX
    assert finding.fix_url.endswith(f"/{gig.promoter.pk}/modifier/") or str(gig.promoter.pk) in (
        finding.fix_url
    )


def test_rad_40_becomes_important_from_the_first_of_september_2027():
    gig = _gig()

    before = rules.rad_40_no_siren(gig, datetime.date(2027, 8, 31))
    after = rules.rad_40_no_siren(gig, datetime.date(2027, 9, 1))

    assert before.severity == rules.FIX and after.severity == rules.IMPORTANT


def test_rad_40_is_quiet_with_a_siret_or_for_a_private_client():
    with_siret = _gig()
    _promoter(with_siret, siret="12345678900012")
    private = _gig()
    _promoter(private, is_private=True)

    assert rules.rad_40_no_siren(with_siret, datetime.date(2027, 3, 1)) is None
    assert rules.rad_40_no_siren(private, datetime.date(2027, 3, 1)) is None


# --- RAD-41: licence --------------------------------------------------------------------------


def test_rad_41_flags_no_licence_and_no_exemption():
    gig = _gig()

    assert rules.rad_41_no_licence(gig.tenant).severity == rules.KNOW


@pytest.mark.parametrize("fields", [{"licence_number": "L-1"}, {"licence_exempt": True}])
def test_rad_41_is_quiet_with_a_licence_or_an_exemption(fields):
    gig = _gig(**fields)

    assert rules.rad_41_no_licence(gig.tenant) is None


# --- RAD-42: mediator for a private client ----------------------------------------------------


def test_rad_42_flags_a_private_client_without_mediator():
    gig = _gig()
    _promoter(gig, is_private=True)

    assert rules.rad_42_no_mediator(gig).code == "RAD-42"


def test_rad_42_is_quiet_with_a_mediator_or_a_professional_client():
    private = _gig(mediator="Médiation Conso")
    _promoter(private, is_private=True)

    assert rules.rad_42_no_mediator(private) is None
    assert rules.rad_42_no_mediator(_gig()) is None


# --- RAD-43: total invoiced above the contract price -------------------------------------------


def _draft(gig, price="1000.00"):
    invoice = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    Invoice.objects.filter(pk=invoice.pk).update(total_excl_tax=Decimal(price))
    invoice.refresh_from_db()
    return invoice


def test_rad_43_is_quiet_when_the_total_matches_the_price():
    gig = _gig()

    assert rules.rad_43_over_invoiced(gig, _draft(gig)) is None


def test_rad_43_flags_a_draft_that_pushes_the_total_above_the_price():
    gig = _gig()
    invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.FULL))

    finding = rules.rad_43_over_invoiced(gig, _draft(gig, "100.00"))

    assert finding.code == "RAD-43" and "1100.00" in finding.message


def test_rad_43_ignores_cancelled_invoices_and_credit_notes():
    gig = _gig()
    first = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.FULL))
    invoicing.issue_invoice(invoicing.create_credit_note(first))

    assert rules.rad_43_over_invoiced(gig, _draft(gig)) is None


def test_rad_43_is_quiet_when_the_date_has_no_price():
    gig = _gig()
    gig.price = Decimal("0")

    assert rules.rad_43_over_invoiced(gig, _draft(gig)) is None


# --- RAD-44: expired quote --------------------------------------------------------------------


def _issued_quote(gig, expired=True):
    quote = invoicing.issue_quote(invoicing.create_quote(gig))
    if expired:
        past = timezone.localdate() - datetime.timedelta(days=1)
        Quote.objects.filter(pk=quote.pk).update(valid_until=past)
    return quote


def test_rad_44_flags_an_expired_quote_never_accepted():
    gig = _gig()
    quote = _issued_quote(gig)

    finding = rules.rad_44_expired_quote(gig)

    assert finding.code == "RAD-44" and quote.number in finding.message


def test_rad_44_is_quiet_for_a_valid_an_accepted_or_an_absent_quote():
    assert rules.rad_44_expired_quote(_gig()) is None
    valid = _gig()
    _issued_quote(valid, expired=False)
    accepted = _gig()
    quote = _issued_quote(accepted, expired=False)
    invoicing.accept_quote(quote, timezone.localdate())
    Quote.objects.filter(pk=quote.pk).update(
        valid_until=timezone.localdate() - datetime.timedelta(days=1)
    )

    assert rules.rad_44_expired_quote(valid) is None
    assert rules.rad_44_expired_quote(accepted) is None


def test_a_newer_valid_quote_replaces_the_expired_one():
    gig = _gig()
    _issued_quote(gig)
    _issued_quote(gig, expired=False)

    assert rules.rad_44_expired_quote(gig) is None


# --- before issuing -----------------------------------------------------------------------------


def test_issuing_an_invoice_lists_the_new_alerts_and_a_quote_only_its_own():
    gig = _gig()
    _issued_quote(gig)
    draft = _draft(gig, "1200.00")

    invoice = _codes(rules.for_action("invoice_issue", gig, document=draft))
    quote = _codes(rules.for_action("quote_issue", gig))

    assert {"RAD-40", "RAD-41", "RAD-43", "RAD-44"} <= set(invoice)
    assert "RAD-43" not in quote and "RAD-44" not in quote and "RAD-41" in quote


def test_the_issue_page_never_blocks(client):
    from django.urls import reverse

    from apps.tenants.factories import MembershipFactory

    membership = MembershipFactory(
        tenant__siret="12345678900012",
        tenant__address="1 rue des Arts, 69001 Lyon",
        tenant__iban="FR1420041010050500013M02606",
    )
    client.force_login(membership.user)
    gig = _gig(membership.tenant)
    _issued_quote(gig)
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    url = reverse("documents:document-issue", args=[gig.pk, "factures", draft.pk])

    page = client.get(url).content.decode()
    client.post(url)

    assert "le devis" in page and "est expiré" in page
    draft.refresh_from_db()
    assert draft.status == Invoice.Status.ISSUED
