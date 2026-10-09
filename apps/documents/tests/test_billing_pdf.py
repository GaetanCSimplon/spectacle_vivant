import html as html_lib
import re
from decimal import Decimal

import pytest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory
from apps.tenants.models import Tenant

from .. import invoicing
from ..models import ImmutableDocument, Invoice

pytestmark = pytest.mark.django_db

D = Decimal
YEAR = timezone.localdate().year


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _gig(tenant=None, **tenant_fields):
    defaults = {
        "name": "Compagnie du Soleil",
        "address": "1 rue des Arts, 69001 Lyon",
        "siret": "12345678900012",
        "vat_regime": Tenant.VatRegime.FRANCHISE,
        "iban": "FR1420041010050500013M02606",
    }
    defaults.update(tenant_fields)
    extra = {"tenant": tenant} if tenant else {f"tenant__{k}": v for k, v in defaults.items()}
    gig = GigFactory(
        price="1000.00",
        promoter__name="Mairie de Nîmes",
        promoter__billing_address="3 place de la Mairie, 30000 Nîmes",
        **extra,
    )
    gig.refresh_from_db()
    return gig


def _issued(gig=None, kind=Invoice.Kind.FULL):
    return invoicing.issue_invoice(invoicing.create_invoice(gig or _gig(), kind))


def _text(document):
    html = render_to_string("documents/billing_pdf.html", invoicing.build_pdf_context(document))
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL)
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", html)).split())


# --- content ---------------------------------------------------------------


def test_issuing_stores_a_real_pdf():
    invoice = _issued()

    saved = Invoice.objects.get(pk=invoice.pk)

    assert saved.pdf_file.name.startswith("invoice")
    assert saved.pdf_file.name.endswith(f"{saved.number}.pdf")
    assert saved.pdf_file.read().startswith(b"%PDF-")


def test_the_pdf_path_cannot_be_guessed():
    invoice = _issued()

    folder = invoice.pdf_file.name.split("/")[1]

    assert len(folder) == 32


def test_an_invoice_shows_the_parties_lines_and_payment_details():
    invoice = _issued()

    text = _text(invoice)

    assert f"FACTURE F-{YEAR}-0001" in text
    assert "Compagnie du Soleil" in text
    assert "SIRET : 12345678900012" in text
    assert "Mairie de Nîmes" in text
    assert "3 place de la Mairie" in text
    assert "Cession du spectacle" in text
    assert "1000,00 €" in text
    assert "IBAN FR1420041010050500013M02606" in text
    assert f"Échéance : {invoice.due_date:%d/%m/%Y}" in text
    assert f"Date de la prestation : {invoice.gig.date:%d/%m/%Y}" in text


def test_a_franchise_tenant_gets_the_293b_mention_and_no_vat_columns():
    text = _text(_issued(_gig(vat_regime="franchise")))

    assert "TVA non applicable, article 293 B du CGI." in text
    assert "Total TTC" not in text
    assert "N° de TVA" not in text


def test_a_non_taxable_tenant_gets_a_mention_without_the_article():
    text = _text(_issued(_gig(vat_regime="not_taxable")))

    assert "TVA non applicable." in text
    assert "293" not in text


def test_a_taxable_tenant_shows_vat_per_rate_and_its_number():
    gig = _gig(vat_regime="taxable", vat_rate="5.5", vat_number="FR12345678901")
    invoice = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    invoicing.add_line(invoice, "Transport", "100.00", vat_rate="20")
    invoice = invoicing.issue_invoice(invoice)

    text = _text(invoice)

    assert "N° de TVA : FR12345678901" in text
    assert "Total HT 1100,00 €" in text
    assert "TVA 5,50 % (sur 1000,00 €) 55,00 €" in text
    assert "TVA 20,00 % (sur 100,00 €) 20,00 €" in text
    assert "Total TTC 1175,00 €" in text
    assert "TVA non applicable" not in text


def test_payment_terms_are_on_invoices_but_not_on_quotes_or_credit_notes():
    gig = _gig()
    invoice = _issued(gig)
    note = invoicing.issue_invoice(invoicing.create_credit_note(invoice))
    quote = invoicing.issue_quote(invoicing.create_quote(gig))

    assert "Pénalités de retard" in _text(invoice)
    assert "Pénalités de retard" not in _text(note)
    assert "Pénalités de retard" not in _text(quote)


