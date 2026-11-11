"""Recette n°1, CTR-05 and CTR-06: payment terms as rules, and the page in three blocks."""

import datetime

import pytest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.documents.services import (
    build_contract_context,
    generate_contract_pdf,
    mark_contract_signed,
)
from apps.finance import bord
from apps.finance.tests.helpers import TENANT_FIELDS, make_gig
from apps.tenants.factories import MembershipFactory, TenantFactory

from .. import payment_terms as pt
from .. import services
from ..models import Gig

pytestmark = pytest.mark.django_db

D = datetime.date
TODAY = timezone.localdate()


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def tenant(client):
    membership = MembershipFactory(
        **{f"tenant__{key}": value for key, value in TENANT_FIELDS.items()}
    )
    client.force_login(membership.user)
    return membership.tenant


def _gig(tenant, **fields):
    return make_gig(tenant=tenant, gig_fields={"date": D(2027, 3, 15), **fields})


def _terms_url(gig):
    return reverse("gigs:terms", args=[gig.pk])


def _complete_url(gig):
    return reverse("documents:contract-complete", args=[gig.pk])


def _sign(gig):
    gig.status = Gig.Status.CONFIRMED
    gig.save()
    generate_contract_pdf(gig)
    mark_contract_signed(gig)
    gig.refresh_from_db()
    return gig


# --- the rules --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("term", "days", "signed", "expected"),
    [
        ("at_signature", None, D(2026, 11, 12), D(2026, 11, 12)),
        ("at_signature", None, None, None),
        ("signature_plus_10", None, D(2026, 11, 25), D(2026, 12, 5)),
        ("signature_plus_30", None, D(2026, 11, 12), D(2026, 12, 12)),
        ("end_of_signature_month", None, D(2028, 2, 3), D(2028, 2, 29)),  # leap year
        ("end_of_signature_month", None, None, None),
        ("days_before", 20, None, D(2027, 2, 23)),
        ("days_before", None, None, None),
        ("specific", None, D(2026, 11, 12), None),
    ],
)
def test_deposit_dates(term, days, signed, expected):
    assert pt.deposit_date(term, days, D(2027, 3, 15), signed) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("on_performance_day", D(2027, 3, 15)),
        ("after_on_invoice", D(2027, 3, 15)),
        ("performance_plus_15", D(2027, 3, 30)),
        ("performance_plus_30", D(2027, 4, 14)),
        ("end_of_next_month", D(2027, 4, 30)),
        ("specific", None),
    ],
)
def test_balance_dates(term, expected):
    assert pt.balance_date(term, D(2027, 3, 15)) == expected


def test_the_month_after_december_is_next_year():
    assert pt.balance_date("end_of_next_month", D(2026, 12, 20)) == D(2027, 1, 31)


def test_phrases_give_the_rule_and_the_date_when_there_is_one():
    assert (
        pt.deposit_phrase("signature_plus_10", None, None)
        == "10 jours après la signature du contrat"
    )
    assert pt.deposit_phrase("signature_plus_10", None, D(2026, 12, 5)) == (
        "10 jours après la signature du contrat, soit le 05/12/2026"
    )
    assert (
        pt.deposit_phrase("days_before", 1, D(2027, 3, 14))
        == "1 jour avant la prestation, soit le 14/03/2027"
    )
    assert pt.deposit_phrase("specific", None, D(2026, 11, 12)) == "le 12/11/2026"
    assert pt.deposit_phrase("specific", None, None) == ""
    assert pt.balance_phrase("performance_plus_15", D(2027, 3, 30)).startswith(
        "15 jours après la prestation"
    )
    assert pt.balance_phrase("specific", None) == ""


# --- the forms --------------------------------------------------------------------------------


def test_a_rule_gives_the_date_and_replaces_the_one_typed(client, tenant):
    gig = _gig(tenant)

    client.post(
        _terms_url(gig),
        {
            "payment_method": "transfer",
            "deposit_term": "days_before",
            "deposit_term_days": "30",
            "deposit_due_on": "2030-01-01",
            "balance_term": "performance_plus_15",
            "balance_due_on": "2030-01-01",
        },
    )

    gig.refresh_from_db()
    assert gig.deposit_due_on == D(2027, 2, 13)
    assert gig.balance_due_on == D(2027, 3, 30)
    assert gig.deposit_term_days == 30


