import datetime

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

from .. import checks, services
from ..factories import make_contract_ready
from ..models import Contract, ContractConfirmation, ContractVersion

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _ready_gig(tenant=None, **kwargs):
    gig = GigFactory(tenant=tenant, **kwargs) if tenant else GigFactory(**kwargs)
    make_contract_ready(gig)
    return gig


def _codes(gig, level=None):
    return {a.code for a in checks.check_contract(gig) if level is None or a.level == level}


def _login(client, gig):
    membership = MembershipFactory(tenant=gig.tenant)
    client.force_login(membership.user)


def test_a_complete_date_has_nothing_to_fix():
    gig = _ready_gig()

    assert checks.is_ready(checks.check_contract(gig))


# (what to change on which object, the code that must appear)
BLOCKERS = [
    ("tenant", {"siret": ""}, "PRODUCTEUR_SIRET_MANQUANT"),
    ("tenant", {"siret": "12345678901234"}, "PRODUCTEUR_SIRET_INVALIDE"),
    ("tenant", {"legal_form": ""}, "PRODUCTEUR_FORME_MANQUANTE"),
    ("tenant", {"contact_name": ""}, "PRODUCTEUR_CONTACT_MANQUANT"),
    ("tenant", {"vat_confirmed_on": None}, "PRODUCTEUR_TVA_NON_CONFIRMEE"),
    ("tenant", {"vat_regime": "taxable", "vat_rate": None}, "PRODUCTEUR_TAUX_TVA_MANQUANT"),
    ("tenant", {"vat_regime": "not_taxable"}, "PRODUCTEUR_FONDEMENT_SANS_TVA"),
    ("tenant", {"licence_number": ""}, "PRODUCTEUR_LICENCE_A_VERIFIER"),
    ("tenant", {"licence_categories": ""}, "PRODUCTEUR_LICENCE_INCOMPLETE"),
    (
        "tenant",
        {"licence_valid_until": datetime.date(2000, 1, 1)},
        "PRODUCTEUR_LICENCE_EXPIREE",
    ),
    ("tenant", {"licence_exempt": True}, "PRODUCTEUR_DISPENSE_SANS_MOTIF"),
    ("promoter", {"representative_role": ""}, "ORGANISATEUR_QUALITE_MANQUANTE"),
    ("promoter", {"siret": ""}, "ORGANISATEUR_SIRET_MANQUANT"),
    ("promoter", {"admin_contact_email": ""}, "ORGANISATEUR_EMAIL_MANQUANT"),
    ("promoter", {"legal_form": ""}, "ORGANISATEUR_FORME_MANQUANTE"),
    ("promoter", {"licence_number": ""}, "ORGANISATEUR_LICENCE_A_VERIFIER"),
    (
        "promoter",
        {"representative_name": "Autre Personne"},
        "ORGANISATEUR_HABILITATION_NON_CONFIRMEE",
    ),
    ("gig", {"setting": ""}, "INTERIEUR_PLEIN_AIR_MANQUANT"),
    ("gig", {"setting": "outdoor"}, "PLEIN_AIR_REPLI_MANQUANT"),
    ("gig", {"performance_time": None}, "HEURE_DE_PASSAGE_MANQUANTE"),
    ("gig", {"copies_count": 1}, "EXEMPLAIRES_INSUFFISANTS"),
    ("gig", {"crew_headcount": None}, "EFFECTIF_MANQUANT"),
    ("gig", {"meals_covered_by": ""}, "RESTAURATION_NON_PRECISEE"),
    ("gig", {"meals_covered_by": "organiser"}, "RESTAURATION_INCOMPLETE"),
    ("gig", {"lodging_covered_by": "shared"}, "HEBERGEMENT_INCOMPLETE"),
    ("gig", {"transport_covered_by": ""}, "TRANSPORT_NON_PRECISE"),
    ("gig", {"price": 0}, "PRIX_MANQUANT"),
    ("gig", {"deposit_required": None}, "ACOMPTE_NON_PRECISE"),
    ("gig", {"deposit_percent": 20}, "ACOMPTE_CONTRADICTOIRE"),
    ("gig", {"deposit_required": True, "deposit_percent": 0}, "ACOMPTE_MONTANT_INVALIDE"),
    (
        "gig",
        {"deposit_required": True, "deposit_percent": 30, "deposit_term": "specific"},
        "ACOMPTE_ECHEANCE_MANQUANTE",
    ),
    ("gig", {"balance_due_on": None}, "SOLDE_ECHEANCE_MANQUANTE"),
    ("gig", {"extra_fees_description": "Piano"}, "FRAIS_SANS_MONTANT"),
    ("gig", {"billing_notes": ""}, "FACTURATION_NON_PRECISEE"),
]