def test_a_credit_note_names_its_invoice_and_shows_negative_amounts():
    invoice = _issued()
    note = invoicing.issue_invoice(invoicing.create_credit_note(invoice))

    text = _text(note)

    assert f"AVOIR F-{YEAR}-0002" in text
    assert f"Avoir sur la facture n° {invoice.number} du {invoice.issue_date:%d/%m/%Y}" in text
    assert "-1000,00 €" in text


def test_a_quote_shows_its_validity_and_the_approval_box():
    quote = invoicing.issue_quote(invoicing.create_quote(_gig()))

    text = _text(quote)

    assert f"DEVIS D-{YEAR}-0001" in text
    assert f"Valable jusqu'au {quote.valid_until:%d/%m/%Y}" in text
    assert "Bon pour accord" in text
    assert "IBAN" not in text


def test_an_issued_pdf_carries_the_provisional_banner_until_reviewed():
    text = _text(_issued())

    assert "Modèle provisoire — non relu par un professionnel" in text


def test_the_provisional_banner_can_be_removed_in_one_place(monkeypatch):
    monkeypatch.setattr(invoicing, "PDF_PROVISIONAL", False)

    assert "non relu" not in _text(_issued())


def test_html_in_a_label_is_escaped():
    gig = _gig()
    invoice = invoicing.create_invoice(
        gig, Invoice.Kind.FULL, lines=[{"label": "<script>x</script>", "unit_price_excl_tax": "5"}]
    )
    html = render_to_string("documents/billing_pdf.html", invoicing.build_pdf_context(invoice))

    assert "<script>" not in html


# --- frozen data -----------------------------------------------------------


def test_the_pdf_is_built_from_the_frozen_data_not_the_live_data():
    gig = _gig()
    invoice = _issued(gig)
    gig.tenant.name = "Nom modifié"
    gig.tenant.save()
    gig.promoter.billing_address = "Ailleurs"
    gig.promoter.save()

    text = _text(Invoice.objects.get(pk=invoice.pk))

    assert "Nom modifié" not in text
    assert "Ailleurs" not in text
    assert "Compagnie du Soleil" in text


def test_a_draft_uses_the_live_data_and_has_no_number():
    gig = _gig()
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    gig.tenant.name = "Nom modifié"
    gig.tenant.save()
    draft.refresh_from_db()

    text = _text(draft)

    assert "Nom modifié" in text
    assert "BROUILLON" in text
    assert "Modèle provisoire" not in text
    assert "FACTURE F-" not in text


# --- storage and immutability ---------------------------------------------


def test_a_pdf_failure_cancels_the_issue_and_gives_the_number_back(monkeypatch):
    gig = _gig()
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)

    def boom(*args, **kwargs):
        raise RuntimeError

    monkeypatch.setattr(invoicing, "render_pdf", boom)
    with pytest.raises(RuntimeError):
        invoicing.issue_invoice(draft)
    monkeypatch.undo()

    draft.refresh_from_db()
    assert draft.is_draft
    assert draft.number == ""
    assert not draft.pdf_file
    assert invoicing.issue_invoice(draft).number == f"F-{YEAR}-0001"


def test_the_stored_pdf_can_never_be_replaced():
    invoice = _issued()
    invoice.pdf_file = "invoices/other/other.pdf"

    with pytest.raises(ImmutableDocument):
        invoice.save(update_fields=["pdf_file"])

    assert Invoice.objects.get(pk=invoice.pk).pdf_file.name != "invoices/other/other.pdf"


def test_a_document_issued_without_pdf_gets_one_once_from_its_frozen_data():
    invoice = _issued()
    Invoice.objects.filter(pk=invoice.pk).update(pdf_file="")
    invoice = Invoice.objects.get(pk=invoice.pk)

    invoicing.ensure_pdf(invoice)
    first_name = invoice.pdf_file.name
    invoicing.ensure_pdf(Invoice.objects.get(pk=invoice.pk))

    saved = Invoice.objects.get(pk=invoice.pk)
    assert first_name
    assert saved.pdf_file.name == first_name
    assert saved.pdf_file.read().startswith(b"%PDF-")


def test_a_draft_has_no_stored_pdf():
    draft = invoicing.create_invoice(_gig(), Invoice.Kind.FULL)

    with pytest.raises(invoicing.InvoicingError):
        invoicing.ensure_pdf(draft)


