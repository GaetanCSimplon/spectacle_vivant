"""What the contract of a date still lacks (spec 03, §10 to §19).

Pure reading of the facts: nothing is changed here. A BLOCKING anomaly stops the final
generation, a CONFIRMATION one needs an explicit, recorded confirmation (it falls again when the
confirmed data changes), a WARNING only reports. The preview and saving are never refused.
"""

import datetime
import hashlib
import json
from dataclasses import dataclass

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.gigs.hospitality import CoveredBy
from apps.gigs.models import Gig
from apps.gigs.payment_terms import BalanceTerm, DepositTerm
from apps.tenants.models import Tenant
from apps.tenants.validators import validate_siret

from .annexes import has_tech_sheet
from .models import Contract, ContractConfirmation

BLOCKING = "BLOCAGE"
CONFIRMATION = "CONFIRMATION_REQUISE"
WARNING = "AVERTISSEMENT"

# Confirmation codes.
PAST_DATE = "DATE_PASSEE"
PRODUCER_SIGNATORY = "SIGNATAIRE_PRODUCTEUR"

SCREENS = {
    "structure": _("Informations de la structure"),
    "promoter": _("Organisateur"),
    "contract": _("Contrat"),
    "show": _("Spectacle"),
}


@dataclass(frozen=True)
class Anomaly:
    code: str
    level: str
    message: str
    screen: str
    url: str
    fingerprint: str = ""  # only for a confirmation: what the user is confirming

    @property
    def screen_label(self):
        return SCREENS[self.screen]


def check_contract(gig, contract=None, today=None):
    today = today or datetime.date.today()
    if contract is None:
        try:
            contract = gig.contract
        except Contract.DoesNotExist:
            contract = None
    found = [
        *_producer(gig.tenant, gig),
        *_promoter(gig.promoter, gig),
        *_performance(gig, today),
        *_tour_and_price(gig),
        *_annexes(gig),
        *_confirmations(gig, contract, today),
    ]
    # `gig.contract` and `gig.confirmations` can be loaded for a whole list beforehand
    # (select_related / prefetch_related), so a list of dates costs a constant number of queries.
    confirmed = {c.code: c.fingerprint for c in gig.confirmations.all()}
    return [
        a for a in found if not (a.level == CONFIRMATION and confirmed.get(a.code) == a.fingerprint)
    ]


def is_ready(anomalies):
    return not any(a.level in (BLOCKING, CONFIRMATION) for a in anomalies)


def to_fix(anomalies):
    return [a for a in anomalies if a.level in (BLOCKING, CONFIRMATION)]


def grouped(anomalies):
    """[(screen label, [anomalies])] in the order of the screens."""
    return [
        (label, [a for a in anomalies if a.screen == key])
        for key, label in SCREENS.items()
        if any(a.screen == key for a in anomalies)
    ]


def confirm(gig, code, user):
    """Record the confirmation `code` as the data stands now. False if nothing asks for it."""
    for anomaly in check_contract(gig):
        if anomaly.code == code and anomaly.level == CONFIRMATION:
            ContractConfirmation.objects.update_or_create(
                gig=gig,
                code=code,
                defaults={
                    "tenant": gig.tenant,
                    "fingerprint": anomaly.fingerprint,
                    "confirmed_by": user,
                },
            )
            return True
    return False


def facts_fingerprint(gig, contract=None):
    """A hash of everything the contract is written from: it changes when any of it changes."""
    skipped = {"id", "tenant", "created_at", "updated_at", "status"}
    facts = []
    for obj in (gig.tenant, gig.promoter, gig.venue, gig.show, gig, contract):
        if obj is None:
            continue
        facts.append(
            {
                f.attname: str(getattr(obj, f.attname))
                for f in obj._meta.concrete_fields
                if f.name not in skipped and f.name not in {"pdf_file", "signed_pdf"}
            }
        )
    return hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()


# --- the checks ---------------------------------------------------------------------------


def _block(code, message, screen, url):
    return Anomaly(code, BLOCKING, str(message), screen, url)


def _warn(code, message, screen, url):
    return Anomaly(code, WARNING, str(message), screen, url)


def _blank(value):
    return not str(value or "").strip()


