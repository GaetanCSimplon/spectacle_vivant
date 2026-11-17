import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.documents.factories import make_contract_ready
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory
from apps.tenants.models import Tenant

from ..models import Contract, ContractVariant
from ..services import (
    build_contract_context,
    contract_variant,
    generate_contract_pdf,
    render_contract_pdf,
)

pytestmark = pytest.mark.django_db


def _member_gig(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return GigFactory(tenant=membership.tenant)


def _html(gig, contract=None):
    return render_to_string(
        "documents/contracts/contract.html", build_contract_context(gig, contract)
    )


def _gig_with_regime(regime, **tenant_fields):
    gig = GigFactory()
    Tenant.objects.filter(pk=gig.tenant.pk).update(vat_regime=regime, **tenant_fields)
    return Gig.objects.get(pk=gig.pk)


def test_the_variant_follows_the_vat_regime_of_the_structure():
    assert contract_variant(Tenant(vat_regime="taxable")) == ContractVariant.WITH_VAT
    assert contract_variant(Tenant(vat_regime="franchise")) == ContractVariant.WITHOUT_VAT
    assert contract_variant(Tenant(vat_regime="not_taxable")) == ContractVariant.WITHOUT_VAT


def test_article_5_with_vat_shows_the_three_amounts():
    gig = _gig_with_regime("taxable", vat_rate="20.00")

    html = _html(gig)

    assert "Prix de cession hors taxes" in html
    assert "Total toutes taxes comprises" in html
    assert "net de TVA" not in html


def test_article_5_without_vat_shows_the_mention_and_no_zero_rate():
    gig = _gig_with_regime("not_taxable", vat_exemption_note="Article 261 du CGI.")

    html = _html(gig)

    assert "net de TVA" in html
    assert "Article 261 du CGI." in html
    assert "Aucune TVA n’est facturée" in html
    assert "Total toutes taxes comprises" not in html
    assert "0 %" not in html


def test_no_template_variable_is_left_in_the_document():
    html = _html(GigFactory())

    assert "{{" not in html
    assert "{%" not in html


def test_a_new_contract_and_its_first_version_get_the_variant_and_the_snapshots():
    gig = _gig_with_regime("franchise")

    version = generate_contract_pdf(gig).latest_version

    assert version.variant == ContractVariant.WITHOUT_VAT
    assert version.fiscal_snapshot["regime"] == "franchise"
    assert version.parties_snapshot["producer"]["name"] == gig.tenant.name
    assert version.parties_snapshot["organiser"]["name"] == gig.promoter.name


def test_the_snapshot_keeps_the_identity_when_the_structure_changes_afterwards():
    gig = GigFactory()
    old_name = gig.tenant.name
    version = generate_contract_pdf(gig).latest_version

    Tenant.objects.filter(pk=gig.tenant.pk).update(name="Autre nom")
    version.refresh_from_db()

    assert version.parties_snapshot["producer"]["name"] == old_name


def test_the_pdf_of_a_stored_version_is_rendered_from_its_snapshot():
    gig = GigFactory()
    version = generate_contract_pdf(gig).latest_version
    snapshots = (version.fiscal_snapshot, version.parties_snapshot)
    snapshots[1]["producer"]["name"] = "Nom figé"

    html = render_to_string(
        "documents/contracts/contract.html",
        build_contract_context(gig, gig.contract, snapshots=snapshots),
    )

    assert "Nom figé" in html


def test_regenerating_adds_a_version_and_keeps_the_old_one():
    gig = GigFactory()
    generate_contract_pdf(gig)

    contract = generate_contract_pdf(gig)

    assert [v.number for v in contract.versions.all()] == [2, 1]


def test_a_signed_contract_is_never_regenerated():
    gig = GigFactory()
    contract = generate_contract_pdf(gig)
    Contract.objects.filter(pk=contract.pk).update(status=Contract.Status.SIGNED)

    contract = generate_contract_pdf(gig)

    assert contract.versions.count() == 1


def test_the_preview_renders_a_pdf():
    assert render_contract_pdf(GigFactory()).startswith(b"%PDF")


def test_the_generate_view_needs_no_model_choice(client):
    gig = _member_gig(client)
    make_contract_ready(gig)

    response = client.post(reverse("documents:contract-generate", args=[gig.pk]))

    assert response.status_code == 302
    assert gig.contract.latest_version.variant in ContractVariant.values


def test_there_is_no_model_selector_any_more(client):
    gig = _member_gig(client)

    html = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()

    assert 'name="template"' not in html
