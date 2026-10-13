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

TEMPLATE = "documents/contracts/model_3.html"


def _render(gig, contract=None):
    gig.refresh_from_db()
    html = render_to_string(TEMPLATE, build_contract_context(gig, contract))
    html = html.split("</style>")[1]  # the CSS is not part of the contract text
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", html)).split())


def _gig(**overrides):
    tenant = TenantFactory(**overrides.pop("tenant_fields", {}))
    return GigFactory(tenant=tenant, **overrides)


def test_the_parties_the_show_and_the_reference_come_from_our_data():
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
    promoter = PromoterFactory(tenant=tenant, name="Mairie de Sète", code_ape="8411Z")
    gig = GigFactory(
        tenant=tenant, promoter=promoter, event_name="Fête de la musique", performances_count=2
    )
    contract = Contract.objects.create(gig=gig, tenant=tenant, reference="C-2026-007")

    text = _render(gig, contract)

    assert "Référence du contrat : C-2026-007" in text
    assert "Raison sociale : Compagnie du Soleil" in text
    assert "Code APE : 9001Z" in text
    assert "Raison sociale : Mairie de Sète" in text
    assert "Code APE : 8411Z" in text
    assert f"Nom du spectacle : {gig.show.title}" in text
    assert "Événement : Fête de la musique" in text
    assert "Nombre de représentations : 2" in text
    assert "pour 2 représentation(s) du spectacle" in text
    assert "Le Producteur s’engage à donner 2 représentation(s)" in text
    assert "IBAN : FR7630006000011234567890189" in text
    assert "BIC : AGRIFRPP" in text
    assert "tribunaux de Montpellier" in text


def test_the_legal_clauses_are_kept_word_for_word():
    text = _render(_gig())

    for clause in [
        "Le montant est ferme et définitivement établi. Le Producteur n’aura pas à justifier a "
        "posteriori de son détail.",
        "Pour une entité publique, l’Organisateur transmettra au Producteur, dès la signature du "
        "contrat, le bon de commande et le numéro d’engagement nécessaires au dépôt des factures "
        "sur Chorus Pro.",
        "Chaque Partie demeure une entité juridique indépendante",
        "Défaillance accidentelle de la fourniture d’électricité par les services publics.",
        "Le Producteur disposera de …… minutes pour installer son matériel",
    ]:
        assert clause in text
    for number in range(1, 13):
        assert f"Article {number} —" in text


def test_the_two_drafting_traces_of_the_source_are_removed():
    text = _render(_gig())

    assert "contrat source" not in text
    assert (
        "La pluie et le mauvais temps ne sont pas considérés comme des cas de force majeure."
        in text
    )
    assert "La liste ci-dessous reprend les événements envisagés et ne remplace pas" in text


def test_every_empty_value_prints_as_dots_and_nothing_breaks():
    gig = _gig(tenant_fields={"vat_regime": "taxable", "vat_rate": None})

    text = _render(gig)

    assert "Référence du contrat : ……" in text
    assert "Configuration : ……" in text
    assert "Repas : ……" in text
    assert "Acompte : …… à régler le ……" in text
    assert "TVA au taux de …… %" in text
    assert "joué moins de …… fois" in text
    assert "Le règlement sera effectué par …… sur présentation" in text
    assert "Rider d’accueil : ……" in text
    assert "None" not in text


def test_hosting_times_payment_and_annexes_are_filled_in_when_known():
    gig = _gig(
        price=Decimal("1000.00"),
        deposit_percent=Decimal("30"),
        meals="4 repas",
        lodging="2 chambres",
        other_hospitality="Parking",
        payment_method="transfer",
        deposit_due_on=datetime.date(2026, 11, 1),
        balance_due_on=datetime.date(2026, 12, 15),
        get_in_time=datetime.time(15, 30),
        soundcheck_time=datetime.time(17, 0),
        performance_time=datetime.time(21, 15),
        invitations_count=4,
        tenant_fields={"vat_regime": "taxable", "vat_rate": Decimal("5.50")},
    )
    gig.show.tech_sheet_text = "Fiche"
    gig.show.save()

    text = _render(gig)

    assert "Repas : 4 repas" in text and "Hébergement : 2 chambres" in text
    assert "Autres éléments d’accueil : Parking" in text
    assert "Get in : 15h30 - Balances : 17h00 - Set : 21h15" in text
    assert "Le règlement sera effectué par virement sur présentation" in text
    assert "Acompte : 316,50 € à régler le 01/11/2026" in text
    assert "Solde : 738,50 € à régler le 15/12/2026" in text
    assert "TVA au taux de 5,50 % 55,00 €" in text
    assert "Total TTC 1055,00 €" in text
    assert "Invitations exonérées : 4" in text
    assert "Fiche technique : jointe au présent contrat" in text


def test_without_vat_the_total_equals_the_price_and_the_mention_is_printed():
    gig = _gig(price=Decimal("500.00"), tenant_fields={"vat_regime": "franchise"})

    text = _render(gig)

    assert "TVA non applicable, article 293 B du CGI." in text
    assert "Total TTC 500,00 €" in text


def test_free_concert_and_signature_details():
    gig = _gig(is_free=True, signing_place="Lyon", copies_count=3)

    text = _render(gig)

    assert "Tarif : Concert gratuit" in text
    assert "Fait à Lyon" in text and "en 3 exemplaires originaux" in text


def test_the_signatory_of_the_contract_replaces_the_representative():
    gig = _gig(tenant_fields={"representative_name": "Julie Martin"})
    contract = Contract.objects.create(
        gig=gig, tenant=gig.tenant, signatory_name="Léa Roux", signatory_role="Trésorière"
    )

    assert "Nom et qualité du signataire : Léa Roux — Trésorière" in _render(gig, contract)


def test_the_pdf_is_produced_and_the_contract_can_use_model_3():
    gig = _gig()

    assert render_contract_pdf(gig, template=ContractTemplate.MODEL_3).startswith(b"%PDF")
    contract = generate_contract_pdf(gig, template=ContractTemplate.MODEL_3)
    assert contract.template == ContractTemplate.MODEL_3
    assert contract.latest_version.template == ContractTemplate.MODEL_3