def _producer(tenant, gig):
    url = reverse("tenants:settings")
    out = []

    def missing(code, text, value):
        if _blank(value):
            out.append(
                _block(
                    code, _("%(what)s de la structure manque.") % {"what": text}, "structure", url
                )
            )

    missing("PRODUCTEUR_NOM_MANQUANT", _("Le nom"), tenant.name)
    missing("PRODUCTEUR_FORME_MANQUANTE", _("La forme juridique"), tenant.legal_form)
    missing("PRODUCTEUR_ADRESSE_MANQUANTE", _("L'adresse"), tenant.address)
    missing("PRODUCTEUR_CODE_POSTAL_MANQUANT", _("Le code postal"), tenant.postal_code)
    missing("PRODUCTEUR_VILLE_MANQUANTE", _("La ville"), tenant.city)
    missing(
        "PRODUCTEUR_CONTACT_MANQUANT", _("Le nom du contact de production"), tenant.contact_name
    )
    missing("PRODUCTEUR_EMAIL_MANQUANT", _("L'e-mail du contact de production"), tenant.email)
    if _blank(tenant.siret):
        out.append(
            _block(
                "PRODUCTEUR_SIRET_MANQUANT",
                _("Renseignez le SIRET de la structure."),
                "structure",
                url,
            )
        )
    else:
        try:
            validate_siret(tenant.siret)
        except Exception:
            out.append(
                _block(
                    "PRODUCTEUR_SIRET_INVALIDE",
                    _("Le SIRET de la structure semble erroné."),
                    "structure",
                    url,
                )
            )
    if _blank(tenant.phone):
        out.append(
            _warn(
                "PRODUCTEUR_TELEPHONE_MANQUANT",
                _("Le téléphone de la structure est recommandé."),
                "structure",
                url,
            )
        )

    if tenant.licence_exempt:
        if _blank(tenant.licence_exemption_reason):
            out.append(
                _block(
                    "PRODUCTEUR_DISPENSE_SANS_MOTIF",
                    _("Indiquez le motif de dispense de licence."),
                    "structure",
                    url,
                )
            )
    elif _blank(tenant.licence_number):
        out.append(
            _block(
                "PRODUCTEUR_LICENCE_A_VERIFIER",
                _("Licence : indiquez votre numéro ou une dispense (situation à vérifier)."),
                "structure",
                url,
            )
        )
    elif _blank(tenant.licence_categories) or tenant.licence_valid_until is None:
        out.append(
            _block(
                "PRODUCTEUR_LICENCE_INCOMPLETE",
                _("Licence : indiquez les catégories et la date de validité."),
                "structure",
                url,
            )
        )
    elif tenant.licence_valid_until < gig.date:
        out.append(
            _block(
                "PRODUCTEUR_LICENCE_EXPIREE",
                _("La licence n'est pas valable à la date de la représentation."),
                "structure",
                url,
            )
        )

    if tenant.vat_confirmed_on is None:
        out.append(
            _block(
                "PRODUCTEUR_TVA_NON_CONFIRMEE",
                _("Confirmez le régime de TVA de la structure."),
                "structure",
                url,
            )
        )
    if tenant.vat_regime == Tenant.VatRegime.TAXABLE and tenant.vat_rate is None:
        out.append(
            _block(
                "PRODUCTEUR_TAUX_TVA_MANQUANT",
                _("Renseignez le taux de TVA de la structure."),
                "structure",
                url,
            )
        )
    if tenant.vat_regime == Tenant.VatRegime.NOT_TAXABLE and _blank(tenant.vat_exemption_note):
        out.append(
            _block(
                "PRODUCTEUR_FONDEMENT_SANS_TVA",
                _("Indiquez le fondement légal de l'absence de TVA."),
                "structure",
                url,
            )
        )
    return out


