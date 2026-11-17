import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import PromoterFactory
from ..forms import PromoterPublicForm

pytestmark = pytest.mark.django_db


def _edit(client, promoter, **fields):
    data = {"name": promoter.name, **fields}
    return client.post(reverse("addressbook:promoter-update", args=[promoter.pk]), data)


def _promoter(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return PromoterFactory(tenant=membership.tenant)


def test_the_contract_fields_are_saved(client):
    promoter = _promoter(client)

    response = _edit(
        client,
        promoter,
        legal_form="Association",
        licence_categories="2, 3",
        licence_exempt="on",
        licence_exemption_reason="Moins de 7 représentations",
        admin_contact_name="Léa Roy",
        admin_contact_email="lea@asso.fr",
        admin_contact_phone="0102030405",
    )

    assert response.status_code == 302
    promoter.refresh_from_db()
    assert promoter.legal_form == "Association"
    assert promoter.licence_categories == "2, 3"
    assert promoter.licence_exempt
    assert promoter.admin_contact_name == "Léa Roy"
    assert promoter.admin_contact_email == "lea@asso.fr"


def test_an_invalid_admin_email_is_refused(client):
    promoter = _promoter(client)

    response = _edit(client, promoter, admin_contact_email="pas un e-mail")

    assert response.status_code == 200
    promoter.refresh_from_db()
    assert promoter.admin_contact_email == ""


def test_the_signatory_confirmation_is_recorded_then_cancelled_when_they_change(client):
    promoter = _promoter(client)
    signatory = {"representative_name": "Paul Durand", "representative_role": "Maire"}

    _edit(client, promoter, representative_confirmed="on", **signatory)
    promoter.refresh_from_db()
    assert promoter.representative_confirmed
    assert promoter.representative_confirmed_on is not None

    # Same signatory, case left ticked by the form: still confirmed, date kept.
    confirmed_on = promoter.representative_confirmed_on
    _edit(client, promoter, representative_confirmed="on", **signatory)
    promoter.refresh_from_db()
    assert promoter.representative_confirmed_on == confirmed_on

    # Another role without ticking again: the confirmation is gone.
    promoter.representative_role = "Adjoint"
    promoter.save()
    assert not promoter.representative_confirmed


def test_unticking_cancels_the_confirmation(client):
    promoter = _promoter(client)
    signatory = {"representative_name": "Paul Durand", "representative_role": "Maire"}
    _edit(client, promoter, representative_confirmed="on", **signatory)

    _edit(client, promoter, **signatory)

    promoter.refresh_from_db()
    assert not promoter.representative_confirmed
    assert promoter.representative_confirmed_on is None


def test_the_signatory_cannot_be_confirmed_without_a_name(client):
    promoter = _promoter(client)

    response = _edit(client, promoter, representative_confirmed="on")

    assert response.status_code == 200
    promoter.refresh_from_db()
    assert not promoter.representative_confirmed


def test_the_public_form_cannot_confirm_the_signatory():
    form = PromoterPublicForm(
        {
            "representative_name": "Paul Durand",
            "representative_confirmed": "on",
            "representative_confirmed_as": "Paul Durand — ",
            "legal_form": "Association",
            "licence_categories": "1",
        }
    )

    assert form.is_valid()
    assert "representative_confirmed" not in form.fields
    assert "representative_confirmed_as" not in form.fields
    assert form.cleaned_data["legal_form"] == "Association"
    assert form.cleaned_data["licence_categories"] == "1"
