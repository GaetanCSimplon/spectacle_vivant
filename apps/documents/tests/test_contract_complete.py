import datetime
import html as html_lib
import re
from decimal import Decimal

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

from ..factories import ContractFactory
from ..models import Contract
from ..services import build_contract_context

pytestmark = pytest.mark.django_db


def _url(gig):
    return reverse("documents:contract-complete", args=[gig.pk])


def _login(client, role="owner"):
    membership = MembershipFactory(role=role)
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {
        "gig-get_in_time": "15:30",
        "gig-soundcheck_time": "17:00",
        "gig-performance_time": "21:15",
        "gig-crew_headcount": "6",
        "gig-invitations_count": "4",
        "gig-signing_place": "Lyon",
        "gig-ticket_price": "12.00",
        "gig-deposit_percent": "30",
        "show-group_name": "Les Nocturnes",
        "show-sacem_number": "SAC-1",
        "show-sacem_object_number": "22-3-P-513447-57",
        "venue-capacity": "300",
        "promoter-siret": "98765432100011",
        "promoter-licence_number": "L-1",
        "promoter-representative_name": "Marc Durand",
        "promoter-representative_role": "Maire",
        "contract-signatory_name": "Léa Roux",
        "contract-signatory_role": "Trésorière",
    }
    data.update(overrides)
    return data