def _promoter(promoter, gig):
    url = reverse("addressbook:promoter-update", args=[promoter.pk])
    out = []

    def missing(code, text, value):
        if _blank(value):
            out.append(
                _block(code, _("Organisateur : %(what)s manque.") % {"what": text}, "promoter", url)
            )

    missing("ORGANISATEUR_NOM_MANQUANT", _("le nom"), promoter.name)
    missing("ORGANISATEUR_ADRESSE_MANQUANTE", _("l'adresse"), promoter.billing_address)
    missing("ORGANISATEUR_CODE_POSTAL_MANQUANT", _("le code postal"), promoter.postal_code)
    missing("ORGANISATEUR_VILLE_MANQUANTE", _("la ville"), promoter.city)
    missing(
        "ORGANISATEUR_SIGNATAIRE_MANQUANT", _("le nom du signataire"), promoter.representative_name
    )
    missing(
        "ORGANISATEUR_QUALITE_MANQUANTE",
        _("la qualité du signataire"),
        promoter.representative_role,
    )
    missing(
        "ORGANISATEUR_CONTACT_MANQUANT",
        _("le nom du contact administratif"),
        promoter.admin_contact_name,
    )
    missing(
        "ORGANISATEUR_EMAIL_MANQUANT",
        _("l'e-mail du contact administratif"),
        promoter.admin_contact_email,
    )
    if not _blank(promoter.representative_name) and not promoter.representative_confirmed:
        out.append(
            _block(
                "ORGANISATEUR_HABILITATION_NON_CONFIRMEE",
                _("Organisateur : confirmez que le signataire est habilité à signer."),
                "promoter",
                url,
            )
        )
    if not promoter.is_private:
        missing("ORGANISATEUR_FORME_MANQUANTE", _("la nature juridique"), promoter.legal_form)
        if _blank(promoter.siret):
            out.append(
                _block(
                    "ORGANISATEUR_SIRET_MANQUANT",
                    _("Organisateur : le SIRET manque."),
                    "promoter",
                    url,
                )
            )
        else:
            try:
                validate_siret(promoter.siret)
            except Exception:
                out.append(
                    _block(
                        "ORGANISATEUR_SIRET_INVALIDE",
                        _("Organisateur : le SIRET semble erroné."),
                        "promoter",
                        url,
                    )
                )
        if promoter.licence_exempt:
            if _blank(promoter.licence_exemption_reason):
                out.append(
                    _block(
                        "ORGANISATEUR_DISPENSE_SANS_MOTIF",
                        _("Organisateur : indiquez le motif de dispense de licence."),
                        "promoter",
                        url,
                    )
                )
        elif _blank(promoter.licence_number) or _blank(promoter.licence_categories):
            out.append(
                _block(
                    "ORGANISATEUR_LICENCE_A_VERIFIER",
                    _("Organisateur : licence (numéro et catégories) ou dispense à renseigner."),
                    "promoter",
                    url,
                )
            )
    if _blank(promoter.phone) and _blank(promoter.admin_contact_phone):
        out.append(
            _warn(
                "ORGANISATEUR_TELEPHONE_MANQUANT",
                _("Organisateur : un téléphone est recommandé."),
                "promoter",
                url,
            )
        )
    return out