def test_a_signature_rule_has_no_date_before_the_signature(client, tenant):
    gig = _gig(tenant)

    client.post(
        _terms_url(gig),
        {"payment_method": "", "deposit_term": "signature_plus_10", "balance_term": "specific"},
    )

    gig.refresh_from_db()
    assert gig.deposit_term == "signature_plus_10" and gig.deposit_due_on is None
    assert gig.deposit_due_display == "10 jours après la signature"
    assert gig.has_payment_terms


def test_date_precise_keeps_the_date_typed(client, tenant):
    gig = _gig(tenant)

    client.post(
        _terms_url(gig),
        {
            "payment_method": "",
            "deposit_term": "specific",
            "deposit_due_on": "2026-12-01",
            "balance_term": "specific",
            "balance_due_on": "2027-04-01",
        },
    )

    gig.refresh_from_db()
    assert (gig.deposit_due_on, gig.balance_due_on) == (D(2026, 12, 1), D(2027, 4, 1))


def test_days_before_needs_the_number_of_days(client, tenant):
    gig = _gig(tenant)

    response = client.post(
        _terms_url(gig),
        {"payment_method": "", "deposit_term": "days_before", "balance_term": "specific"},
    )

    assert response.status_code == 200
    assert "Indiquez le nombre de jours" in response.content.decode()
    gig.refresh_from_db()
    assert gig.deposit_term == "specific"


def test_days_are_forgotten_when_the_rule_does_not_use_them(client, tenant):
    gig = _gig(tenant, deposit_term="days_before", deposit_term_days=20)

    client.post(
        _terms_url(gig),
        {
            "payment_method": "",
            "deposit_term": "at_signature",
            "deposit_term_days": "20",
            "balance_term": "specific",
        },
    )

    gig.refresh_from_db()
    assert gig.deposit_term_days is None


def test_an_unknown_rule_is_refused(client, tenant):
    gig = _gig(tenant)

    response = client.post(
        _terms_url(gig),
        {"payment_method": "", "deposit_term": "whenever", "balance_term": "specific"},
    )

    assert response.status_code == 200
    gig.refresh_from_db()
    assert gig.deposit_term == "specific"


def test_the_completion_page_saves_the_rules_too(client, tenant):
    gig = _gig(tenant)

    client.post(
        _complete_url(gig),
        {
            "gig-deposit_term": "days_before",
            "gig-deposit_term_days": "10",
            "gig-balance_term": "end_of_next_month",
        },
    )

    gig.refresh_from_db()
    assert gig.deposit_due_on == D(2027, 3, 5) and gig.balance_due_on == D(2027, 4, 30)


def test_a_request_without_the_rules_keeps_the_current_ones(client, tenant):
    gig = _gig(
        tenant, deposit_term="days_before", deposit_term_days=10, balance_term="performance_plus_15"
    )
    services.refresh_due_dates(gig)

    client.post(_complete_url(gig), {"gig-signing_place": "Lyon"})

    gig.refresh_from_db()
    assert gig.deposit_term == "days_before" and gig.balance_term == "performance_plus_15"
    assert gig.balance_due_on == D(2027, 3, 30)


# --- the signature gives the date --------------------------------------------------------------


def test_signing_the_contract_gives_the_date_of_the_signature_rules(tenant):
    gig = _gig(tenant, deposit_term="signature_plus_10", balance_term="performance_plus_30")

    _sign(gig)

    assert gig.deposit_due_on == timezone.localdate() + datetime.timedelta(days=10)
    assert gig.balance_due_on == D(2027, 4, 14)


def test_signing_leaves_a_date_precise_alone(tenant):
    gig = _gig(tenant, deposit_due_on=D(2026, 12, 1))

    _sign(gig)

    assert gig.deposit_due_on == D(2026, 12, 1)


