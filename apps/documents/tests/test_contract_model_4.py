import datetime
import html as html_lib
import re
from decimal import Decimal

import pytest
from django.template.loader import render_to_string

from apps.addressbook.factories import PromoterFactory
from apps.gigs.factories import GigFactory
from apps.tenants.factories import TenantFactory

from ..models import Contract, ContractTemplate
from ..services import build_contract_context, generate_contract_pdf, render_contract_pdf

pytestmark = pytest.mark.django_db

TEMPLATE = "documents/contracts/model_4.html"


def _render(gig, contract=None):
    gig.refresh_from_db()
    html = render_to_string(TEMPLATE, build_contract_context(gig, contract))
    html = html.split("</style>")[1]  # the CSS is not part of the contract text
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", html)).split())


def _gig(**overrides):
    tenant = TenantFactory(**overrides.pop("tenant_fields", {}))
    return GigFactory(tenant=tenant, **overrides)


def test_the_parties_the_show_and_the_siren_come_from_our_data():
    tenant = TenantFactory(
        name="Compagnie du Soleil",
        siret="12345678900012",
        licence_number="L-1",
        phone="04 67 00 00 00",
        jurisdiction_city="Montpellier",
    )
    promoter = PromoterFactory(tenant=tenant, name="Mairie de Sète", siret="98765432100011")
    gig = GigFactory(tenant=tenant, promoter=promoter, performances_count=2)

    text = _render(gig)

    assert "Raison sociale de l’entreprise : Compagnie du Soleil" in text
    assert "Numéro SIREN : 123456789 " in text
    assert "Numéro SIREN : 987654321 " in text
    assert "Licence d’entrepreneur de spectacles n° et catégorie : L-1" in text
    assert "Raison sociale de l’entreprise : Mairie de Sète" in text
    assert f"Titre du spectacle : {gig.show.title}" in text
    assert "donner, dans les conditions définies ci-après" in text
    assert "2 représentation(s), sur les lieux précités" in text
    assert "tribunaux compétents de la ville de Montpellier" in text


def test_the_legal_clauses_are_kept_word_for_word():
    text = _render(_gig())

    for clause in [
        "a été représenté moins de 141 fois au sens défini par l’article 89 ter annexe III du "
        "Code général des impôts.",
        "Les droits voisins sont à la charge du Producteur.",
        "Il est rappelé que la force majeure doit répondre aux 3 critères suivants : "
        "imprévisibilité, extériorité et irrésistibilité.",
        "Chaque page du présent contrat doit être paraphée par les deux parties.",
        "Les annexes sont paraphées. Elles font partie intégrante du contrat",
    ]:
        assert clause in text
    for number in range(1, 13):
        assert f"Article {number} " in text
    for number in range(1, 5):
        assert f"Annexe n°{number}" in text


def test_the_editor_notes_of_the_source_are_not_printed():
    text = _render(_gig())

    for note in [
        "Ce contrat est un modèle qu'il convient d'adapter",
        "Attention",
        "Il est possible de",
        "Il est important de préciser",
        "Il appartient aux parties",
        "Possibilité de lister",
        "Il n’existe pas de fiche technique type",
        "Cette annexe ne prévoit que",
    ]:
        assert note not in text


def test_every_empty_value_prints_as_dots_and_nothing_breaks():
    gig = _gig(tenant_fields={"vat_regime": "taxable", "vat_rate": None})

    text = _render(gig)

    assert "Titre de l’ouvrage : ……" in text
    assert "Auteur : ……" in text
    assert "Metteur en scène ou chorégraphe : ……" in text
    assert "sera effectué au plus tard le …… par chèque" in text
    assert "dans les …… jours au Producteur" in text
    assert "Autres dispositions : ……" in text
    assert "(TVA à …… %)" in text
    assert "None" not in text