def _performance(gig, today):
    url = reverse("documents:contract-complete", args=[gig.pk])
    out = []

    def block(code, message):
        out.append(_block(code, message, "contract", url))

    def warn(code, message):
        out.append(_warn(code, message, "contract", url))

    if _blank(gig.show.title) or _blank(gig.show.group_name):
        block(
            "SPECTACLE_INCOMPLET",
            _("Spectacle : le titre et le nom de l'artiste ou du groupe sont requis."),
        )
    if gig.show.duration_minutes < 1:
        block("DUREE_MANQUANTE", _("Spectacle : la durée est requise."))
    if gig.performances_count < 1:
        block("REPRESENTATIONS_INVALIDES", _("Le nombre de représentations doit être au moins 1."))
    if _blank(gig.venue.name) or (_blank(gig.venue.address) and _blank(gig.venue.city)):
        block("LIEU_INCOMPLET", _("Le lieu doit avoir un nom et une adresse ou une ville."))
    if not gig.setting:
        block(
            "INTERIEUR_PLEIN_AIR_MANQUANT",
            _("Indiquez si la représentation est en intérieur ou en plein air."),
        )
    if gig.setting == Gig.Setting.OUTDOOR:
        if not gig.outdoor_fallback:
            block(
                "PLEIN_AIR_REPLI_MANQUANT",
                _("Plein air : indiquez le repli, ou son absence acceptée."),
            )
        elif gig.outdoor_fallback == Gig.OutdoorFallback.PROVIDED and _blank(
            gig.outdoor_fallback_details
        ):
            block("PLEIN_AIR_MODALITES_MANQUANTES", _("Plein air : décrivez le repli prévu."))
        if _blank(gig.outdoor_procedure):
            block(
                "PLEIN_AIR_PROCEDURE_MANQUANTE",
                _("Plein air : indiquez la procédure de maintien, report ou arrêt."),
            )
        if _blank(gig.outdoor_referents):
            block(
                "PLEIN_AIR_REFERENTS_MANQUANTS",
                _("Plein air : indiquez les référents des deux parties."),
            )
    if gig.performance_time is None:
        block("HEURE_DE_PASSAGE_MANQUANTE", _("L'heure de début de la représentation manque."))
    if gig.copies_count < 2:
        block("EXEMPLAIRES_INSUFFISANTS", _("Le contrat est établi en 2 exemplaires au moins."))
    if gig.get_in_time is None:
        warn(
            "ARRIVEE_MANQUANTE",
            _("L'heure d'arrivée manque : « à préciser dans la fiche d'accueil »."),
        )
    if gig.soundcheck_time is None:
        warn(
            "BALANCES_MANQUANTES",
            _("L'heure des balances manque : « à préciser dans la fiche d'accueil »."),
        )
    if gig.performance_time is not None and any(
        t is not None and t > gig.performance_time for t in (gig.get_in_time, gig.soundcheck_time)
    ):
        # A time alone cannot tell a show that runs past midnight: only a warning.
        warn(
            "HORAIRES_A_VERIFIER",
            _("L'arrivée ou les balances sont après le début : vérifiez les horaires."),
        )
    if gig.venue.capacity is None:
        warn("JAUGE_MANQUANTE", _("La jauge manque : « à préciser dans la fiche d'accueil »."))
    if not gig.is_free and gig.ticket_price <= 0:
        warn("PRIX_DES_PLACES_MANQUANT", _("Le prix des places manque : « à préciser »."))
    if _blank(gig.onsite_contact_name):
        warn(
            "CONTACT_SUR_PLACE_MANQUANT",
            _("Le contact sur place manque : « à préciser dans la fiche d'accueil »."),
        )
    return out


def _annexes(gig):
    if has_tech_sheet(gig.show):
        return []
    return [
        _block(
            "ANNEXE_FICHE_TECHNIQUE_MANQUANTE",
            _("Spectacle : déposez la fiche technique (PDF ou texte), c'est l'annexe 1."),
            "show",
            reverse("catalog:show-update", args=[gig.show.pk]),
        )
    ]


