"""The 20 scenarios of the minimal acceptance test (spec 03, §20), one test each.

Scenarios 9, 12, 14 and 19 depend on the e-mail and e-signature phases (D9) or on documentation:
see docs/metier/points-pour-le-juriste-contrat.md. Scenario 8 (missing annex) is also covered by
test_contract_annexes.py.
"""

import datetime
import html as html_lib
import re
from decimal import Decimal

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.gigs.hospitality import compose
from apps.gigs.models import Gig
from apps.tenants.models import Tenant

from .. import checks, services
from ..factories import make_contract_ready
from ..models import Contract, ContractVariant

pytestmark = pytest.mark.django_db


def _ready(**fields):
    """A date that passes every check, then the fields of the scenario on top of it."""
    related = {k: v for k, v in fields.items() if "__" in k}
    own = {k: v for k, v in fields.items() if "__" not in k}
    gig = GigFactory(**related)
    make_contract_ready(gig)
    Gig.objects.filter(pk=gig.pk).update(**own)
    return Gig.objects.get(pk=gig.pk)


def _tenant(gig, **fields):
    Tenant.objects.filter(pk=gig.tenant_id).update(**fields)
    return Gig.objects.get(pk=gig.pk)


def _text(gig, contract=None):
    html = render_to_string(
        "documents/contracts/contract.html", services.build_contract_context(gig, contract)
    )
    return " ".join(re.sub(r"<[^>]+>", " ", html_lib.unescape(html)).split())


def _codes(gig, level=None):
    return {a.code for a in checks.check_contract(gig) if level in (None, a.level)}


def test_scenario_01_a_producer_charging_vat_gets_the_vat_variant():
    gig = _tenant(_ready(), vat_regime="taxable", vat_rate="20.00")

    text = _text(gig)

    assert services.contract_variant(gig.tenant) == ContractVariant.WITH_VAT
    assert "TVA — taux 20 %" in text


def test_scenario_02_a_franchise_producer_gets_the_variant_without_vat_and_no_zero_rate():
    gig = _tenant(_ready(), vat_regime="franchise")

    text = _text(gig)

    assert services.contract_variant(gig.tenant) == ContractVariant.WITHOUT_VAT
    assert "293 B" in text and "0 %" not in text


def test_scenario_03_another_exemption_quotes_its_own_basis_and_never_293_b():
    gig = _tenant(_ready(), vat_regime="not_taxable", vat_exemption_note="Article 261 du CGI.")

    text = _text(gig)

    assert "Article 261 du CGI." in text and "293 B" not in text


def test_scenario_04_the_vat_of_the_promoter_never_picks_the_variant():
    taxable = _tenant(_ready(promoter__vat_number="FR1234"), vat_regime="taxable")
    franchise = _tenant(_ready(promoter__vat_number="FR1234"), vat_regime="franchise")

    assert services.contract_variant(taxable.tenant) == ContractVariant.WITH_VAT
    assert services.contract_variant(franchise.tenant) == ContractVariant.WITHOUT_VAT


def test_scenario_05_a_signed_contract_does_not_change_when_the_parameters_do():
    gig = _tenant(_ready(), vat_regime="taxable", vat_rate="20.00")
    contract = services.generate_contract_pdf(gig)
    frozen = contract.latest_version.pdf_file.read()
    Contract.objects.filter(pk=contract.pk).update(status=Contract.Status.SIGNED)

    gig = _tenant(gig, vat_regime="franchise", name="Autre nom")
    contract = services.generate_contract_pdf(gig)

    assert contract.versions.count() == 1
    assert contract.latest_version.pdf_file.read() == frozen
    assert contract.latest_version.fiscal_snapshot["regime"] == "taxable"


def test_scenario_06_a_free_concert_keeps_the_cnm_clause_without_any_exemption():
    text = _text(_ready(is_free=True))

    assert "taxe sur les spectacles" in text
    assert "La gratuité de l’accès du public ne dispense pas, à elle seule, de cette taxe" in text


