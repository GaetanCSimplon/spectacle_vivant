import html as html_lib

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

from ..factories import ContractFactory
from ..models import Contract
from ..services import build_contract_context, generate_contract_pdf

pytestmark = pytest.mark.django_db


def test_generate_contract_pdf_creates_a_pdf_file():
    gig = GigFactory()

    contract = generate_contract_pdf(gig)

    assert contract.pdf_file.name
    assert contract.pdf_file.read().startswith(b"%PDF-")
    assert contract.generated_at is not None
    assert contract.status == Contract.Status.DRAFT


def test_generate_contract_pdf_is_idempotent_for_a_draft_contract():
    gig = GigFactory()

    generate_contract_pdf(gig)
    generate_contract_pdf(gig)

    assert Contract.objects.filter(gig=gig).count() == 1


def test_generate_contract_pdf_does_not_touch_a_signed_contract():
    gig = GigFactory()
    contract = generate_contract_pdf(gig)
    contract.status = Contract.Status.SIGNED
    contract.save()
    signed_file_name = contract.pdf_file.name

    generate_contract_pdf(gig)

    contract.refresh_from_db()
    assert contract.pdf_file.name == signed_file_name


def test_contract_html_contains_the_gig_details_in_french_format():
    gig = GigFactory()  # default price is 500.00
    # A freshly built factory instance keeps the raw Python value it was given
    # (here a str); only a DB round-trip turns it into a Decimal, which is
    # what template localization (French comma) needs.
    gig.refresh_from_db()

    html = render_to_string("documents/contract_pdf.html", build_contract_context(gig))

    assert gig.show.title in html
    assert gig.promoter.name in html
    assert gig.venue.name in html
    assert gig.tenant.name in html
    assert "500,00" in html
    assert str(gig.date.year) in html


def test_contract_preview_requires_login(client):
    gig = GigFactory()

    response = client.get(reverse("documents:contract-preview", args=[gig.pk]))

    assert response.status_code == 302


def test_contract_preview_returns_a_pdf_for_the_gigs_tenant(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant)

    response = client.get(reverse("documents:contract-preview", args=[gig.pk]))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"


def test_contract_download_is_an_attachment(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant)

    response = client.get(reverse("documents:contract-download", args=[gig.pk]))

    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]


def test_contract_preview_of_another_tenants_gig_returns_404(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    other_gig = GigFactory()

    response = client.get(reverse("documents:contract-preview", args=[other_gig.pk]))

    assert response.status_code == 404


def _render(gig, contract=None):
    gig.refresh_from_db()
    html = render_to_string("documents/contract_pdf.html", build_contract_context(gig, contract))
    return html_lib.unescape(html)


def test_contract_names_the_tenant_as_the_artist_by_default():
    gig = GigFactory()

    html = _render(gig)

    assert "L'artiste" in html
    assert "Le producteur" not in html


def test_contract_names_the_tenant_as_the_producer_when_configured():
    gig = GigFactory(tenant__contract_party_label="producteur")

    html = _render(gig)

    assert "Le producteur" in html
    assert "L'artiste" not in html


def test_contract_shows_the_signing_place_and_invitations():
    gig = GigFactory(signing_place="Lyon", invitations_count=4)

    html = _render(gig)

    assert "à Lyon, le" in html
    assert "Nombre d'invitations : 4" in html


def test_contract_shows_the_signatory():
    gig = GigFactory()
    contract = ContractFactory(gig=gig, signatory_name="Julie Martin", signatory_role="Présidente")

    html = _render(gig, contract)

    assert "Julie Martin, Présidente" in html


def test_contract_without_optional_fields_still_renders_and_generates_a_pdf():
    gig = GigFactory()

    html = _render(gig)
    contract = generate_contract_pdf(gig)

    assert "Nombre d'invitations" not in html
    assert " à , le" not in html
    assert contract.pdf_file.read().startswith(b"%PDF-")
