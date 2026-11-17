"""Recette n°1, CTR-02: the sentence that says why a document has no VAT, in one place."""

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.tenants.factories import MembershipFactory, TenantFactory
from apps.tenants.models import Tenant

from .. import invoicing
from ..models import Invoice
from .test_billing_pdf import _gig, _issued, _text

pytestmark = pytest.mark.django_db

ARTICLE = "TVA non applicable, article 293 B du CGI."
ASSOCIATION = "TVA non applicable, article 261-7-1° b du CGI."


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _login(client, gig):
    membership = MembershipFactory(tenant=gig.tenant)
    client.force_login(membership.user)


def _detail(gig, document):
    doc_type = "factures" if isinstance(document, Invoice) else "devis"
    return reverse("documents:document-detail", args=[gig.pk, doc_type, document.pk])


# --- the texts --------------------------------------------------------------------------------


def test_each_regime_has_its_sentences():
    assert invoicing.vat_mentions("franchise") == [ARTICLE]
    assert invoicing.vat_mentions("not_taxable") == [ASSOCIATION]
    assert invoicing.vat_mentions("taxable") == []


def test_the_list_returned_can_be_changed_without_changing_the_next_call():
    invoicing.vat_mentions("franchise").append("x")

    assert invoicing.vat_mentions("franchise") == [ARTICLE]


# --- the screen of a quote and of an invoice ---------------------------------------------------


def test_the_screen_of_a_franchise_quote_quotes_the_article(client):
    gig = _gig(vat_regime="franchise")
    _login(client, gig)
    quote = invoicing.create_quote(gig)

    content = client.get(_detail(gig, quote)).content.decode()

    assert ARTICLE in content
    assert ASSOCIATION not in content


def test_the_screen_of_a_non_taxable_quote_adds_the_association_sentence(client):
    gig = _gig(vat_regime="not_taxable")
    _login(client, gig)
    quote = invoicing.create_quote(gig)

    content = client.get(_detail(gig, quote)).content.decode()

    assert ASSOCIATION in content
    assert "article 293 B" not in content


def test_the_screen_of_a_taxable_quote_has_no_exemption_sentence(client):
    gig = _gig(vat_regime="taxable", vat_rate="5.5", vat_number="FR12345678901")
    _login(client, gig)
    quote = invoicing.create_quote(gig)

    content = client.get(_detail(gig, quote)).content.decode()

    assert "non applicable" not in content and ASSOCIATION not in content
    assert "Total TTC" in content


def test_an_issued_invoice_keeps_the_regime_it_was_issued_with_on_screen(client):
    gig = _gig(vat_regime="franchise")
    _login(client, gig)
    invoice = _issued(gig)
    Tenant.objects.filter(pk=gig.tenant.pk).update(vat_regime="taxable")

    content = client.get(_detail(gig, invoice)).content.decode()

    assert ARTICLE in content
    assert "Total TTC" not in content


# --- the PDF ----------------------------------------------------------------------------------


def test_the_pdf_of_a_non_taxable_invoice_carries_the_association_sentence():
    text = _text(_issued(_gig(vat_regime="not_taxable")))

    assert ASSOCIATION in text


def test_the_pdf_of_a_non_taxable_quote_carries_it_too():
    gig = _gig(vat_regime="not_taxable")
    quote = invoicing.issue_quote(invoicing.create_quote(gig))

    text = _text(quote)

    assert ASSOCIATION in text and "Pénalités de retard" not in text


def test_a_credit_note_keeps_the_vat_sentence_without_the_late_payment_mention():
    invoice = _issued(_gig(vat_regime="franchise"))
    note = invoicing.issue_invoice(invoicing.create_credit_note(invoice))

    text = _text(note)

    assert ARTICLE in text and "Pénalités de retard" not in text


def test_a_franchise_pdf_has_no_association_sentence():
    assert ASSOCIATION not in _text(_issued(_gig(vat_regime="franchise")))


# --- the contract ---


def test_the_contract_carries_the_association_sentence():
    from apps.documents.services import build_contract_context

    gig = _gig(vat_regime="not_taxable")

    html = render_to_string("documents/contracts/contract.html", build_contract_context(gig))

    assert ASSOCIATION in html


# --- explanation of the regimes -----------------------------------------------------------------


def test_the_onboarding_and_the_structure_card_explain_the_three_regimes(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    card = client.get(reverse("tenants:settings")).content.decode()

    for text in (
        "Franchise en base : vous ne facturez pas de TVA",
        "Non assujetti : par exemple une association",
    ):
        assert text in card


def test_the_onboarding_explains_them_too(client):
    from apps.accounts.factories import UserFactory

    client.force_login(UserFactory())

    content = client.get(reverse("tenants-onboarding")).content.decode()

    assert "Assujetti : vous facturez la TVA" in content


# --- isolation ----------------------------------------------------------------------------------


def test_another_structures_quote_is_a_404(client):
    mine = _gig(vat_regime="franchise")
    _login(client, mine)
    foreign = _gig(tenant=TenantFactory(vat_regime="not_taxable", name="Autre"))
    quote = invoicing.create_quote(foreign)

    response = client.get(_detail(foreign, quote))

    assert response.status_code == 404
