"""Spec v2 (PR 2): the new « Ma structure » and organizer fields, and what they print."""

import datetime

import pytest

from apps.addressbook.forms import PromoterForm
from apps.tenants.forms import TenantProfileForm
from apps.tenants.models import Tenant

from .. import invoicing
from .test_billing_pdf import _gig, _issued, _text

pytestmark = pytest.mark.django_db

PENALTIES = "trois fois le taux d'intérêt légal"
MEDIATOR = "En cas de litige, vous pouvez recourir gratuitement au médiateur de la consommation"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _private(gig, value=True):
    gig.promoter.is_private = value
    gig.promoter.save()


# --- customer: professional or private ---------------------------------------------------------


def test_a_professional_customer_gets_the_penalties():
    assert PENALTIES in _text(_issued(_gig()))


def test_a_private_customer_gets_no_penalties_but_the_mediator():
    gig = _gig(mediator="Médiation Conso — mediation-conso.example")
    _private(gig)

    text = _text(_issued(gig))

    assert PENALTIES not in text and "indemnité forfaitaire" not in text
    assert f"{MEDIATOR} : Médiation Conso — mediation-conso.example" in text


def test_a_private_customer_without_a_mediator_gets_neither_sentence():
    gig = _gig()
    _private(gig)

    text = _text(_issued(gig))

    assert PENALTIES not in text and MEDIATOR not in text


def test_a_professional_customer_does_not_get_the_mediator():
    assert MEDIATOR not in _text(_issued(_gig(mediator="Médiation Conso")))


def test_a_quote_for_a_private_customer_shows_the_mediator():
    gig = _gig(mediator="Médiation Conso")
    _private(gig)

    assert MEDIATOR in _text(invoicing.issue_quote(invoicing.create_quote(gig)))


def test_the_customer_kind_is_frozen_at_issue():
    gig = _gig()
    _private(gig)
    invoice = _issued(gig)
    _private(gig, False)

    assert invoice.customer_snapshot["is_private"] is True
    assert PENALTIES not in _text(invoice)


def test_a_snapshot_made_before_these_fields_reads_as_a_professional_customer():
    mentions = invoicing.legal_mentions({"vat_regime": "franchise"}, True, False, {"name": "X"})

    assert any(PENALTIES in mention for mention in mentions)
    assert not any(MEDIATOR in mention for mention in mentions)


# --- VAT on debits ----------------------------------------------------------------------------


def test_a_taxable_structure_with_the_option_prints_it_on_invoices_only():
    gig = _gig(vat_regime="taxable", vat_rate="5.5", vat_number="FR12345678901", vat_on_debits=True)
    sentence = "Option pour le paiement de la TVA d'après les débits."

    assert sentence in _text(_issued(gig))
    assert sentence not in _text(invoicing.issue_quote(invoicing.create_quote(gig)))


def test_the_option_is_ignored_for_a_structure_without_vat():
    assert "d'après les débits" not in _text(
        _issued(_gig(vat_regime="franchise", vat_on_debits=True))
    )


# --- licence, capital, RCS ---------------------------------------------------------------------


def test_the_licence_number_is_printed_and_wins_over_the_exemption():
    text = _text(_issued(_gig(licence_number="PLATESV-D-2026-1", licence_exempt=True)))

    assert "Licence d'entrepreneur de spectacles : PLATESV-D-2026-1" in text
    assert "non soumis" not in text


def test_an_exempt_structure_without_a_number_says_so():
    text = _text(_issued(_gig(licence_exempt=True)))

    assert "Licence d'entrepreneur de spectacles : non soumis (moins de 7 représentations" in text


def test_no_licence_and_no_exemption_prints_no_licence_line():
    assert "Licence d'entrepreneur" not in _text(_issued(_gig()))


def test_capital_and_rcs_are_printed_when_filled():
    text = _text(_issued(_gig(share_capital="5 000 €", rcs="RCS Lyon 123 456 789")))

    assert "Capital : 5 000 €" in text
    assert "RCS : RCS Lyon 123 456 789" in text


def test_capital_and_rcs_are_absent_when_empty():
    text = _text(_issued(_gig()))

    assert "Capital :" not in text and "RCS :" not in text


def test_the_structure_data_is_frozen_at_issue():
    gig = _gig(mediator="Médiation Conso", rcs="RCS Lyon 1")
    _private(gig)
    invoice = _issued(gig)
    Tenant.objects.filter(pk=gig.tenant.pk).update(mediator="", rcs="")

    text = _text(invoice)

    assert "Médiation Conso" in text and "RCS : RCS Lyon 1" in text


# --- delays -----------------------------------------------------------------------------------


def test_the_invoice_due_date_follows_the_payment_term_of_the_structure():
    invoice = _issued(_gig(payment_term_days=45))

    assert invoice.due_date == invoice.issue_date + datetime.timedelta(days=45)


def test_the_quote_validity_follows_the_setting_of_the_structure():
    quote = invoicing.issue_quote(invoicing.create_quote(_gig(quote_validity_days=10)))

    assert quote.valid_until == quote.issue_date + datetime.timedelta(days=10)


def test_the_default_delays_stay_at_thirty_days():
    invoice = _issued(_gig())

    assert invoice.due_date == invoice.issue_date + datetime.timedelta(days=30)


# --- the forms --------------------------------------------------------------------------------


def _profile_data(**changes):
    data = {"name": "Compagnie", "vat_regime": "franchise", "quote_validity_days": 30}
    data.update({"payment_term_days": 30, **changes})
    return data


@pytest.mark.parametrize(("days", "valid"), [(60, True), (61, False), (0, False), (1, True)])
def test_the_payment_term_is_between_1_and_60_days(days, valid):
    form = TenantProfileForm(_profile_data(payment_term_days=days))

    assert ("payment_term_days" not in form.errors) is valid


@pytest.mark.parametrize(("days", "valid"), [(365, True), (366, False), (0, False)])
def test_the_quote_validity_is_between_1_and_365_days(days, valid):
    form = TenantProfileForm(_profile_data(quote_validity_days=days))

    assert ("quote_validity_days" not in form.errors) is valid


def test_the_organizer_form_offers_the_private_checkbox():
    assert "is_private" in PromoterForm().fields


def test_an_empty_delay_keeps_the_current_value():
    form = TenantProfileForm(
        _profile_data(payment_term_days="", quote_validity_days=""), instance=Tenant(name="X")
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["payment_term_days"] == 30
    assert form.cleaned_data["quote_validity_days"] == 30