@pytest.mark.parametrize(("where", "change", "code"), BLOCKERS)
def test_a_missing_or_wrong_fact_blocks(where, change, code):
    gig = _ready_gig()
    target = {"tenant": gig.tenant, "promoter": gig.promoter, "gig": gig}[where]
    for name, value in change.items():
        setattr(target, name, value)
    target.save()
    gig.refresh_from_db()

    anomalies = checks.check_contract(gig)

    assert code in {a.code for a in anomalies if a.level == checks.BLOCKING}
    assert not checks.is_ready(anomalies)


def test_a_private_promoter_needs_no_siret_legal_form_or_licence():
    gig = _ready_gig()
    gig.promoter.is_private = True
    gig.promoter.siret = gig.promoter.legal_form = gig.promoter.licence_number = ""
    gig.promoter.save()
    gig.refresh_from_db()

    assert checks.is_ready(checks.check_contract(gig))


def test_unknown_details_only_warn_and_never_block():
    gig = _ready_gig()
    gig.get_in_time = gig.soundcheck_time = None
    gig.onsite_contact_name = ""
    gig.save()
    gig.venue.capacity = None
    gig.venue.save()
    gig.refresh_from_db()

    anomalies = checks.check_contract(gig)

    assert {"ARRIVEE_MANQUANTE", "BALANCES_MANQUANTES", "JAUGE_MANQUANTE"} <= {
        a.code for a in anomalies if a.level == checks.WARNING
    }
    assert checks.is_ready(anomalies)


def test_a_time_after_the_start_is_only_a_warning():
    gig = _ready_gig()
    gig.get_in_time = datetime.time(23, 0)
    gig.save()
    gig.refresh_from_db()

    assert "HORAIRES_A_VERIFIER" in _codes(gig, checks.WARNING)
    assert checks.is_ready(checks.check_contract(gig))


def test_a_past_date_asks_for_a_confirmation_that_a_change_of_date_cancels():
    gig = _ready_gig(date=datetime.date.today() - datetime.timedelta(days=3))
    pending = checks.PAST_DATE in _codes(gig, checks.CONFIRMATION)
    assert pending is False  # make_contract_ready already confirmed it
    assert ContractConfirmation.objects.filter(gig=gig, code=checks.PAST_DATE).exists()

    gig.date -= datetime.timedelta(days=1)
    gig.save()
    assert checks.PAST_DATE in _codes(gig, checks.CONFIRMATION)


def test_the_producer_signatory_is_confirmed_until_they_change():
    gig = _ready_gig()
    assert checks.is_ready(checks.check_contract(gig))

    contract = gig.contract
    contract.signatory_role = "Présidente"
    contract.save()
    gig.refresh_from_db()

    assert checks.PRODUCER_SIGNATORY in _codes(gig, checks.CONFIRMATION)


def test_a_missing_producer_signatory_blocks():
    gig = _ready_gig()
    Contract.objects.filter(gig=gig).update(signatory_name="")
    gig.refresh_from_db()

    assert "PRODUCTEUR_SIGNATAIRE_MANQUANT" in _codes(gig, checks.BLOCKING)