def test_the_price_follows_the_vat_regime():
    taxable = _render(
        _gig(
            price=Decimal("1000.00"),
            tenant_fields={"vat_regime": "taxable", "vat_rate": Decimal("5.50")},
        )
    )
    franchise = _render(_gig(price=Decimal("500.00"), tenant_fields={"vat_regime": "franchise"}))
    not_taxable = _render(
        _gig(price=Decimal("500.00"), tenant_fields={"vat_regime": "not_taxable"})
    )

    assert "1000,00 € HT + 55,00 € (TVA à 5,50 %) = 1055,00 € TTC" in taxable
    assert (
        "500,00 € HT = 500,00 € TTC (TVA non applicable conformément à l'article 293 B" in franchise
    )
    assert "500,00 € HT = 500,00 € TTC (TVA non applicable)" in not_taxable
    assert "article 293 B" not in not_taxable


def test_the_payment_mode_chosen_for_the_gig_replaces_the_alternatives():
    cheque = _render(_gig(payment_method="cheque"))
    transfer = _render(
        _gig(
            payment_method="transfer",
            tenant_fields={"iban": "FR7630006000011234567890189", "bic": "AGRIFRPP"},
        )
    )
    undecided = _render(_gig())

    assert "OU par virement" not in cheque and "Rayer les mentions inutiles" not in cheque
    assert "par chèque établi à l’ordre de" in cheque
    assert "par virement au compte IBAN FR7630006000011234567890189 (BIC AGRIFRPP)" in transfer
    assert "par chèque" not in transfer.split("Article 9")[1].split("Article 10")[0]
    assert "OU par virement" in undecided and "Rayer les mentions inutiles" in undecided


def test_the_deposit_and_dates_are_printed():
    gig = _gig(
        price=Decimal("1000.00"),
        deposit_percent=Decimal("30"),
        balance_due_on=datetime.date(2026, 12, 15),
        signature_deadline_days=10,
        conditions="Loge chauffée.",
        invitations_count=4,
        is_free=False,
        ticket_price=Decimal("12.00"),
        performance_time=datetime.time(21, 15),
        signing_place="Lyon",
        copies_count=3,
        tenant_fields={"vat_regime": "franchise"},
    )

    text = _render(gig)

    assert "soit la somme de 300,00 €" in text
    assert "sera effectué au plus tard le 15/12/2026" in text
    assert "dans les 10 jours au Producteur" in text
    assert "Autres dispositions : Loge chauffée." in text
    assert "Elles sont au nombre de 4 par représentation" in text
    assert "Le prix des places est fixé à 12,00 €" in text
    assert f"le {gig.date:%d/%m/%Y}, à 21h15" in text
    assert "Fait à Lyon" in text and "en 3 exemplaires" in text


def test_the_technical_sheet_text_of_the_show_goes_into_annex_2():
    gig = _gig()
    gig.show.tech_sheet_text = "Deux micros chant, une DI guitare."
    gig.show.performers = "Léa et Marc"
    gig.show.save()

    text = _render(gig)

    assert "Deux micros chant, une DI guitare." in text
    assert "Nom des interprètes principaux : Léa et Marc" in text
    assert "Distribution artistique : Léa et Marc" in text


def test_the_annexes_start_on_a_new_page():
    gig = _gig()
    html = render_to_string(TEMPLATE, build_contract_context(gig))

    assert html.count('class="annex"') == 4
    assert "page-break-before: always" in html


def test_the_signatory_of_the_contract_replaces_the_representative():
    gig = _gig(tenant_fields={"representative_name": "Julie Martin"})
    contract = Contract.objects.create(
        gig=gig, tenant=gig.tenant, signatory_name="Léa Roux", signatory_role="Trésorière"
    )

    assert "Léa Roux, Trésorière" in _render(gig, contract)


def test_the_pdf_is_produced_and_the_contract_can_use_model_4():
    gig = _gig()

    assert render_contract_pdf(gig, template=ContractTemplate.MODEL_4).startswith(b"%PDF")
    contract = generate_contract_pdf(gig, template=ContractTemplate.MODEL_4)
    assert contract.template == ContractTemplate.MODEL_4