# --- views -----------------------------------------------------------------


def _login(client):
    membership = MembershipFactory(
        tenant__address="1 rue des Arts",
        tenant__siret="12345678900012",
        tenant__vat_regime=Tenant.VatRegime.FRANCHISE,
    )
    client.force_login(membership.user)
    return membership.tenant


def _client_gig(tenant):
    gig = GigFactory(tenant=tenant, price="1000.00", promoter__billing_address="3 place X")
    gig.refresh_from_db()
    return gig


def _url(gig, document):
    doc_type = "factures" if isinstance(document, Invoice) else "devis"
    return reverse("documents:document-pdf", args=[gig.pk, doc_type, document.pk])


def test_issued_pdf_download_is_an_attachment_named_after_the_number(client):
    tenant = _login(client)
    gig = _client_gig(tenant)
    invoice = _issued(gig)

    response = client.get(_url(gig, invoice))

    assert response["Content-Type"] == "application/pdf"
    assert f'filename="{invoice.number}.pdf"' in response["Content-Disposition"]
    assert "attachment" in response["Content-Disposition"]
    assert b"".join(response.streaming_content).startswith(b"%PDF-")


def test_quote_pdf_download(client):
    tenant = _login(client)
    gig = _client_gig(tenant)
    quote = invoicing.issue_quote(invoicing.create_quote(gig))

    response = client.get(_url(gig, quote))

    assert f'filename="{quote.number}.pdf"' in response["Content-Disposition"]


def test_draft_preview_is_a_pdf_and_stores_nothing(client):
    tenant = _login(client)
    gig = _client_gig(tenant)
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)

    response = client.get(_url(gig, draft))

    assert response["Content-Type"] == "application/pdf"
    assert "attachment" not in response.get("Content-Disposition", "")
    assert response.content.startswith(b"%PDF-")
    draft.refresh_from_db()
    assert not draft.pdf_file
    assert draft.number == ""


def test_the_detail_page_offers_the_right_pdf_button(client):
    tenant = _login(client)
    gig = _client_gig(tenant)
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    issued = _issued(gig)

    draft_page = client.get(
        reverse("documents:document-detail", args=[gig.pk, "factures", draft.pk])
    ).content.decode()
    issued_page = client.get(
        reverse("documents:document-detail", args=[gig.pk, "factures", issued.pk])
    ).content.decode()

    assert "Aperçu PDF" in draft_page
    assert "Télécharger le PDF" not in draft_page
    assert "Télécharger le PDF" in issued_page
    assert "Aperçu PDF" not in issued_page


def test_the_pdf_requires_login(client):
    tenant = _login(client)
    gig = _client_gig(tenant)
    invoice = _issued(gig)
    client.logout()

    response = client.get(_url(gig, invoice))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_another_tenant_cannot_download_or_preview_a_pdf(client):
    other_gig = _client_gig(
        MembershipFactory(
            tenant__address="x", tenant__siret="1", tenant__vat_regime="franchise"
        ).tenant
    )
    issued = _issued(other_gig)
    draft = invoicing.create_invoice(other_gig, Invoice.Kind.FULL)
    _login(client)

    assert client.get(_url(other_gig, issued)).status_code == 404
    assert client.get(_url(other_gig, draft)).status_code == 404


def test_a_pdf_is_not_reachable_through_another_gig_or_a_wrong_type(client):
    tenant = _login(client)
    gig, other_gig = _client_gig(tenant), _client_gig(tenant)
    invoice = _issued(gig)

    assert client.get(_url(other_gig, invoice)).status_code == 404
    wrong = reverse("documents:document-pdf", args=[gig.pk, "devis", invoice.pk])
    assert client.get(wrong).status_code == 404


def test_the_stored_file_has_no_public_url(client, settings):
    tenant = _login(client)
    gig = _client_gig(tenant)
    invoice = _issued(gig)
    settings.DEBUG = True

    response = client.get(f"/media/{invoice.pdf_file.name}")

    assert response.status_code == 404


def test_invoice_html_shows_the_code_ape_from_the_snapshot():
    from .test_invoicing import _gig, _issued

    invoice = _issued(_gig(code_ape="9001Z"))
    html = render_to_string("documents/billing_pdf.html", invoicing.build_pdf_context(invoice))
    assert "Code APE : 9001Z" in html