def test_scenario_07_fed_and_housed_people_are_confirmed_when_fewer_than_the_crew():
    gig = _ready(
        crew_headcount=4,
        meals_covered_by="organiser",
        meals_people=3,
        meals_count=3,
        lodging_covered_by="organiser",
        lodging_people=3,
        lodging_nights=1,
    )

    pending = {a.code: a for a in checks.check_contract(gig) if a.level == checks.CONFIRMATION}
    assert {"RESTAURATION_EFFECTIF_INFERIEUR", "HEBERGEMENT_EFFECTIF_INFERIEUR"} <= set(pending)

    for code in ("RESTAURATION_EFFECTIF_INFERIEUR", "HEBERGEMENT_EFFECTIF_INFERIEUR"):
        assert checks.confirm(gig, code, None)
    assert checks.is_ready(checks.check_contract(gig))
    assert compose("organiser", 3, ("repas", "repas"), "", people=3) == (
        "À la charge de l'Organisateur : 3 personnes, 3 repas"
    )

    GigFactory._meta.model.objects.filter(pk=gig.pk).update(meals_people=2)
    assert "RESTAURATION_EFFECTIF_INFERIEUR" in _codes(Gig.objects.get(pk=gig.pk))


def test_scenario_07_more_people_than_the_crew_must_be_corrected():
    gig = _ready(crew_headcount=4, meals_covered_by="organiser", meals_people=6, meals_count=6)

    assert "RESTAURATION_EFFECTIF_SUPERIEUR" in _codes(gig, checks.BLOCKING)


def test_scenario_07_a_covered_meal_without_people_is_incomplete():
    gig = _ready(meals_covered_by="organiser", meals_count=3, meals_people=None)

    assert "RESTAURATION_INCOMPLETE" in _codes(gig, checks.BLOCKING)


def test_scenario_08_a_missing_annex_blocks_the_final_generation_but_not_the_preview():
    gig = _ready()
    gig.show.tech_sheet_text = ""
    gig.show.save()

    assert "ANNEXE_FICHE_TECHNIQUE_MANQUANTE" in _codes(gig, checks.BLOCKING)
    pdf, annexes = services.render_contract_pdf(gig)
    assert pdf.startswith(b"%PDF") and annexes["tech_sheet"]["pages"] == 1


def test_scenario_10_without_a_sacem_number_a_replacement_text_is_printed():
    gig = _ready(show__sacem_number="")

    text = _text(gig)

    assert "Aucun numéro de programme type n’a été déclaré à ce jour" in text
    assert "_codes" not in text and not {c for c in _codes(gig) if "SACEM" in c}


def test_scenario_11_an_open_air_date_needs_its_fallback_procedure_and_referents():
    gig = _ready(setting="outdoor", outdoor_fallback="", outdoor_procedure="", outdoor_referents="")

    assert {
        "PLEIN_AIR_REPLI_MANQUANT",
        "PLEIN_AIR_PROCEDURE_MANQUANTE",
        "PLEIN_AIR_REFERENTS_MANQUANTS",
    } <= _codes(gig, checks.BLOCKING)


def test_scenario_11_no_fallback_accepted_is_stated_without_an_implicit_price_guarantee():
    gig = _ready(
        setting="outdoor",
        outdoor_fallback="none_accepted",
        outdoor_procedure="Décision commune",
        outdoor_referents="Léa, Marc",
        outdoor_financial_terms="",
    )

    text = _text(gig)

    assert checks.is_ready(checks.check_contract(gig))
    assert "Pas de repli, accepté par les deux parties" in text
    assert "totalité du cachet" not in text


def test_scenario_13_a_missing_siret_blocks_with_a_link_to_the_structure():
    gig = _tenant(_ready(), siret="")

    missing = [a for a in checks.check_contract(gig) if a.code == "PRODUCTEUR_SIRET_MANQUANT"]

    assert missing and missing[0].level == checks.BLOCKING
    assert missing[0].url == reverse("tenants:settings")


def test_scenario_15_the_contact_and_the_signatory_are_kept_apart():
    gig = _ready()
    Tenant.objects.filter(pk=gig.tenant_id).update(contact_name="Sam Contact")
    gig = Gig.objects.get(pk=gig.pk)

    version = services.generate_contract_pdf(gig).latest_version
    producer = version.parties_snapshot["producer"]

    assert producer["contact_name"] == "Sam Contact"
    assert producer["signatory_name"] == "Léa Roux"
    text = _text(gig, gig.contract)
    assert "Contact : Sam Contact" in text and "Représenté par Léa Roux" in text


