import datetime

import pytest
from django.test import Client
from django.urls import reverse

from apps.addressbook import services as promoter_services
from apps.addressbook.factories import PromoterFactory
from apps.addressbook.forms import PromoterPublicForm
from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

from ..models import Contract

pytestmark = pytest.mark.django_db

PROFILE_URL = reverse("tenants:settings")


def _login(client):
    membership = MembershipFactory(tenant__name="Compagnie A")
    client.force_login(membership.user)
    return membership


def _profile_payload(**overrides):
    data = {"name": "Compagnie A", "vat_regime": "franchise", "vat_rate": ""}
    data.update(overrides)
    return data


# --- the structure ----------------------------------------------------------------------


def test_the_structure_keeps_its_phone_email_and_bic(client):
    membership = _login(client)

    response = client.post(
        PROFILE_URL,
        _profile_payload(phone="04 67 00 00 00", email="contact@example.org", bic="agri fr pp"),
    )

    assert response.status_code == 302
    tenant = membership.tenant
    tenant.refresh_from_db()
    assert (tenant.phone, tenant.email, tenant.bic) == (
        "04 67 00 00 00",
        "contact@example.org",
        "AGRIFRPP",
    )


@pytest.mark.parametrize("bic", ["AGRI", "AGRIFRPP1", "12345678", "AGRI-FRPP"])
def test_a_malformed_bic_is_refused(client, bic):
    membership = _login(client)

    response = client.post(PROFILE_URL, _profile_payload(bic=bic))

    assert response.status_code == 200
    membership.tenant.refresh_from_db()
    assert membership.tenant.bic == ""


def test_a_bad_email_is_refused(client):
    _login(client)

    assert client.post(PROFILE_URL, _profile_payload(email="pas-un-mail")).status_code == 200


# --- the organiser ----------------------------------------------------------------------


def _promoter_payload(**overrides):
    data = {"name": "Mairie de Sète"}
    data.update(overrides)
    return data


def test_the_organiser_keeps_its_ape_code_and_vat_number(client):
    membership = _login(client)

    client.post(
        reverse("addressbook:promoter-create"),
        _promoter_payload(code_ape="84.11 z", vat_number="fr 12 345678901"),
    )

    promoter = membership.tenant.promoter_set.get()
    assert (promoter.code_ape, promoter.vat_number) == ("8411Z", "FR12345678901")


def test_a_malformed_ape_code_is_refused_for_an_organiser(client):
    membership = _login(client)

    response = client.post(
        reverse("addressbook:promoter-create"), _promoter_payload(code_ape="ABCDE")
    )

    assert response.status_code == 200
    assert not membership.tenant.promoter_set.exists()


def test_the_organiser_page_shows_the_ape_code_and_vat_number(client):
    membership = _login(client)
    promoter = PromoterFactory(
        tenant=membership.tenant, code_ape="8411Z", vat_number="FR12345678901"
    )

    page = client.get(reverse("addressbook:promoter-detail", args=[promoter.pk])).content.decode()

    assert "8411Z" in page and "FR12345678901" in page


def test_the_form_sent_to_the_organiser_collects_the_ape_code_and_vat_number():
    promoter = PromoterFactory(code_ape="", vat_number="")
    invitation = promoter_services.create_invitation(promoter, None)

    response = Client().post(
        reverse("promoter-form-public", args=[invitation.token]),
        {"city": "Sète", "code_ape": "84.11Z", "vat_number": "FR 12 345678901"},
    )

    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.response["fields"]["code_ape"] == "8411Z"
    assert invitation.response["fields"]["vat_number"] == "FR12345678901"
    promoter.refresh_from_db()
    assert (promoter.code_ape, promoter.vat_number) == ("", "")