def test_complete_page_requires_login(client):
    gig = GigFactory()

    response = client.get(_url(gig))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_complete_page_shows_every_section(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.get(_url(gig))

    assert response.status_code == 200
    content = response.content.decode()
    for section in ("La date", "Le spectacle", "Le lieu", "Signature"):
        assert section in content
    assert 'name="tenant-' not in content
    assert reverse("tenants:settings") in content


def test_gig_detail_links_to_the_complete_form(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.get(reverse("gigs:detail", args=[gig.pk]))

    assert _url(gig) in response.content.decode()


def test_saving_updates_every_related_object(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.post(_url(gig), _payload())

    assert response.status_code == 302
    assert response.url == reverse("gigs:detail", args=[gig.pk])
    gig.refresh_from_db()
    gig.show.refresh_from_db()
    gig.venue.refresh_from_db()
    gig.promoter.refresh_from_db()
    assert gig.get_in_time == datetime.time(15, 30)
    assert gig.soundcheck_time == datetime.time(17, 0)
    assert gig.performance_time == datetime.time(21, 15)
    assert gig.crew_headcount == 6
    assert gig.invitations_count == 4
    assert gig.signing_place == "Lyon"
    assert gig.ticket_price == Decimal("12.00")
    assert gig.show.group_name == "Les Nocturnes"
    assert gig.show.sacem_number == "SAC-1"
    assert gig.show.sacem_object_number == "22-3-P-513447-57"
    assert gig.venue.capacity == 300
    assert gig.promoter.licence_number == "L-1"
    assert gig.promoter.representative_name == "Marc Durand"


def test_saving_creates_a_draft_contract_with_the_signatory(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    client.post(_url(gig), _payload())

    contract = Contract.objects.get(gig=gig)
    assert contract.tenant == tenant
    assert contract.status == Contract.Status.DRAFT
    assert contract.signatory_name == "Léa Roux"
    assert contract.signatory_role == "Trésorière"


def test_saving_updates_the_existing_contract_instead_of_duplicating_it(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    ContractFactory(gig=gig, signatory_name="Ancien")

    client.post(_url(gig), _payload())

    assert Contract.objects.filter(gig=gig).count() == 1
    assert Contract.objects.get(gig=gig).signatory_name == "Léa Roux"


def test_a_free_gig_resets_the_ticket_price_to_zero(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    client.post(_url(gig), _payload(**{"gig-is_free": "on", "gig-ticket_price": "15.00"}))

    gig.refresh_from_db()
    assert gig.is_free is True
    assert gig.ticket_price == Decimal("0.00")


def test_a_free_gig_without_submitted_price_is_accepted(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    data = _payload(**{"gig-is_free": "on"})
    del data["gig-ticket_price"]  # a disabled input is not sent by the browser

    response = client.post(_url(gig), data)

    assert response.status_code == 302
    gig.refresh_from_db()
    assert gig.ticket_price == Decimal("0.00")


def test_empty_optional_fields_are_accepted(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    data = {key: "" for key in _payload()}

    response = client.post(_url(gig), data)

    assert response.status_code == 302
    gig.refresh_from_db()
    assert gig.invitations_count == 0
    assert gig.get_in_time is None
    assert gig.crew_headcount is None


def test_invalid_values_save_nothing_and_show_errors(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    data = _payload(**{"gig-crew_headcount": "-3", "gig-get_in_time": "pas une heure"})

    response = client.post(_url(gig), data)

    assert response.status_code == 200
    assert "Certains champs sont à corriger" in response.content.decode()
    gig.refresh_from_db()
    gig.show.refresh_from_db()
    assert gig.crew_headcount is None
    assert gig.show.group_name == ""
    assert not Contract.objects.filter(gig=gig).exists()


def test_the_form_no_longer_edits_the_tenant(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    client.post(_url(gig), _payload(**{"tenant-jurisdiction_city": "Montpellier"}))

    tenant.refresh_from_db()
    assert tenant.jurisdiction_city == ""


def test_a_member_who_is_not_owner_can_fill_in_the_date(client):
    tenant = _login(client, role="member")
    gig = GigFactory(tenant=tenant)

    response = client.post(_url(gig), _payload())

    assert response.status_code == 302
    gig.refresh_from_db()
    assert gig.signing_place == "Lyon"


def test_another_tenants_gig_returns_404_and_is_left_untouched(client):
    _login(client)
    other_gig = GigFactory()

    get_response = client.get(_url(other_gig))
    post_response = client.post(_url(other_gig), _payload())

    assert get_response.status_code == 404
    assert post_response.status_code == 404
    other_gig.refresh_from_db()
    other_gig.show.refresh_from_db()
    assert other_gig.signing_place == ""
    assert other_gig.show.group_name == ""
    assert not Contract.objects.filter(gig=other_gig).exists()


def test_saving_never_touches_another_tenants_data(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    other_gig = GigFactory()

    client.post(_url(gig), _payload())

    other_gig.show.refresh_from_db()
    assert other_gig.show.group_name == ""


def test_a_signed_contract_can_no_longer_be_edited(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    ContractFactory(gig=gig, status=Contract.Status.SIGNED)

    get_response = client.get(_url(gig))
    post_response = client.post(_url(gig), _payload())

    assert get_response.status_code == 302
    assert post_response.status_code == 302
    gig.refresh_from_db()
    assert gig.signing_place == ""


def test_completed_values_end_up_in_the_contract(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    client.post(_url(gig), _payload())

    gig.refresh_from_db()
    contract = Contract.objects.get(gig=gig)
    context = build_contract_context(gig, contract)
    rendered = html_lib.unescape(render_to_string("documents/contracts/contract.html", context))
    text = " ".join(re.sub(r"<[^>]+>", " ", rendered).split())
    assert "Arrivée de l’équipe 15h30" in text
    assert "programme type déclaré à la SACEM : SAC-1" in text
    assert "Jauge maximale autorisée 300" in text
    assert "Représenté par Léa Roux, en qualité de Trésorière" in text


def test_the_hidden_fields_are_not_edited_and_keep_their_value(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, conditions="Ancien texte", signature_deadline_days=8)

    page = client.get(_url(gig)).content.decode()
    client.post(
        _url(gig), _payload(**{"gig-conditions": "Nouveau", "gig-signature_deadline_days": "3"})
    )

    gig.refresh_from_db()
    assert "gig-conditions" not in page and "gig-signature_deadline_days" not in page
    assert gig.conditions == "Ancien texte"
    assert gig.signature_deadline_days == 8


def test_the_contract_sheet_fields_are_saved(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.post(
        _url(gig),
        _payload(
            **{
                "gig-setting": "outdoor",
                "gig-outdoor_fallback": "none_accepted",
                "gig-outdoor_procedure": "Décision commune",
                "gig-outdoor_referents": "Léa, Marc",
                "gig-transport_covered_by": "producer",
                "gig-transport_notes": "Train",
                "gig-price_includes": "Le son",
                "gig-extra_fees_description": "Location de piano",
                "gig-extra_fees_amount": "120.50",
                "gig-extra_fees_accepted": "on",
                "gig-billing_notes": "Bon de commande 42",
                "gig-deposit_required": "true",
                "gig-onsite_contact_name": "Sam",
                "gig-onsite_contact_phone": "0102030405",
            }
        ),
    )

    assert response.status_code == 302
    gig.refresh_from_db()
    assert gig.setting == "outdoor"
    assert gig.outdoor_fallback == "none_accepted"
    assert gig.transport_covered_by == "producer"
    assert gig.extra_fees_amount == Decimal("120.50")
    assert gig.extra_fees_accepted
    assert gig.deposit_required is True
    assert gig.onsite_contact_name == "Sam"


def test_the_contract_sheet_answers_stay_unanswered_when_left_empty(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    client.post(_url(gig), _payload())

    gig.refresh_from_db()
    assert gig.setting == ""
    assert gig.deposit_required is None


def test_negative_extra_fees_are_rejected(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.post(_url(gig), _payload(**{"gig-extra_fees_amount": "-5"}))

    assert response.status_code == 200
    gig.refresh_from_db()
    assert gig.extra_fees_amount is None


def test_the_show_form_names_the_sacem_programme_type(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    assert "programme type SACEM" in client.get(_url(gig)).content.decode()


def test_deposit_percent_defaults_to_zero_and_can_be_changed_per_gig(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    assert Gig._meta.get_field("deposit_percent").default == 0

    client.post(_url(gig), _payload(**{"gig-deposit_percent": "40.50"}))

    gig.refresh_from_db()
    assert gig.deposit_percent == Decimal("40.50")


@pytest.mark.parametrize("value", ["-1", "100.01", "abc"])
def test_invalid_deposit_percent_is_rejected(client, value):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.post(_url(gig), _payload(**{"gig-deposit_percent": value}))

    assert response.status_code == 200
    gig.refresh_from_db()
    assert gig.deposit_percent == 30


def test_empty_deposit_percent_keeps_the_current_value(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, deposit_percent=Decimal("45"))

    client.post(_url(gig), _payload(**{"gig-deposit_percent": ""}))

    gig.refresh_from_db()
    assert gig.deposit_percent == Decimal("45.00")


def test_the_completion_page_and_its_link_are_named_after_the_contract(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status="option")

    detail = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()
    page = client.get(_url(gig)).content.decode()

    assert "Compléter le contrat" in detail
    assert "Compléter le contrat — Bòrd Pro" in page
    assert "Compléter la date" not in detail + page


# --- sending the organiser form from here (F-89) --------------------------------------------------


def _invite_url(gig):
    return reverse("addressbook:promoter-invite", args=[gig.promoter.pk])


def test_the_page_offers_to_send_the_form_to_the_organiser(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status="option")

    page = client.get(_url(gig)).content.decode()

    assert "Envoyer un formulaire à l'organisateur" in page
    assert f'action="{_invite_url(gig)}"' in page
    assert f'name="gig" value="{gig.pk}"' in page


def test_sending_the_form_from_here_comes_back_here_and_shows_the_link(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status="option")

    response = client.post(_invite_url(gig), {"gig": gig.pk})

    assert response.status_code == 302
    assert response.url == _url(gig)
    page = client.get(response.url).content.decode()
    assert "Un lien est actif jusqu'au" in page
    assert "Envoyer un formulaire à l'organisateur" not in page


def test_an_answered_form_is_offered_for_review_from_here(client):
    from django.utils import timezone

    from apps.addressbook.services import create_invitation

    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status="option")
    invitation = create_invitation(gig.promoter, None)
    invitation.completed_at = timezone.now()
    invitation.save(update_fields=["completed_at"])

    page = client.get(_url(gig)).content.decode()

    assert "L'organisateur a répondu le" in page
    assert reverse("addressbook:promoter-answer", args=[gig.promoter.pk]) in page


def test_the_gig_of_another_organiser_or_structure_is_ignored(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status="option")
    same_tenant_other_promoter = GigFactory(tenant=tenant, status="option")
    other_tenant_gig = GigFactory(status="option")

    for foreign in (same_tenant_other_promoter, other_tenant_gig):
        response = client.post(_invite_url(gig), {"gig": foreign.pk})
        assert response.url == reverse("addressbook:promoter-detail", args=[gig.promoter.pk])

    for junk in ("abc", "", "-1", "1;2"):
        response = client.post(_invite_url(gig), {"gig": junk})
        assert response.url == reverse("addressbook:promoter-detail", args=[gig.promoter.pk])


def test_another_tenant_cannot_send_a_form_for_my_organiser(client):
    _login(client)
    foreign = GigFactory()

    assert client.post(_invite_url(foreign), {"gig": foreign.pk}).status_code == 404
