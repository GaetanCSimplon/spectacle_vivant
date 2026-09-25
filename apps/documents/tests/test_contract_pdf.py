import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

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
