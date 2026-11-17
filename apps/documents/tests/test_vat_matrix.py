"""The VAT sentences follow the VAT regime of the structure, on the contract and on
the invoice, the quote and the credit note. The wording is provisional (accountant to check)."""

import html as html_lib
import re

import pytest
from django.template.loader import render_to_string

from apps.documents import invoicing
from apps.documents.models import Invoice
from apps.documents.services import build_contract_context
from apps.finance.tests.helpers import make_gig

pytestmark = pytest.mark.django_db

MODELS = ["documents/contracts/contract.html"]
ARTICLE = "293 B"


def _text(html):
    html = html.split("</style>")[-1]
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", html)).split())


def _contract_text(template, **tenant):
    gig = make_gig(**tenant)
    return _text(render_to_string(template, build_contract_context(gig, None)))


@pytest.mark.parametrize("template", MODELS)
def test_a_franchise_contract_quotes_article_293_b(template):
    assert ARTICLE in _contract_text(template, vat_regime="franchise")


@pytest.mark.parametrize("template", MODELS)
def test_a_non_taxable_contract_says_vat_does_not_apply_without_the_article(template):
    text = _contract_text(template, vat_regime="not_taxable")

    assert "TVA non applicable" in text or "non applicable" in text
    assert ARTICLE not in text


@pytest.mark.parametrize("template", MODELS)
def test_a_taxable_contract_never_says_vat_does_not_apply(template):
    text = _contract_text(template, vat_regime="taxable", vat_rate="20.00", vat_number="FR123")

    assert ARTICLE not in text and "TVA non applicable" not in text
    assert "20" in text


@pytest.mark.parametrize(
    ("regime", "expected", "forbidden"),
    [
        ("franchise", "article 293 B", None),
        ("not_taxable", "TVA non applicable", "293 B"),
        ("taxable", None, "TVA non applicable"),
    ],
)
def test_the_invoice_mentions_follow_the_regime(regime, expected, forbidden):
    tenant = {"vat_regime": regime}
    if regime == "taxable":
        tenant.update(vat_rate="20.00", vat_number="FR12345678901")
    gig = make_gig(**tenant)
    document = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.FULL))
    document.refresh_from_db()

    mentions = " ".join(invoicing.build_pdf_context(document)["mentions"])

    assert expected is None or expected in mentions
    assert forbidden is None or forbidden not in mentions
