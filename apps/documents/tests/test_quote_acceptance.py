"""Spec v2 (PR 3): "Devis signé reçu", the expired quote, the purchase order and the due date."""

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.tenants.factories import MembershipFactory

from .. import invoicing
from ..models import ImmutableDocument, Invoice, Quote
from .test_billing_pdf import _gig, _issued, _text

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()
PDF = b"%PDF-1.4 scan"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _quote(gig=None):
    return invoicing.issue_quote(invoicing.create_quote(gig or _gig()))


def _pdf(content=PDF, name="scan.pdf"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def _login(client, gig):
    client.force_login(MembershipFactory(tenant=gig.tenant).user)


def _url(name, quote):
    return reverse(f"documents:{name}", args=[quote.gig_id, quote.pk])


# --- accepting a quote ------------------------------------------------------------------------


def test_a_quote_is_accepted_once_with_its_day_and_scan():
    quote = invoicing.accept_quote(_quote(), TODAY, _pdf())

    quote.refresh_from_db()
    assert quote.accepted_on == TODAY
    assert quote.signed_file.name.startswith("quotes/") and quote.signed_file.name.endswith(".pdf")
    assert "scan" not in quote.signed_file.name


def test_the_scan_is_optional():
    quote = invoicing.accept_quote(_quote(), TODAY)

    assert quote.accepted_on == TODAY and not quote.signed_file


def test_accepting_changes_nothing_else_on_the_issued_quote():
    quote = _quote()
    frozen = (quote.number, quote.total_incl_tax, quote.issuer_snapshot, quote.valid_until)

    invoicing.accept_quote(quote, TODAY)
    quote.refresh_from_db()

    assert (quote.number, quote.total_incl_tax, quote.issuer_snapshot, quote.valid_until) == frozen
    quote.valid_until = TODAY
    with pytest.raises(ImmutableDocument):
        quote.save()


def test_a_draft_quote_cannot_be_accepted():
    draft = invoicing.create_quote(_gig())

    with pytest.raises(invoicing.InvoicingError):
        invoicing.accept_quote(draft, TODAY)


def test_a_quote_cannot_be_accepted_twice():
    quote = invoicing.accept_quote(_quote(), TODAY)

    with pytest.raises(invoicing.InvoicingError, match="déjà accepté"):
        invoicing.accept_quote(quote, TODAY)


def test_the_day_cannot_be_in_the_future_or_before_the_issue():
    quote = _quote()

    with pytest.raises(invoicing.InvoicingError, match="futur"):
        invoicing.accept_quote(quote, TODAY + datetime.timedelta(days=1))
    with pytest.raises(invoicing.InvoicingError, match="avant son émission"):
        invoicing.accept_quote(quote, TODAY - datetime.timedelta(days=1))
    quote.refresh_from_db()
    assert quote.accepted_on is None


def test_the_scan_can_be_added_afterwards_once_never_replaced():
    quote = invoicing.accept_quote(_quote(), TODAY)

    invoicing.attach_quote_scan(quote, _pdf())
    first = quote.signed_file.name

    with pytest.raises(invoicing.InvoicingError, match="déjà enregistré"):
        invoicing.attach_quote_scan(quote, _pdf())
    quote.refresh_from_db()
    assert quote.signed_file.name == first


def test_a_scan_cannot_be_added_before_the_quote_is_accepted():
    with pytest.raises(invoicing.InvoicingError, match="pas encore accepté"):
        invoicing.attach_quote_scan(_quote(), _pdf())


# --- expired ---------------------------------------------------------------------------------


def test_a_quote_is_expired_when_issued_not_accepted_and_past_its_date():
    quote = _quote()
    assert not quote.is_expired

    Quote.objects.filter(pk=quote.pk).update(valid_until=TODAY - datetime.timedelta(days=1))
    quote.refresh_from_db()
    assert quote.is_expired


def test_an_accepted_quote_never_expires():
    quote = invoicing.accept_quote(_quote(), TODAY)
    Quote.objects.filter(pk=quote.pk).update(valid_until=TODAY - datetime.timedelta(days=1))
    quote.refresh_from_db()

    assert not quote.is_expired


def test_a_draft_is_not_expired():
    draft = invoicing.create_quote(_gig())
    draft.valid_until = TODAY - datetime.timedelta(days=5)

    assert not draft.is_expired


# --- the screens ------------------------------------------------------------------------------


def test_the_accept_form_posts_the_day_and_the_scan(client):
    quote = _quote()
    _login(client, quote.gig)

    response = client.post(
        _url("quote-accept", quote), {"accepted_on": TODAY.isoformat(), "signed_pdf": _pdf()}
    )

    assert response.status_code == 302
    quote.refresh_from_db()
    assert quote.accepted_on == TODAY and quote.signed_file


def test_the_detail_page_offers_the_button_then_shows_the_acceptance(client):
    quote = _quote()
    _login(client, quote.gig)
    url = reverse("documents:document-detail", args=[quote.gig_id, "devis", quote.pk])

    assert "Devis signé reçu" in client.get(url).content.decode()
    invoicing.accept_quote(quote, TODAY, _pdf())
    page = client.get(url).content.decode()

    assert f"Devis accepté le {TODAY:%d/%m/%Y}" in page
    assert "Télécharger le devis signé" in page and "Devis signé reçu" not in page


def test_the_billing_list_shows_accepted_and_expired(client):
    gig = _gig()
    _login(client, gig)
    accepted = invoicing.accept_quote(_quote(gig), TODAY)
    expired = _quote(gig)
    Quote.objects.filter(pk=expired.pk).update(valid_until=TODAY - datetime.timedelta(days=1))

    page = client.get(reverse("documents:billing", args=[gig.pk])).content.decode()

    assert f"Accepté le {accepted.accepted_on:%d/%m/%Y}" in page
    assert "Expiré" in page


def test_a_fake_pdf_is_refused_and_nothing_is_saved(client):
    quote = _quote()
    _login(client, quote.gig)

    client.post(
        _url("quote-accept", quote),
        {"accepted_on": TODAY.isoformat(), "signed_pdf": _pdf(b"not a pdf")},
    )

    quote.refresh_from_db()
    assert quote.accepted_on is None and not quote.signed_file


def test_a_missing_or_future_day_is_refused(client):
    quote = _quote()
    _login(client, quote.gig)

    client.post(_url("quote-accept", quote), {})
    client.post(
        _url("quote-accept", quote),
        {"accepted_on": (TODAY + datetime.timedelta(days=2)).isoformat()},
    )

    quote.refresh_from_db()
    assert quote.accepted_on is None


def test_the_scan_download_and_the_late_upload(client):
    quote = invoicing.accept_quote(_quote(), TODAY)
    _login(client, quote.gig)
    url = _url("quote-scan", quote)

    assert client.get(url).status_code == 404
    assert client.post(url, {"signed_pdf": _pdf()}).status_code == 302
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("attachment")
    assert quote.number in response["Content-Disposition"]
    assert b"".join(response.streaming_content) == PDF


def test_the_stored_scan_has_no_public_url(client):
    quote = invoicing.accept_quote(_quote(), TODAY, _pdf())

    assert not quote.signed_file.name.startswith(("/", "http"))
    assert client.get("/media/" + quote.signed_file.name).status_code == 404


def test_the_actions_need_a_login(client):
    quote = _quote()

    for name in ("quote-accept", "quote-scan"):
        response = client.post(_url(name, quote), {})
        assert response.status_code == 302 and "login" in response["Location"]


def test_another_tenant_gets_404_on_the_scan_of_a_quote(client):
    quote = invoicing.accept_quote(_quote(), TODAY, _pdf())
    _login(client, _gig())

    assert client.get(_url("quote-scan", quote)).status_code == 404
    assert client.post(_url("quote-scan", quote), {"signed_pdf": _pdf()}).status_code == 404


def test_the_second_tenant_cannot_accept_the_quote_of_the_first(client):
    quote = _quote()
    _login(client, _gig())

    response = client.post(_url("quote-accept", quote), {"accepted_on": TODAY.isoformat()})

    assert response.status_code == 404
    quote.refresh_from_db()
    assert quote.accepted_on is None


def test_a_quote_is_not_reachable_through_another_gig_of_the_same_tenant(client):
    quote = _quote()
    _login(client, quote.gig)
    other_gig = _gig(quote.tenant)
    url = reverse("documents:quote-accept", args=[other_gig.pk, quote.pk])

    assert client.post(url, {"accepted_on": TODAY.isoformat()}).status_code == 404


# --- the invoice recalls the accepted quote --------------------------------------------------


def test_the_invoice_recalls_the_acceptance_date():
    gig = _gig()
    quote = invoicing.accept_quote(_quote(gig), TODAY)

    invoice = _issued(gig)

    assert f"Devis n° {quote.number} accepté le {TODAY:%d/%m/%Y}" in _text(invoice)


def test_the_invoice_prefers_the_accepted_quote_to_a_later_one():
    gig = _gig()
    accepted = invoicing.accept_quote(_quote(gig), TODAY)
    _quote(gig)

    assert f"Devis n° {accepted.number} accepté le" in _text(_issued(gig))


def test_without_acceptance_the_invoice_says_the_quote_was_issued():
    gig = _gig()
    quote = _quote(gig)

    assert f"Devis n° {quote.number} émis le {TODAY:%d/%m/%Y}" in _text(_issued(gig))


# --- purchase order and due date on a draft invoice -----------------------------------------


def _draft(gig=None):
    return invoicing.create_invoice(gig or _gig(), Invoice.Kind.FULL)


def test_the_purchase_order_is_printed_and_frozen():
    draft = _draft()
    invoicing.set_invoice_details(draft, "  BC-2026-77  ")

    invoice = invoicing.issue_invoice(draft)

    assert invoice.purchase_order_number == "BC-2026-77"
    assert "Bon de commande n° BC-2026-77" in _text(invoice)


def test_without_a_purchase_order_nothing_is_printed():
    assert "Bon de commande" not in _text(_issued())


def test_a_chosen_due_date_is_kept_up_to_sixty_days():
    due = TODAY + datetime.timedelta(days=60)
    draft = _draft()
    invoicing.set_invoice_details(draft, "", due)

    assert invoicing.issue_invoice(draft).due_date == due


def test_a_due_date_after_sixty_days_blocks_the_issue():
    draft = _draft()
    invoicing.set_invoice_details(draft, "", TODAY + datetime.timedelta(days=61))

    with pytest.raises(invoicing.InvoicingError, match="60 jours"):
        invoicing.issue_invoice(draft)
    draft.refresh_from_db()
    assert draft.is_draft and draft.number == ""


def test_a_due_date_before_the_issue_blocks_the_issue():
    draft = _draft()
    invoicing.set_invoice_details(draft, "", TODAY - datetime.timedelta(days=1))

    with pytest.raises(invoicing.InvoicingError, match="avant la date d'émission"):
        invoicing.issue_invoice(draft)


def test_without_a_due_date_the_structure_term_applies():
    invoice = _issued(_gig(payment_term_days=20))

    assert invoice.due_date == invoice.issue_date + datetime.timedelta(days=20)


def test_details_are_for_a_draft_invoice_only():
    invoice = _issued()
    note = invoicing.create_credit_note(invoice)

    with pytest.raises(invoicing.InvoicingError):
        invoicing.set_invoice_details(invoice, "X")
    with pytest.raises(invoicing.InvoicingError):
        invoicing.set_invoice_details(note, "X")


def test_the_details_form_saves_and_refuses_a_far_due_date(client):
    draft = _draft()
    _login(client, draft.gig)
    url = reverse("documents:invoice-details", args=[draft.gig_id, draft.pk])
    far = (TODAY + datetime.timedelta(days=61)).isoformat()

    client.post(url, {"purchase_order_number": "BC-1", "due_date": far})
    draft.refresh_from_db()
    assert draft.purchase_order_number == "" and draft.due_date is None

    client.post(url, {"purchase_order_number": "BC-1", "due_date": ""})
    draft.refresh_from_db()
    assert draft.purchase_order_number == "BC-1"


def test_the_details_form_is_only_on_a_draft_invoice(client):
    draft = _draft()
    _login(client, draft.gig)
    page_url = reverse("documents:document-detail", args=[draft.gig_id, "factures", draft.pk])

    assert "Enregistrer les détails" in client.get(page_url).content.decode()
    invoicing.issue_invoice(draft)
    assert "Enregistrer les détails" not in client.get(page_url).content.decode()


def test_another_tenant_gets_404_on_the_invoice_details(client):
    draft = _draft()
    _login(client, _gig())

    url = reverse("documents:invoice-details", args=[draft.gig_id, draft.pk])

    assert client.post(url, {"purchase_order_number": "X"}).status_code == 404
    draft.refresh_from_db()
    assert draft.purchase_order_number == ""
