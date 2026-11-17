import datetime
import html as html_lib
import re
from decimal import Decimal

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.addressbook.factories import PromoterFactory
from apps.documents.factories import make_contract_ready
from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory, TenantFactory

from ..models import Contract, ContractTemplate
from ..services import (
    build_contract_context,
    generate_contract_pdf,
    payment_schedule,
    render_contract_pdf,
)

pytestmark = pytest.mark.django_db

TEMPLATE = "documents/contracts/model_2.html"


def _render(gig, contract=None):
    gig.refresh_from_db()
    html = render_to_string(TEMPLATE, build_contract_context(gig, contract))
    html = html.split("</style>")[1]  # the CSS is not part of the contract text
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", html)).split())


def _gig(**overrides):
    tenant_fields = overrides.pop("tenant_fields", {})
    tenant = TenantFactory(**tenant_fields)
    return GigFactory(tenant=tenant, **overrides)


# --- the content ------------------------------------------------------------------------


def test_the_parties_and_the_show_come_from_our_data():
    tenant = TenantFactory(
        name="Compagnie du Soleil",
        siret="12345678900012",
        code_ape="9001Z",
        phone="04 67 00 00 00",
        email="contact@example.org",
        iban="FR7630006000011234567890189",
        bic="AGRIFRPP",
        jurisdiction_city="Montpellier",
        vat_regime="franchise",
    )
    promoter = PromoterFactory(
        tenant=tenant,
        name="Mairie de Sète",
        code_ape="8411Z",
        vat_number="FR12345678901",
        phone="04 99 00 00 00",
    )
    gig = GigFactory(tenant=tenant, promoter=promoter, event_name="Fête de la musique")

    text = _render(gig)

    assert "Raison sociale : Compagnie du Soleil" in text
    assert "SIRET : 123 456 789 00012" in text
    assert "Code APE : 9001Z" in text
    assert "Téléphone : 04 67 00 00 00" in text
    assert "Raison sociale : Mairie de Sète" in text
    assert "Code APE : 8411Z" in text
    assert "N° TVA intracommunautaire : FR12345678901" in text
    assert f"Nom du spectacle : {gig.show.title}" in text
    assert "Nom de l’événement : Fête de la musique" in text
    assert "IBAN : FR7630006000011234567890189" in text
    assert "BIC : AGRIFRPP" in text
    assert "tribunaux de Montpellier" in text
    assert "Le règlement sera établi à l’ordre de Compagnie du Soleil" in text


def test_the_legal_clauses_are_kept_word_for_word():
    text = _render(_gig())

    for clause in [
        "L’Organisateur ne pourra invoquer une insuffisance des recettes pour se soustraire au "
        "règlement du montant prévu au présent contrat.",
        "Toute annulation du fait de l’Organisateur entraînera pour celui-ci l’obligation de "
        "verser au Producteur l’intégralité du prix de cession.",
        "Aucune connexion à la console son ne pourra être réalisée sans l’accord préalable de "
        "l’artiste.",
        "En cas de litige relatif à l’exécution ou à l’interprétation du présent contrat",
    ]:
        assert clause in text
    for number in range(1, 12):
        assert f"{number}. " in text


def test_every_empty_value_prints_as_dots_and_nothing_breaks():
    gig = _gig(tenant_fields={"vat_regime": "taxable", "vat_rate": None})

    text = _render(gig)

    assert "Nom commercial / label : ……" in text
    assert "Capital social : ……" in text
    assert "Nom de l’événement : ……" in text
    assert "Restauration : ……" in text
    assert "dans un délai de …… jours" in text
    assert "tribunaux de ……" in text
    assert "None" not in text


def test_the_hosting_paragraphs_only_appear_when_the_element_is_provided():
    empty = _render(_gig())
    full = _render(
        _gig(
            meals="4 repas",
            lodging="2 chambres",
            local_transport="Navette",
            other_hospitality="Parking",
        )
    )

    assert "Les repas devront être chauds et complets" not in empty
    assert "L’hébergement devra être validé au préalable" not in empty
    assert "Les véhicules utilisés pour les transferts" not in empty
    assert "Autres éléments d’accueil" not in empty
    assert "Restauration : 4 repas" in full
    assert "Les repas devront être chauds et complets" in full
    assert "L’hébergement devra être validé au préalable" in full
    assert "Les véhicules utilisés pour les transferts" in full
    assert "Autres éléments d’accueil : Parking" in full