def test_scenario_16_an_incomplete_schedule_blocks():
    gig = _ready(
        deposit_required=True, deposit_percent=0, balance_term="specific", balance_due_on=None
    )

    assert {"ACOMPTE_MONTANT_INVALIDE", "SOLDE_ECHEANCE_MANQUANTE"} <= _codes(gig, checks.BLOCKING)


def test_scenario_16_the_deposit_and_the_balance_always_add_up_to_the_total_to_the_cent():
    gig = _tenant(
        _ready(price="333.33", deposit_required=True, deposit_percent=30),
        vat_regime="taxable",
        vat_rate="20.00",
    )
    gig = Gig.objects.get(pk=gig.pk)

    schedule = services.payment_schedule(gig)

    assert schedule["deposit_ht"] + schedule["balance_ht"] == Decimal("333.33")
    assert schedule["deposit_ttc"] + schedule["balance_ttc"] == schedule["total_ttc"]


def test_amounts_in_the_schedule_use_the_french_decimal_comma():
    gig = _tenant(
        _ready(price="1500.00", deposit_required=True, deposit_percent=30),
        vat_regime="taxable",
        vat_rate="20.00",
    )

    assert "Acompte de 540,00 € TTC" in services.build_contract_context(gig)["payment_text"]


def test_the_open_air_clause_labels_each_piece_of_information():
    gig = _ready(
        setting="outdoor",
        outdoor_fallback="provided",
        outdoor_fallback_details="Salle des fêtes",
        outdoor_procedure="Décision commune",
        outdoor_referents="Léa, Marc",
    )

    clause = services.build_contract_context(gig)["outdoor_clause"]

    assert "Référents des deux parties : Léa, Marc." in clause
    assert "Modalités du repli : Salle des fêtes." in clause


def test_scenario_17_the_generation_date_is_never_presented_as_the_signature_date():
    gig = _ready(signing_place="Lyon")

    text = _text(gig)

    assert re.search(r"Fait à Lyon, le …+\.", text)
    assert not re.search(r"Fait à Lyon, le \d", text)


def test_scenario_18_a_show_running_past_midnight_gets_a_warning_and_no_blocking():
    gig = _ready(
        get_in_time=datetime.time(22, 0),
        soundcheck_time=datetime.time(22, 30),
        performance_time=datetime.time(0, 30),
    )

    anomalies = checks.check_contract(gig)

    assert "HORAIRES_A_VERIFIER" in {a.code for a in anomalies if a.level == checks.WARNING}
    assert checks.is_ready(anomalies)


def test_scenario_20_changing_a_confirmed_fact_renews_the_confirmation_and_outdates_the_version():
    gig = _ready(date=datetime.date(2020, 1, 1))
    assert checks.confirm(gig, checks.PAST_DATE, None)
    assert checks.PAST_DATE not in _codes(gig)
    before = checks.facts_fingerprint(gig, gig.contract)

    Gig.objects.filter(pk=gig.pk).update(date=datetime.date(2020, 2, 2))
    gig = Gig.objects.get(pk=gig.pk)

    assert checks.PAST_DATE in _codes(gig)
    assert checks.facts_fingerprint(gig, gig.contract) != before


# --- sending a version without its annexes (decision of 2026-11-17) ---


def test_a_version_without_annexes_cannot_be_marked_sent_nor_shared():
    gig = _ready()
    contract = services.generate_contract_pdf(gig)
    version = contract.latest_version
    version.annexes_snapshot = []
    version.save()

    with pytest.raises(services.ContractSigningError):
        services.mark_contract_sent(gig)
    with pytest.raises(services.ContractSigningError):
        services.create_share_link(contract, None)


def test_a_version_with_its_annexes_can_be_marked_sent_and_shared():
    gig = _ready()
    contract = services.generate_contract_pdf(gig)

    services.mark_contract_sent(gig)
    link = services.create_share_link(contract, None)

    assert link.version_id == contract.latest_version.pk
