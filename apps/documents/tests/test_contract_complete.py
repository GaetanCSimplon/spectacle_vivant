import datetime
import html as html_lib
from decimal import Decimal

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.gigs.factories import GigFactory
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
        "show-group_name": "Les Nocturnes",
        "show-sacem_number": "SAC-1",
        "show-sacem_object_number": "OBJ-2",
        "venue-capacity": "300",
        "promoter-siret": "98765432100011",
        "promoter-licence_number": "L-1",
        "promoter-representative_name": "Marc Durand",
        "promoter-representative_role": "Maire",
        "contract-signatory_name": "Léa Roux",
        "contract-signatory_role": "Trésorière",
        "tenant-siret": "12345678900012",
        "tenant-address": "1 rue des Arts\n69001 Lyon",
        "tenant-licence_number": "L-2",
        "tenant-representative_name": "Julie Martin",
        "tenant-representative_role": "Présidente",
        "tenant-jurisdiction_city": "Montpellier",
        "tenant-contract_party_label": "producteur",
    }
    data.update(overrides)
    return data


def test_complete_page_requires_login(client):
    gig = GigFactory()

    response = client.get(_url(gig))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_complete_page_shows_every_section_to_the_owner(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.get(_url(gig))

    assert response.status_code == 200
    content = response.content.decode()
    for section in ("La date", "Le spectacle", "Le lieu", "Ma structure", "Signature"):
        assert section in content
    assert 'name="tenant-jurisdiction_city"' in content


def test_ready_page_links_to_the_complete_form(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.get(reverse("documents:contract-ready", args=[gig.pk]))

    assert _url(gig) in response.content.decode()


def test_saving_updates_every_related_object(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.post(_url(gig), _payload())

    assert response.status_code == 302
    assert response.url == reverse("documents:contract-ready", args=[gig.pk])
    gig.refresh_from_db()
    gig.show.refresh_from_db()
    gig.venue.refresh_from_db()
    gig.promoter.refresh_from_db()
    tenant.refresh_from_db()
    assert gig.get_in_time == datetime.time(15, 30)
    assert gig.soundcheck_time == datetime.time(17, 0)
    assert gig.performance_time == datetime.time(21, 15)
    assert gig.crew_headcount == 6
    assert gig.invitations_count == 4
    assert gig.signing_place == "Lyon"
    assert gig.ticket_price == Decimal("12.00")
    assert gig.show.group_name == "Les Nocturnes"
    assert gig.show.sacem_number == "SAC-1"
    assert gig.show.sacem_object_number == "OBJ-2"
    assert gig.venue.capacity == 300
    assert gig.promoter.licence_number == "L-1"
    assert gig.promoter.representative_name == "Marc Durand"
    assert tenant.jurisdiction_city == "Montpellier"
    assert tenant.representative_role == "Présidente"
    assert tenant.contract_party_label == "producteur"


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
    data["tenant-contract_party_label"] = "artiste"

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
    tenant.refresh_from_db()
    assert gig.crew_headcount is None
    assert gig.show.group_name == ""
    assert tenant.jurisdiction_city == ""
    assert not Contract.objects.filter(gig=gig).exists()


def test_unknown_party_label_is_rejected(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.post(_url(gig), _payload(**{"tenant-contract_party_label": "cedant"}))

    assert response.status_code == 200
    tenant.refresh_from_db()
    assert tenant.contract_party_label == "artiste"


def test_a_member_who_is_not_owner_cannot_edit_the_tenant(client):
    tenant = _login(client, role="member")
    gig = GigFactory(tenant=tenant)

    get_response = client.get(_url(gig))
    post_response = client.post(_url(gig), _payload())

    assert 'name="tenant-jurisdiction_city"' not in get_response.content.decode()
    assert "Seul le propriétaire" in get_response.content.decode()
    assert post_response.status_code == 302
    tenant.refresh_from_db()
    assert tenant.jurisdiction_city == ""
    assert tenant.representative_name == ""
    assert tenant.contract_party_label == "artiste"
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
    other_gig.tenant.refresh_from_db()
    assert other_gig.signing_place == ""
    assert other_gig.show.group_name == ""
    assert other_gig.tenant.jurisdiction_city == ""
    assert not Contract.objects.filter(gig=other_gig).exists()


def test_saving_never_touches_another_tenants_data(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    other_gig = GigFactory()

    client.post(_url(gig), _payload())

    other_gig.show.refresh_from_db()
    other_gig.tenant.refresh_from_db()
    assert other_gig.show.group_name == ""
    assert other_gig.tenant.jurisdiction_city == ""
    assert other_gig.tenant.contract_party_label == "artiste"


def test_a_signed_contract_can_no_longer_be_edited(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    ContractFactory(gig=gig, status=Contract.Status.SIGNED)

    get_response = client.get(_url(gig))
    post_response = client.post(_url(gig), _payload())

    assert get_response.status_code == 302
    assert post_response.status_code == 302
    gig.refresh_from_db()
    tenant.refresh_from_db()
    assert gig.signing_place == ""
    assert tenant.jurisdiction_city == ""


def test_completed_values_end_up_in_the_contract(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    client.post(_url(gig), _payload())

    gig.refresh_from_db()
    contract = Contract.objects.get(gig=gig)
    context = build_contract_context(gig, contract)
    rendered = html_lib.unescape(render_to_string("documents/contract_pdf.html", context))
    text = " ".join(rendered.split())
    assert "Heure de get in : 15h30" in text
    assert "numéro SACEM : SAC-1" in text
    assert "capacité de la salle est de 300 places" in text
    assert "tribunaux de MONTPELLIER" in text
    assert "LE PRODUCTEUR fournira" in text
    assert "Léa Roux, Trésorière" in text
    assert "……" not in text
