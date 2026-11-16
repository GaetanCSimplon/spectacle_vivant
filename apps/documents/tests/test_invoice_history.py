"""Recette n°1, CTR-10: what an invoice recalls of the order, frozen when it is issued."""

import datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.finance import services as finance
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory, TenantFactory

from .. import invoicing
from ..models import Invoice
from ..services import generate_contract_pdf, mark_contract_signed
from .test_billing_pdf import _gig, _issued, _text

pytestmark = pytest.mark.django_db

D = Decimal
TODAY = timezone.localdate()


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _other_tenant():
    return TenantFactory(
        name="Autre",
        vat_regime="franchise",
        address="2 rue Neuve, 75001 Paris",
        siret="73282932000074",
    )


def _quote(gig):
    return invoicing.issue_quote(invoicing.create_quote(gig))


def _invoice(gig, kind, amount=None):
    invoice = invoicing.create_invoice(gig, kind)
    return invoicing.issue_invoice(invoice)


def _screen(client, invoice):
    membership = MembershipFactory(tenant=invoice.tenant)
    client.force_login(membership.user)
    url = reverse("documents:document-detail", args=[invoice.gig.pk, "factures", invoice.pk])
    return client.get(url).content.decode()


# --- the content ------------------------------------------------------------------------------


def test_a_deposit_invoice_recalls_the_quote_the_contract_and_the_balance():
    gig = _gig(vat_regime="franchise")  # 1000 €, deposit 30 % by default
    quote = _quote(gig)

    deposit = _invoice(gig, Invoice.Kind.DEPOSIT)

    history = deposit.history_snapshot
    assert history["quote"] == {
        "number": quote.number,
        "issue_date": TODAY.isoformat(),
        "accepted_on": None,
    }
    assert history["contract"]["total_incl_tax"] == "1000.00"
    assert history["contract"]["signed_on"] is None
    assert history["deposit"]["this_invoice"] is True
    assert D(history["deposit"]["amount_incl_tax"]) == deposit.total_incl_tax
    assert D(history["balance_incl_tax"]) == D("1000.00") - deposit.total_incl_tax


def test_a_balance_invoice_recalls_the_deposit_already_invoiced_and_paid():
    gig = _gig(vat_regime="franchise")
    deposit = _invoice(gig, Invoice.Kind.DEPOSIT)
    finance.record_payment(
        deposit, deposit.total_incl_tax, TODAY - datetime.timedelta(days=2), "transfer"
    )

    balance = _invoice(gig, Invoice.Kind.BALANCE)

    recalled = balance.history_snapshot["deposit"]
    assert recalled["number"] == deposit.number
    assert recalled["paid_on"] == (TODAY - datetime.timedelta(days=2)).isoformat()
    assert D(balance.history_snapshot["balance_incl_tax"]) == D("1000.00") - deposit.total_incl_tax


def test_a_deposit_not_yet_paid_says_so_and_a_partial_payment_is_not_paid():
    gig = _gig(vat_regime="franchise")
    deposit = _invoice(gig, Invoice.Kind.DEPOSIT)
    finance.record_payment(deposit, D("1.00"), TODAY, "transfer")

    balance = _invoice(gig, Invoice.Kind.BALANCE)

    assert balance.history_snapshot["deposit"]["paid_on"] is None


def test_a_balance_without_any_deposit_invoice_shows_the_planned_deposit():
    balance = _invoice(_gig(vat_regime="franchise"), Invoice.Kind.BALANCE)

    assert balance.history_snapshot["deposit"]["planned"] is True


def test_a_full_invoice_recalls_the_quote_and_the_contract_but_no_deposit():
    gig = _gig(vat_regime="franchise")

    full = _invoice(gig, Invoice.Kind.FULL)

    assert "deposit" not in full.history_snapshot
    assert "balance_incl_tax" not in full.history_snapshot
    assert full.history_snapshot["quote"] is None


def test_a_signed_contract_gives_its_signature_day():
    gig = _gig(vat_regime="franchise")
    gig.status = Gig.Status.CONFIRMED
    gig.save()
    generate_contract_pdf(gig)
    mark_contract_signed(gig)

    full = _invoice(gig, Invoice.Kind.FULL)

    assert full.history_snapshot["contract"]["signed_on"] == TODAY.isoformat()