def test_the_free_concert_and_the_signing_details():
    gig = _gig(is_free=True, signing_place="Lyon", signature_deadline_days=15)

    text = _render(gig)

    assert "Prix des places : Gratuit" in text
    assert "Fait à Lyon" in text
    assert "dans un délai de 15 jours" in text


def test_the_signatory_of_the_contract_replaces_the_representative():
    gig = _gig(tenant_fields={"representative_name": "Julie Martin"})
    contract = Contract.objects.create(
        gig=gig, tenant=gig.tenant, signatory_name="Léa Roux", signatory_role="Trésorière"
    )

    text = _render(gig, contract)

    assert "Représenté par Léa Roux, en qualité de Trésorière." in text


def test_the_company_vat_number_is_shown_only_when_it_is_subject_to_vat():
    taxable = _render(_gig(tenant_fields={"vat_regime": "taxable", "vat_number": "FR99999999999"}))
    franchise = _render(_gig(tenant_fields={"vat_regime": "franchise", "vat_number": "FR1"}))

    assert "N° TVA intracommunautaire : FR99999999999" in taxable
    assert franchise.count("N° TVA intracommunautaire") == 1  # the organiser's only


# --- the money --------------------------------------------------------------------------


def test_the_schedule_splits_the_price_following_the_deposit_percent():
    gig = _gig(
        price=Decimal("1000.00"),
        deposit_percent=Decimal("30"),
        tenant_fields={"vat_regime": "taxable", "vat_rate": Decimal("5.50")},
    )

    schedule = payment_schedule(gig)

    assert schedule == {
        "deposit_ht": Decimal("300.00"),
        "deposit_ttc": Decimal("316.50"),
        "balance_ht": Decimal("700.00"),
        "balance_ttc": Decimal("738.50"),
        "total_ht": Decimal("1000.00"),
        "total_ttc": Decimal("1055.00"),
    }


def test_deposit_and_balance_always_add_up_to_the_total_to_the_cent():
    gig = _gig(
        price=Decimal("333.33"),
        deposit_percent=Decimal("33.33"),
        tenant_fields={"vat_regime": "taxable", "vat_rate": Decimal("5.50")},
    )

    schedule = payment_schedule(gig)

    assert schedule["deposit_ht"] + schedule["balance_ht"] == schedule["total_ht"]
    assert schedule["deposit_ttc"] + schedule["balance_ttc"] == schedule["total_ttc"]


def test_without_vat_the_amounts_with_tax_equal_the_amounts_without():
    gig = _gig(price=Decimal("500.00"), tenant_fields={"vat_regime": "franchise"})

    schedule = payment_schedule(gig)

    assert schedule["total_ttc"] == schedule["total_ht"] == Decimal("500.00")
    assert "TVA non applicable, article 293 B du CGI." in _render(gig)


def test_a_structure_not_subject_to_vat_gets_the_plain_mention():
    text = _render(_gig(tenant_fields={"vat_regime": "not_taxable"}))

    assert "TVA non applicable, article 261-7-1° b du CGI." in text
    assert "article 293 B" not in text


def test_an_unknown_vat_rate_leaves_the_amounts_with_tax_in_dots():
    gig = _gig(price=Decimal("1000.00"), tenant_fields={"vat_regime": "taxable", "vat_rate": None})

    assert payment_schedule(gig)["total_ttc"] is None
    assert "Total 1000,00 € ……" in _render(gig)


def test_the_due_dates_are_printed():
    gig = _gig(
        deposit_due_on=datetime.date(2026, 11, 1), balance_due_on=datetime.date(2026, 12, 15)
    )

    text = _render(gig)

    assert "01/11/2026" in text and "15/12/2026" in text


# --- the PDF and the choice -------------------------------------------------------------


def test_the_pdf_is_produced_with_model_2():
    pdf = render_contract_pdf(_gig(), template=ContractTemplate.MODEL_2)

    assert pdf.startswith(b"%PDF")


def test_a_contract_can_move_from_model_1_to_model_2_while_a_draft():
    gig = _gig()
    generate_contract_pdf(gig)

    contract = generate_contract_pdf(gig, template=ContractTemplate.MODEL_2)

    assert contract.template == ContractTemplate.MODEL_2
    assert contract.versions.count() == 2


def test_the_user_picks_model_2_from_the_contract_page(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant)
    make_contract_ready(gig)

    page = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()
    client.post(reverse("documents:contract-generate", args=[gig.pk]), {"template": "model_2"})

    assert 'value="model_2"' in page
    assert gig.contract.template == ContractTemplate.MODEL_2
