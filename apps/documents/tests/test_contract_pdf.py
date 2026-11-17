import datetime
import html as html_lib
import re

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

from ..factories import ContractFactory
from ..models import Contract, ContractVersion
from ..services import build_contract_context, generate_contract_pdf

pytestmark = pytest.mark.django_db


def test_generate_contract_pdf_creates_a_pdf_file():
    gig = GigFactory()

    contract = generate_contract_pdf(gig)

    version = contract.latest_version
    assert version.number == 1
    assert version.pdf_file.read().startswith(b"%PDF-")
    assert contract.status == Contract.Status.DRAFT


def test_generate_contract_pdf_keeps_a_single_contract_with_one_version_per_call():
    gig = GigFactory()

    generate_contract_pdf(gig)
    generate_contract_pdf(gig)

    assert Contract.objects.filter(gig=gig).count() == 1
    assert ContractVersion.objects.filter(contract__gig=gig).count() == 2


def test_generate_contract_pdf_does_not_touch_a_signed_contract():
    gig = GigFactory()
    contract = generate_contract_pdf(gig)
    contract.status = Contract.Status.SIGNED
    contract.save()

    generate_contract_pdf(gig)

    assert contract.versions.count() == 1


def test_contract_html_contains_the_gig_details_in_french_format():
    gig = GigFactory()  # default price is 500.00
    # A freshly built factory instance keeps the raw Python value it was given
    # (here a str); only a DB round-trip turns it into a Decimal, which is
    # what template localization (French comma) needs.
    gig.refresh_from_db()

    html = render_to_string("documents/contracts/contract.html", build_contract_context(gig))

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
    generate_contract_pdf(gig)

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
    html = render_to_string(
        "documents/contracts/contract.html", build_contract_context(gig, contract)
    )
    return " ".join(re.sub(r"<[^>]+>", " ", html_lib.unescape(html)).split())


def test_contract_names_the_tenant_as_the_producer_and_the_promoter_as_the_organiser():
    gig = GigFactory()

    html = _render(gig)

    assert "Le producteur" in html and "L’organisateur" in html
    assert gig.tenant.name in html and gig.promoter.name in html
    assert "L'ARTISTE" not in html


def test_contract_shows_the_signing_place():
    html = _render(GigFactory(signing_place="Lyon", copies_count=3))

    assert "Fait à Lyon" in html
    assert "Fait en 3 exemplaires originaux" in html


def test_contract_shows_invitations_count():
    html = _render(GigFactory(invitations_count=4))

    assert "Invitations réservées au producteur 4" in html


def test_contract_shows_the_parties_details():
    gig = GigFactory(
        tenant__licence_number="L-123",
        tenant__representative_name="Julie Martin",
        tenant__representative_role="Présidente",
        promoter__licence_number="L-456",
        promoter__representative_name="Marc Durand",
        promoter__representative_role="Maire",
    )

    html = _render(gig)

    assert "L-123" in html and "L-456" in html
    assert "Représenté par Julie Martin, en qualité de Présidente" in html
    assert "Représenté par Marc Durand, en qualité de Maire" in html


def test_contract_shows_show_venue_and_schedule_details():
    gig = GigFactory(
        show__group_name="Les Nocturnes",
        show__sacem_number="SAC-1",
        venue__capacity=300,
        get_in_time=datetime.time(15, 30),
        soundcheck_time=datetime.time(17, 0),
        performance_time=datetime.time(21, 15),
        crew_headcount=6,
    )

    html = _render(gig)

    assert "Les Nocturnes" in html
    assert "programme type déclaré à la SACEM : SAC-1" in html
    assert "Jauge maximale autorisée 300" in html
    assert "Arrivée de l’équipe 15h30" in html
    assert "Installation et balances 17h00" in html
    assert "Début de la représentation 21h15" in html
    assert "6 personne(s)" in html


def test_contract_unknown_arrival_and_capacity_point_to_the_welcome_sheet():
    html = _render(GigFactory(get_in_time=None, soundcheck_time=None, venue__capacity=None))

    assert html.count("À préciser dans la fiche d’accueil") == 3


def test_contract_free_gig_hides_the_ticket_price():
    free = _render(GigFactory(is_free=True, ticket_price=15))
    paid = _render(GigFactory(is_free=False, ticket_price=15))

    assert "Prix des places Gratuit" in free
    assert "Prix des places 15" in paid