def test_with_vat_the_contract_total_is_given_with_and_without_tax():
    gig = _gig(vat_regime="taxable", vat_rate="5.5", vat_number="FR12345678901")

    deposit = _invoice(gig, Invoice.Kind.DEPOSIT)

    contract = deposit.history_snapshot["contract"]
    assert contract["total_excl_tax"] == "1000.00" and contract["total_incl_tax"] == "1055.00"


def test_the_latest_issued_quote_is_the_one_recalled_and_a_draft_is_ignored():
    gig = _gig(vat_regime="franchise")
    _quote(gig)
    latest = _quote(gig)
    invoicing.create_quote(gig)  # a draft

    full = _invoice(gig, Invoice.Kind.FULL)

    assert full.history_snapshot["quote"]["number"] == latest.number


def test_a_credit_note_has_no_recall():
    invoice = _issued(_gig(vat_regime="franchise"))

    note = invoicing.issue_invoice(invoicing.create_credit_note(invoice))

    assert note.history_snapshot == {}


# --- frozen -----------------------------------------------------------------------------------


def test_the_recall_does_not_change_when_the_price_or_the_quotes_change_later():
    gig = _gig(vat_regime="franchise")
    quote = _quote(gig)
    deposit = _invoice(gig, Invoice.Kind.DEPOSIT)
    before = dict(deposit.history_snapshot)

    gig.price = D("5000.00")
    gig.save()
    _quote(gig)

    deposit.refresh_from_db()
    assert deposit.history_snapshot == before
    assert deposit.history_snapshot["quote"]["number"] == quote.number


def test_an_older_invoice_without_a_recall_shows_no_block(client):
    gig = _gig(vat_regime="franchise")
    invoice = _issued(gig)
    Invoice.objects.filter(pk=invoice.pk).update(history_snapshot={})
    invoice.refresh_from_db()

    assert "Rappel de la commande" not in _screen(client, invoice)
    assert "Rappel de la commande" not in _text(invoice)


# --- screen and PDF ----------------------------------------------------------------------------


def test_the_pdf_and_the_screen_show_the_recall(client):
    gig = _gig(vat_regime="franchise")
    quote = _quote(gig)
    deposit = _invoice(gig, Invoice.Kind.DEPOSIT)
    finance.record_payment(deposit, deposit.total_incl_tax, TODAY, "transfer")
    balance = _invoice(gig, Invoice.Kind.BALANCE)

    for content in (_text(balance), _screen(client, balance)):
        assert "Rappel de la commande" in content
        assert f"Devis n° {quote.number} émis le {TODAY:%d/%m/%Y}" in content
        assert "prix de cession convenu" in content
        assert (
            f"facturé le {TODAY:%d/%m/%Y} ({deposit.number}), réglé le {TODAY:%d/%m/%Y}" in content
        )
        assert "Solde restant dû" in content


def test_with_vat_the_amounts_are_labelled_ht_and_ttc():
    gig = _gig(vat_regime="taxable", vat_rate="20", vat_number="FR12345678901")

    text = _text(_invoice(gig, Invoice.Kind.DEPOSIT))

    assert "1000,00 € HT" in text and "TTC" in text


def test_a_quote_and_a_credit_note_have_no_recall_block():
    gig = _gig(vat_regime="franchise")
    assert "Rappel de la commande" not in _text(_quote(gig))
    note = invoicing.issue_invoice(invoicing.create_credit_note(_issued(gig)))
    assert "Rappel de la commande" not in _text(note)


# --- isolation ---------------------------------------------------------------------------------


def test_the_recall_never_uses_another_structures_quotes_or_contract():
    mine = _gig(vat_regime="franchise")
    other = _gig(tenant=_other_tenant())
    _quote(other)

    full = _invoice(mine, Invoice.Kind.FULL)

    assert full.history_snapshot["quote"] is None


def test_another_structures_invoice_screen_is_a_404(client):
    mine = _gig(vat_regime="franchise")
    foreign = _invoice(_gig(tenant=_other_tenant()), "full")
    client.force_login(MembershipFactory(tenant=mine.tenant).user)

    url = reverse("documents:document-detail", args=[foreign.gig.pk, "factures", foreign.pk])

    assert client.get(url).status_code == 404