# --- the contracts ----------------------------------------------------------------------------


@pytest.mark.parametrize("template", ["model_2", "model_3", "model_4"])
def test_a_contract_states_the_rule_before_the_signature(tenant, template):
    gig = _gig(tenant, deposit_term="signature_plus_10", balance_term="performance_plus_15")
    services.refresh_due_dates(gig)

    html = render_to_string(f"documents/contracts/{template}.html", build_contract_context(gig))

    assert "15 jours après la prestation, soit le 30/03/2027" in html
    if template != "model_4":
        assert "10 jours après la signature du contrat" in html


@pytest.mark.parametrize("template", ["model_2", "model_3", "model_4"])
def test_a_contract_with_a_date_precise_prints_it_as_before(tenant, template):
    gig = _gig(tenant, deposit_due_on=D(2026, 12, 1), balance_due_on=D(2027, 4, 1))

    html = render_to_string(f"documents/contracts/{template}.html", build_contract_context(gig))

    assert "le 01/04/2027" in html
    if template != "model_4":
        assert "le 01/12/2026" in html


@pytest.mark.parametrize("template", ["model_2", "model_3", "model_4"])
def test_a_contract_without_terms_keeps_its_dots(tenant, template):
    gig = _gig(tenant)

    html = render_to_string(f"documents/contracts/{template}.html", build_contract_context(gig))

    assert "……" in html


# --- the screens and the dashboard -------------------------------------------------------------


def test_the_date_page_shows_the_rule_while_there_is_no_date(client, tenant):
    gig = _gig(tenant, deposit_term="at_signature")

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert "À la signature du contrat" in content


def test_a_rule_counts_as_a_term_for_the_dashboard(tenant):
    soon = TODAY + datetime.timedelta(days=10)
    without = make_gig(tenant=tenant, gig_fields={"status": Gig.Status.SIGNED, "date": soon})
    with_rule = make_gig(
        tenant=tenant,
        gig_fields={"status": Gig.Status.SIGNED, "date": soon, "deposit_term": "at_signature"},
    )

    texts = [item["text"] for item in bord.attention(tenant, TODAY)[0]]

    assert without.has_payment_terms is False and with_rule.has_payment_terms is True
    assert sum("Échéances de paiement à renseigner" in str(text) for text in texts) == 1


# --- CTR-06: three blocks ----------------------------------------------------------------------


def test_the_page_is_in_three_blocks_with_their_chips(client, tenant):
    gig = _gig(tenant)

    content = client.get(_complete_url(gig)).content.decode()

    positions = [content.index(f'id="block-{name}"') for name in ("contract", "budget", "roadmap")]
    assert positions == sorted(positions)
    for chip in ("volet-contrats", "volet-budget", "volet-regie"):
        assert chip in content


@pytest.mark.parametrize(
    ("block", "field", "other"),
    [
        ("contract", "gig-event_name", "block-budget"),
        ("budget", "gig-deposit_term", "block-roadmap"),
        ("roadmap", "gig-get_in_time", None),
    ],
)
def test_each_field_sits_in_its_block(client, tenant, block, field, other):
    gig = _gig(tenant)

    content = client.get(_complete_url(gig)).content.decode()

    start = content.index(f'id="block-{block}"')
    assert content.index(f'name="{field}"') > start
    if other:
        assert content.index(f'name="{field}"') < content.index(f'id="{other}"')


def test_every_field_of_the_form_is_still_on_the_page(client, tenant):
    gig = _gig(tenant)
    response = client.get(_complete_url(gig))
    content = response.content.decode()

    for name in response.context["forms"]["gig"].fields:
        assert f'name="gig-{name}"' in content, name


# --- isolation --------------------------------------------------------------------------------


def test_another_structures_date_cannot_be_edited(client, tenant):
    foreign = make_gig(tenant=TenantFactory(name="Autre"))

    assert client.get(_complete_url(foreign)).status_code == 404
    assert client.get(_terms_url(foreign)).status_code == 404
    assert client.post(_terms_url(foreign), {"deposit_term": "at_signature"}).status_code == 404