def _tour_and_price(gig):
    url = reverse("documents:contract-complete", args=[gig.pk])
    out = []

    def block(code, message):
        out.append(_block(code, message, "contract", url))

    if gig.crew_headcount is None or gig.crew_headcount < 1:
        block("EFFECTIF_MANQUANT", _("Indiquez le nombre de personnes en tournée."))
    for covered_by, people, count, code, what, unit in (
        (
            gig.meals_covered_by,
            gig.meals_people,
            gig.meals_count,
            "RESTAURATION",
            _("Restauration"),
            _("le nombre de repas"),
        ),
        (
            gig.lodging_covered_by,
            gig.lodging_people,
            gig.lodging_nights,
            "HEBERGEMENT",
            _("Hébergement"),
            _("le nombre de nuits"),
        ),
    ):
        if not covered_by:
            block(
                f"{code}_NON_PRECISEE",
                _("%(what)s : précisez qui la prend en charge, ou « non concerné ».")
                % {"what": what},
            )
        elif covered_by in (CoveredBy.ORGANISER, CoveredBy.SHARED):
            if not count or not people:
                block(
                    f"{code}_INCOMPLETE",
                    _("%(what)s : indiquez le nombre de personnes et %(unit)s.")
                    % {"what": what, "unit": unit},
                )
            elif gig.crew_headcount and people > gig.crew_headcount:
                block(
                    f"{code}_EFFECTIF_SUPERIEUR",
                    _("%(what)s : %(people)d personnes, mais %(crew)d seulement en tournée.")
                    % {"what": what, "people": people, "crew": gig.crew_headcount},
                )
            elif gig.crew_headcount and people < gig.crew_headcount:
                out.append(
                    Anomaly(
                        f"{code}_EFFECTIF_INFERIEUR",
                        CONFIRMATION,
                        str(
                            _(
                                "%(what)s : %(people)d personnes sur %(crew)d en tournée. "
                                "Confirmez que les autres ne sont pas pris en charge."
                            )
                            % {"what": what, "people": people, "crew": gig.crew_headcount}
                        ),
                        "contract",
                        url,
                        f"{people}/{gig.crew_headcount}",
                    )
                )
    if not gig.transport_covered_by:
        block(
            "TRANSPORT_NON_PRECISE",
            _("Transport : précisez qui le prend en charge, ou « non concerné »."),
        )

    if gig.price <= 0:
        block("PRIX_MANQUANT", _("Le prix de cession doit être supérieur à 0."))
    if gig.deposit_required is None:
        block("ACOMPTE_NON_PRECISE", _("Précisez si un acompte est demandé."))
    elif gig.deposit_required:
        if not 0 < gig.deposit_percent <= 100:
            block(
                "ACOMPTE_MONTANT_INVALIDE", _("Acompte : indiquez un pourcentage entre 0 et 100.")
            )
        if gig.deposit_term == DepositTerm.SPECIFIC and gig.deposit_due_on is None:
            block("ACOMPTE_ECHEANCE_MANQUANTE", _("Acompte : indiquez son échéance."))
    elif gig.deposit_percent > 0:
        block(
            "ACOMPTE_CONTRADICTOIRE",
            _("Pas d'acompte demandé, mais un pourcentage est saisi : mettez-le à 0."),
        )
    if gig.balance_term == BalanceTerm.SPECIFIC and gig.balance_due_on is None:
        block("SOLDE_ECHEANCE_MANQUANTE", _("Indiquez l'échéance du solde."))
    if not _blank(gig.extra_fees_description) or gig.extra_fees_amount:
        if _blank(gig.extra_fees_description):
            block("FRAIS_SANS_DESCRIPTION", _("Frais supplémentaires : décrivez-les."))
        if not gig.extra_fees_amount:
            block("FRAIS_SANS_MONTANT", _("Frais supplémentaires : indiquez le montant."))
        if not gig.extra_fees_accepted:
            block(
                "FRAIS_NON_ACCEPTES",
                _("Frais supplémentaires : confirmez l'accord de l'organisateur."),
            )
    if _blank(gig.billing_notes):
        block("FACTURATION_NON_PRECISEE", _("Indiquez les modalités de facturation."))
    return out


def _confirmations(gig, contract, today):
    url = reverse("documents:contract-complete", args=[gig.pk])
    out = []
    if gig.date < today:
        out.append(
            Anomaly(
                PAST_DATE,
                CONFIRMATION,
                str(
                    _(
                        "La représentation est passée : confirmez que le contrat régularise "
                        "une date déjà jouée (il ne sera pas antidaté)."
                    )
                ),
                "contract",
                url,
                gig.date.isoformat(),
            )
        )
    name = contract.signatory_name.strip() if contract else ""
    if not name:
        out.append(
            _block(
                "PRODUCTEUR_SIGNATAIRE_MANQUANT",
                _("Indiquez le nom et la qualité de la personne qui signe pour la structure."),
                "contract",
                url,
            )
        )
    else:
        role = contract.signatory_role.strip()
        if not role:
            out.append(
                _block(
                    "PRODUCTEUR_QUALITE_MANQUANTE",
                    _("Indiquez la qualité du signataire de la structure."),
                    "contract",
                    url,
                )
            )
        else:
            out.append(
                Anomaly(
                    PRODUCER_SIGNATORY,
                    CONFIRMATION,
                    str(
                        _("Confirmez que %(who)s est habilité(e) à signer pour la structure.")
                        % {"who": f"{name}, {role}"}
                    ),
                    "contract",
                    url,
                    f"{name} — {role}",
                )
            )
    return out