def test_contract_franchise_regime_shows_the_mention_without_vat_amounts():
    html = _render(GigFactory(tenant__vat_regime="franchise", price="100.00"))

    assert "100,00 € net de TVA" in html
    assert "article 293 B du CGI" in html


def test_contract_not_taxable_regime_does_not_quote_article_293_b():
    html = _render(GigFactory(tenant__vat_regime="not_taxable", price="100.00"))

    assert "TVA non applicable, article 261-7-1° b du CGI." in html
    assert "293 B" not in html


def test_contract_taxable_regime_leaves_vat_to_fill_in_without_a_rate():
    html = _render(GigFactory(tenant__vat_regime="taxable"))

    assert "293 B" not in html
    assert "TVA — taux …… %" in html


def test_contract_taxable_regime_computes_vat_when_a_rate_is_set():
    gig = GigFactory(tenant__vat_regime="taxable", tenant__vat_rate="20.00", price="100.00")

    html = _render(gig)

    assert "293 B" not in html
    assert "100,00 € " in html and "20,00 €" in html and "120,00 €" in html


def test_contract_shows_the_signatory():
    gig = GigFactory()
    contract = ContractFactory(gig=gig, signatory_name="Julie Martin", signatory_role="Présidente")

    html = _render(gig, contract)

    assert "Représenté par Julie Martin, en qualité de Présidente" in html


def test_contract_without_optional_fields_still_renders_and_generates_a_pdf():
    gig = GigFactory()

    html = _render(gig)
    contract = generate_contract_pdf(gig)

    assert "Fait à ……" in html
    assert contract.latest_version.pdf_file.read().startswith(b"%PDF-")


def test_contract_escapes_html_in_free_text():
    gig = GigFactory(price_includes="<script>alert(1)</script>")

    html = render_to_string("documents/contracts/contract.html", build_contract_context(gig))

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def test_contract_preview_does_not_store_anything(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.get(reverse("documents:contract-preview", args=[gig.pk]))

    assert response.content.startswith(b"%PDF-")
    assert not Contract.objects.filter(gig=gig).exists()


def test_contract_preview_leaves_an_existing_draft_file_untouched(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    contract = generate_contract_pdf(gig)

    client.get(reverse("documents:contract-preview", args=[gig.pk]))

    assert contract.versions.count() == 1


def test_contract_preview_of_a_signed_contract_serves_the_frozen_pdf(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    contract = generate_contract_pdf(gig)
    contract.status = Contract.Status.SIGNED
    contract.save()
    frozen_bytes = contract.latest_version.pdf_file.read()
    gig.price_includes = "Ajouté après la signature"
    gig.save()

    response = client.get(reverse("documents:contract-preview", args=[gig.pk]))

    assert response.getvalue() == frozen_bytes


def test_cancelled_gig_without_contract_gets_none(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status="cancelled")

    for name in ("contract-preview", "contract-download"):
        response = client.get(reverse(f"documents:{name}", args=[gig.pk]))
        assert response.status_code == 302

    assert not Contract.objects.filter(gig=gig).exists()


def test_cancelled_gig_keeps_its_existing_contract_downloadable(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    contract = generate_contract_pdf(gig)
    version_count = contract.versions.count()
    gig.status = "cancelled"
    gig.save()

    response = client.get(reverse("documents:contract-download", args=[gig.pk]))

    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    assert contract.versions.count() == version_count


def test_cancelled_gig_hides_the_contract_actions_when_there_is_no_contract(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status="cancelled")

    response = client.get(reverse("gigs:detail", args=[gig.pk]))

    assert "Aperçu du contrat" not in response.content.decode()
    assert "Compléter le contrat" not in response.content.decode()


def test_contract_shows_the_vat_number_only_for_a_taxable_tenant():
    taxable = _render(GigFactory(tenant__vat_regime="taxable", tenant__vat_number="FR12345678901"))
    franchise = _render(GigFactory(tenant__vat_regime="franchise", tenant__vat_number="FR999"))

    assert "Numéro de TVA intracommunautaire du producteur : FR12345678901" in taxable
    assert "FR999" not in franchise
