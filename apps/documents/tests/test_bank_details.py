import html as html_lib
import re

import pytest
from django.template.loader import render_to_string

from apps.gigs.factories import GigFactory
from apps.tenants.models import Tenant

from .. import invoicing
from ..models import Invoice

pytestmark = pytest.mark.django_db

IBAN = "FR1420041010050500013M02606"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _gig(**tenant_fields):
    fields = {
        "address": "1 rue des Arts, 69001 Lyon",
        "siret": "12345678900012",
        "vat_regime": Tenant.VatRegime.FRANCHISE,
        "iban": IBAN,
        "bic": "AGRIFRPP",
    }
    fields.update(tenant_fields)
    gig = GigFactory(
        price="1000.00",
        promoter__billing_address="3 place de la Mairie, 30000 Nîmes",
        **{f"tenant__{key}": value for key, value in fields.items()},
    )
    gig.refresh_from_db()
    return gig


def _text(html):
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL)
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", html)).split())


def _pdf_text(document):
    return _text(
        render_to_string("documents/billing_pdf.html", invoicing.build_pdf_context(document))
    )


def test_the_bic_is_copied_into_the_issuer_snapshot():
    gig = _gig()

    assert invoicing.build_issuer_snapshot(gig.tenant)["bic"] == "AGRIFRPP"


def test_an_invoice_shows_the_iban_and_the_bic():
    invoice = invoicing.issue_invoice(invoicing.create_invoice(_gig(), Invoice.Kind.FULL))

    assert f"Règlement par virement : IBAN {IBAN} — BIC AGRIFRPP" in _pdf_text(invoice)


def test_a_quote_shows_the_iban_and_the_bic():
    quote = invoicing.issue_quote(invoicing.create_quote(_gig()))

    assert f"Coordonnées bancaires pour le règlement : IBAN {IBAN} — BIC AGRIFRPP" in _pdf_text(
        quote
    )


def test_a_draft_shows_the_current_bank_details():
    draft = invoicing.create_invoice(_gig(), Invoice.Kind.FULL)

    assert f"IBAN {IBAN} — BIC AGRIFRPP" in _pdf_text(draft)


def test_a_credit_note_shows_no_bank_details():
    gig = _gig()
    invoice = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.FULL))
    note = invoicing.issue_invoice(invoicing.create_credit_note(invoice))

    text = _pdf_text(note)

    assert "IBAN" not in text and "BIC" not in text


def test_only_the_iban_is_shown_when_there_is_no_bic():
    quote = invoicing.issue_quote(invoicing.create_quote(_gig(bic="")))

    text = _pdf_text(quote)

    assert f"IBAN {IBAN}" in text
    assert "BIC" not in text


def test_nothing_is_shown_without_an_iban():
    invoice = invoicing.issue_invoice(invoicing.create_invoice(_gig(iban="", bic=""), "full"))

    assert "IBAN" not in _pdf_text(invoice)


def test_an_issued_document_keeps_the_bank_details_it_was_issued_with():
    gig = _gig()
    quote = invoicing.issue_quote(invoicing.create_quote(gig))
    gig.tenant.iban, gig.tenant.bic = "", "ZZZZFRPP"
    gig.tenant.save()
    quote.refresh_from_db()

    text = _pdf_text(quote)

    assert f"IBAN {IBAN} — BIC AGRIFRPP" in text
    assert "ZZZZFRPP" not in text


def test_a_document_issued_before_the_bic_existed_still_renders():
    quote = invoicing.issue_quote(invoicing.create_quote(_gig()))
    snapshot = dict(quote.issuer_snapshot)
    del snapshot["bic"]
    type(quote).objects.filter(pk=quote.pk).update(issuer_snapshot=snapshot)
    quote.refresh_from_db()

    text = _pdf_text(quote)

    assert f"IBAN {IBAN}" in text and "BIC" not in text