def test_the_organiser_can_apply_the_ape_code_and_vat_number_after_review(client):
    membership = _login(client)
    promoter = PromoterFactory(tenant=membership.tenant, code_ape="", vat_number="")
    invitation = promoter_services.create_invitation(promoter, None)
    form = PromoterPublicForm({"code_ape": "8411Z", "vat_number": "FR12345678901"})
    assert form.is_valid(), form.errors
    promoter_services.submit_response(invitation, form.cleaned_data)

    client.post(
        reverse("addressbook:promoter-answer", args=[promoter.pk]),
        {"fields": ["code_ape", "vat_number"]},
    )

    promoter.refresh_from_db()
    assert (promoter.code_ape, promoter.vat_number) == ("8411Z", "FR12345678901")


def test_a_malformed_ape_code_is_refused_by_the_public_form():
    promoter = PromoterFactory()
    invitation = promoter_services.create_invitation(promoter, None)

    response = Client().post(
        reverse("promoter-form-public", args=[invitation.token]), {"code_ape": "oups"}
    )

    assert response.status_code == 200
    invitation.refresh_from_db()
    assert invitation.response == {}


# --- the date ---------------------------------------------------------------------------


def _complete_url(gig):
    return reverse("documents:contract-complete", args=[gig.pk])


def test_a_new_gig_has_one_performance_and_two_copies():
    gig = GigFactory()

    assert (gig.performances_count, gig.copies_count) == (1, 2)
    assert gig.event_name == "" and gig.deposit_due_on is None


def test_the_date_form_saves_the_contract_wording_fields(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)

    response = client.post(
        _complete_url(gig),
        {
            "gig-event_name": "Fête de la musique",
            "gig-performances_count": "2",
            "gig-copies_count": "3",
            "gig-payment_method": "cheque",
            "gig-deposit_percent": "30",
            "gig-deposit_due_on": "2026-11-01",
            "gig-balance_due_on": "2026-12-15",
            "gig-meals_covered_by": "organiser",
            "gig-meals_count": "3",
            "gig-meals_notes": "chauds",
            "gig-lodging_covered_by": "producer",
            "gig-lodging_nights": "2",
            "gig-lodging_notes": "",
            "gig-local_transport": "Navette",
            "gig-other_hospitality": "Parking gardé",
        },
    )

    assert response.status_code == 302
    gig.refresh_from_db()
    assert gig.event_name == "Fête de la musique"
    assert (gig.performances_count, gig.copies_count) == (2, 3)
    assert gig.payment_method == "cheque"
    assert gig.deposit_due_on == datetime.date(2026, 11, 1)
    assert gig.balance_due_on == datetime.date(2026, 12, 15)
    assert (gig.meals, gig.lodging, gig.local_transport) == (
        "À la charge de l'Organisateur : 3 repas. chauds",
        "À la charge du Producteur : 2 nuits",
        "Navette",
    )
    assert gig.other_hospitality == "Parking gardé"


def test_empty_counts_keep_their_defaults(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)

    client.post(_complete_url(gig), {"gig-performances_count": "", "gig-copies_count": ""})

    gig.refresh_from_db()
    assert (gig.performances_count, gig.copies_count) == (1, 2)


@pytest.mark.parametrize(
    "field,value",
    [
        ("gig-performances_count", "0"),
        ("gig-copies_count", "0"),
        ("gig-payment_method", "bitcoin"),
        ("gig-deposit_due_on", "pas une date"),
    ],
)
def test_bad_wording_values_are_refused(client, field, value):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)

    response = client.post(_complete_url(gig), {field: value})

    assert response.status_code == 200
    gig.refresh_from_db()
    assert (gig.performances_count, gig.copies_count) == (1, 2)


def test_a_signed_contract_refuses_the_new_fields(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)
    Contract.objects.create(gig=gig, tenant=gig.tenant, status=Contract.Status.SIGNED)

    client.post(_complete_url(gig), {"gig-event_name": "Trop tard"})

    gig.refresh_from_db()
    assert gig.event_name == ""


def test_another_structure_cannot_complete_this_gig(client):
    _login(client)
    other = GigFactory()

    response = client.post(_complete_url(other), {"gig-event_name": "Intrus"})

    assert response.status_code == 404
    other.refresh_from_db()
    assert other.event_name == ""
