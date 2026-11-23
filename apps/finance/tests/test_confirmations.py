"""Every action that changes something says so (PR 0 of the navigation work)."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import ExpenseClaimFactory, ExpenseFactory
from .helpers import TENANT_FIELDS, issued_invoice, make_gig
from .test_expense_claims import _data as _claim_data
from .test_expense_claims import _on_gig, _person_with_space
from .test_expense_claims import _url as _team_url
from .test_views import HTMX, _expense_data, _payment_data, _url

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def tenant(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    return membership.tenant


@pytest.fixture
def gig(tenant):
    return make_gig(tenant=tenant, price="1000.00")


def _says(client, url, data, text):
    response = client.post(url, data, follow=True)
    assert text in response.content.decode()
    return response


def test_payments_are_confirmed(client, gig):
    invoice = issued_invoice(gig)
    _says(
        client,
        _url("payment-add", gig, invoice.pk),
        _payment_data(),
        "Le paiement est enregistré.",
    )
    payment = invoice.payments.get()
    _says(
        client,
        _url("payment-edit", gig, payment.pk),
        _payment_data("500.00"),
        "Le paiement est modifié.",
    )
    _says(client, _url("payment-delete", gig, payment.pk), {}, "Le paiement est supprimé.")


def test_expenses_are_confirmed(client, gig):
    _says(client, _url("expense-add", gig), _expense_data(), "La dépense est enregistrée.")
    expense = gig.expenses.get()
    _says(
        client,
        _url("expense-edit", gig, expense.pk),
        _expense_data(label="Péage"),
        "La dépense est modifiée.",
    )
    _says(client, _url("expense-delete", gig, expense.pk), {}, "La dépense est supprimée.")


def test_reimbursing_is_confirmed(client, gig, tenant):
    from apps.tenants.factories import PersonFactory

    expense = ExpenseFactory(
        tenant=tenant, gig=gig, person=PersonFactory(tenant=tenant), amount="10.00"
    )
    url = _url("expense-reimburse", gig, expense.pk)
    _says(client, url, {}, "marquée remboursée")
    _says(client, url, {"state": "undo"}, "Le remboursement est annulé.")


def test_deciding_a_proposal_is_confirmed(client, gig, tenant):
    claim = ExpenseClaimFactory(tenant=tenant, gig=gig)
    _says(client, _url("claim-accept", gig, claim.pk), {}, "La proposition est acceptée")
    other = ExpenseClaimFactory(tenant=tenant, gig=gig)
    _says(client, _url("claim-refuse", gig, other.pk), {}, "La proposition est refusée.")


def test_htmx_shows_the_message_once_inside_the_block(client, gig):
    response = client.post(_url("expense-add", gig), _expense_data(), **HTMX)

    content = response.content.decode()
    assert "<html" not in content
    assert content.count("La dépense est enregistrée.") == 1
    assert 'id="finance-body"' in content
    # consumed: the next page does not repeat it
    assert "La dépense est enregistrée." not in client.get(_url("page", gig)).content.decode()


def test_an_invalid_form_gives_no_success_message(client, gig):
    response = client.post(_url("expense-add", gig), _expense_data(amount=""), **HTMX)

    assert "est enregistrée" not in response.content.decode()


def test_the_team_space_confirms_each_step(client):
    person = _person_with_space()
    gig = _on_gig(person)
    response = client.post(_team_url("team-expenses", person), _claim_data(gig), follow=True)
    text = response.content.decode()
    assert "Votre dépense est envoyée" in text
    claim = person.expense_claims.get()
    _says(
        client,
        _team_url("team-expense-edit", person, claim.pk),
        _claim_data(gig, label="Péage"),
        "Votre proposition est modifiée.",
    )
    _says(
        client,
        reverse("team-expense-delete", args=[person.access_token, claim.pk]),
        {},
        "Votre proposition est retirée.",
    )