def test_confirm_only_records_what_the_checks_ask_for(client):
    gig = _ready_gig(date=datetime.date.today() - datetime.timedelta(days=3))
    ContractConfirmation.objects.all().delete()
    _login(client, gig)
    url = reverse("documents:contract-confirm", args=[gig.pk])

    client.post(url, {"code": "NOT_A_CODE"})
    assert not ContractConfirmation.objects.exists()

    client.post(url, {"code": checks.PAST_DATE})
    confirmation = ContractConfirmation.objects.get()
    assert confirmation.fingerprint == gig.date.isoformat()
    assert confirmation.confirmed_by is not None


def test_another_structure_cannot_confirm_or_read_the_checks_of_my_date(client):
    gig = _ready_gig(date=datetime.date.today() - datetime.timedelta(days=3))
    ContractConfirmation.objects.all().delete()
    other = MembershipFactory()
    client.force_login(other.user)

    confirm = client.post(
        reverse("documents:contract-confirm", args=[gig.pk]), {"code": checks.PAST_DATE}
    )
    history = client.get(reverse("documents:contract-history", args=[gig.pk]))

    assert confirm.status_code == 404
    assert history.status_code == 404
    assert not ContractConfirmation.objects.exists()


def test_generating_is_refused_while_something_blocks_and_nothing_is_stored(client):
    gig = GigFactory()
    _login(client, gig)

    response = client.post(reverse("documents:contract-generate", args=[gig.pk]))

    assert response.status_code == 302
    assert not ContractVersion.objects.exists()
    page = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()
    assert "Génération impossible" in page


def test_generating_works_once_everything_is_filled_and_confirmed(client):
    gig = _ready_gig()
    _login(client, gig)

    client.post(reverse("documents:contract-generate", args=[gig.pk]))

    assert ContractVersion.objects.filter(contract__gig=gig).count() == 1


def test_the_preview_is_always_possible_and_says_it_is_a_draft(client):
    gig = GigFactory()
    gig.refresh_from_db()  # the factory keeps the price as typed (a string)
    _login(client, gig)

    response = client.get(reverse("documents:contract-preview", args=[gig.pk]))
    anomalies = checks.to_fix(checks.check_contract(gig))
    html = render_to_string(
        "documents/contracts/contract.html",
        services.build_contract_context(gig, None, draft_anomalies=anomalies),
    )
    ready = _ready_gig()
    ready_html = render_to_string(
        "documents/contracts/contract.html", services.build_contract_context(ready, ready.contract)
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert "BROUILLON — INFORMATIONS INCOMPLÈTES" in html
    assert "BROUILLON" not in ready_html


def test_a_version_becomes_to_update_when_the_data_changes_unless_it_was_sent(client):
    gig = _ready_gig()
    _login(client, gig)
    client.post(reverse("documents:contract-generate", args=[gig.pk]))
    history = reverse("documents:contract-history", args=[gig.pk])
    assert "À actualiser" not in client.get(history).content.decode()

    gig.refresh_from_db()
    gig.billing_notes = "Autre mention"
    gig.save()
    assert "À actualiser" in client.get(history).content.decode()

    services.mark_contract_sent(gig)
    assert "À actualiser" not in client.get(history).content.decode()


def test_old_versions_without_a_fingerprint_are_never_marked(client):
    gig = _ready_gig()
    _login(client, gig)
    client.post(reverse("documents:contract-generate", args=[gig.pk]))
    ContractVersion.objects.update(facts_fingerprint="")
    gig.billing_notes = "Autre mention"
    gig.save()

    page = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()

    assert "À actualiser" not in page


def test_the_completion_page_lists_what_is_missing_without_confirm_buttons(client):
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    _login(client, gig)

    page = client.get(reverse("documents:contract-complete", args=[gig.pk])).content.decode()

    assert "Génération impossible" in page
    assert "Informations de la structure" in page
    assert "contrat/confirmer/" not in page
