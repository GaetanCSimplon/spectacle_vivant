"""Radar's rules: what is missing or does not fit, read from the facts already entered.

Radar watches and warns, it never changes anything and never blocks (docs/marque/sources-associe/
RADAR-PARATGE/02-RADAR-copilote.md). Each rule is a plain function that reads one object and
returns a `Finding` or None; the lists at the bottom say which objects they read. Alerts are
computed when the page is shown and stored nowhere (version 0).
"""

import datetime
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.finance.models import Expense
from apps.gigs.models import Gig

IMPORTANT, FIX, KNOW = "important", "fix", "know"
SEVERITIES = {IMPORTANT: _("Important"), FIX: _("À corriger"), KNOW: _("À savoir")}
ORDER = {IMPORTANT: 0, FIX: 1, KNOW: 2}

# A date's route sheet is expected complete this many days before the concert (RAD-20).
ROADMAP_DAYS = 7


@dataclass(frozen=True)
class Explanation:
    """The three texts under each alert ("Pourquoi cette alerte ?")."""

    why: str
    admin: str  # what a company administrator would do
    source: str = ""


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    fix_url: str
    gig: Gig | None = None

    @property
    def severity_label(self):
        return SEVERITIES[self.severity]

    @property
    def explanation(self):
        return EXPLANATIONS[self.code]


EXPLANATIONS = {
    "RAD-01": Explanation(
        _(
            "Le nom, le SIRET et l'adresse de votre structure figurent sur chaque devis, contrat "
            "et facture : sans eux, le document est incomplet."
        ),
        _("Il compléterait la fiche de la structure avant d'émettre le premier document."),
    ),
    "RAD-02": Explanation(
        _("Une facture sans IBAN ni BIC oblige l'organisateur à vous les demander pour payer."),
        _("Il ajouterait les coordonnées bancaires une fois pour toutes dans la fiche."),
    ),
    "RAD-10": Explanation(
        _(
            "Un contrat envoyé avec des blancs doit être corrigé puis renvoyé : l'organisateur "
            "signe un document à jour ou rien."
        ),
        _("Il compléterait les informations de l'organisateur et de la date avant d'envoyer."),
    ),
    "RAD-20": Explanation(
        _(
            "À une semaine du concert, l'équipe et le lieu ont besoin des horaires "
            "pour s'organiser."
        ),
        _("Il confirmerait les horaires avec le lieu et les saisirait dans la date."),
    ),
    "RAD-22": Explanation(
        _("Des horaires dans le désordre mènent à des malentendus le jour même."),
        _("Il relirait le déroulé de la journée avec le lieu."),
    ),
    "RAD-26": Explanation(
        _("Sans adresse ni ville, la feuille de route et l'accès au lieu restent incomplets."),
        _("Il demanderait l'adresse exacte au lieu et la saisirait dans sa fiche."),
    ),
    "RAD-29": Explanation(
        _("Les dépenses saisies pour cette date dépassent déjà ce qu'elle rapporte."),
        _("Il vérifierait chaque dépense, puis discuterait du prix ou des frais pris en charge."),
    ),
    "RAD-35": Explanation(
        _("Sans prix de cession, ni le contrat, ni le devis, ni le bilan ne sont fiables."),
        _("Il reporterait le prix convenu avec l'organisateur dans la date."),
    ),
}


def _gig_url(gig):
    return reverse("gigs:detail", args=[gig.pk])


def _label(gig):
    return f"{gig.promoter.name}, {gig.date:%d/%m/%Y}"


def rad_01_legal_information(tenant):
    missing = []
    if not tenant.name.strip():
        missing.append(_("le nom"))
    if not tenant.siret.strip():
        missing.append(_("le SIRET"))
    if not (tenant.address.strip() or tenant.city.strip()):
        missing.append(_("l'adresse"))
    if not missing:
        return None
    message = _("Ma structure : %(missing)s manque pour vos devis, contrats et factures.") % {
        "missing": ", ".join(str(m) for m in missing)
    }
    return Finding("RAD-01", IMPORTANT, message, reverse("tenants:settings"))


def rad_02_bank_details(tenant):
    if tenant.iban.strip() and tenant.bic.strip():
        return None
    message = _("Ma structure : l'IBAN ou le BIC manque pour vos factures.")
    return Finding("RAD-02", FIX, message, reverse("tenants:settings"))


def rad_10_contract_gaps(gig):
    """What the contract of a confirmed date still lacks (it would print as dots)."""
    if gig.status != Gig.Status.CONFIRMED:
        return None
    promoter = gig.promoter
    checks = (
        (_("le SIRET de l'organisateur"), promoter.siret),
        (_("le représentant de l'organisateur"), promoter.representative_name),
        (_("sa qualité"), promoter.representative_role),
        (_("le mode de paiement"), gig.payment_method),
        (_("le lieu de signature"), gig.signing_place),
    )
    missing = [str(label) for label, value in checks if not str(value).strip()]
    if not missing:
        return None
    message = _("%(gig)s : pour le contrat, il manque %(missing)s.") % {
        "gig": _label(gig),
        "missing": ", ".join(missing),
    }
    url = reverse("documents:contract-complete", args=[gig.pk])
    return Finding("RAD-10", IMPORTANT, message, url, gig)


def rad_20_roadmap_times(gig, today):
    if gig.date < today or (gig.date - today).days > ROADMAP_DAYS:
        return None
    missing = [
        label
        for label, value in (
            (_("l'arrivée"), gig.get_in_time),
            (_("les balances"), gig.soundcheck_time),
            (_("le concert"), gig.performance_time),
        )
        if value is None
    ]
    if not missing:
        return None
    message = _("%(gig)s : l'heure de %(missing)s n'est pas saisie.") % {
        "gig": _label(gig),
        "missing": ", ".join(str(m) for m in missing),
    }
    return Finding("RAD-20", FIX, message, _gig_url(gig), gig)


def rad_22_times_out_of_order(gig):
    times = [
        (_("l'arrivée"), gig.get_in_time),
        (_("les balances"), gig.soundcheck_time),
        (_("le concert"), gig.performance_time),
    ]
    given = [(label, value) for label, value in times if value is not None]
    for (before, first), (after, second) in zip(given, given[1:], strict=False):
        if first > second:
            message = _("%(gig)s : %(before)s est prévue après %(after)s.") % {
                "gig": _label(gig),
                "before": before,
                "after": after,
            }
            return Finding("RAD-22", FIX, message, _gig_url(gig), gig)
    return None


def rad_26_no_place(gig):
    venue = gig.venue
    if venue.address.strip() or venue.city.strip():
        return None
    message = _("%(gig)s : le lieu « %(venue)s » n'a ni adresse ni ville.") % {
        "gig": _label(gig),
        "venue": venue.name,
    }
    return Finding(
        "RAD-26", FIX, message, reverse("addressbook:venue-update", args=[venue.pk]), gig
    )


def rad_35_no_price(gig):
    if gig.price > 0 or gig.is_free:
        return None
    message = _("%(gig)s : le prix de cession n'est pas renseigné.") % {"gig": _label(gig)}
    return Finding("RAD-35", FIX, message, reverse("gigs:price", args=[gig.pk]), gig)


def rad_29_expenses_above_price(gig, expenses_total):
    if gig.price <= 0 or expenses_total <= gig.price:
        return None
    message = _(
        "%(gig)s : les dépenses saisies (%(expenses)s €) dépassent le prix de cession "
        "(%(price)s €)."
    ) % {"gig": _label(gig), "expenses": f"{expenses_total:.2f}", "price": f"{gig.price:.2f}"}
    return Finding("RAD-29", FIX, message, reverse("finance:page", args=[gig.pk]), gig)


def tenant_findings(tenant):
    """The rules about the structure itself."""
    found = [rad_01_legal_information(tenant), rad_02_bank_details(tenant)]
    return [f for f in found if f]


def gig_findings(gig, today, expenses_total=Decimal("0")):
    """The rules about one date."""
    found = [
        rad_10_contract_gaps(gig),
        rad_20_roadmap_times(gig, today),
        rad_22_times_out_of_order(gig),
        rad_26_no_place(gig),
        rad_35_no_price(gig),
        rad_29_expenses_above_price(gig, expenses_total),
    ]
    return [f for f in found if f]


def all_findings(tenant, today=None):
    """Everything that sticks for a structure: its own information, then its coming dates
    (cancelled dates and past dates are left alone). Most serious first, then nearest date."""
    today = today or datetime.date.today()
    gigs = list(
        Gig.objects.filter(tenant=tenant, date__gte=today)
        .exclude(status=Gig.Status.CANCELLED)
        .select_related("promoter", "venue", "show")
        .annotate(expenses_total=Sum("expenses__amount"))
        .order_by("date")
    )
    found = tenant_findings(tenant)
    for gig in gigs:
        found.extend(gig_findings(gig, today, gig.expenses_total or Decimal("0")))
    # sorted() is stable: dates stay in order inside one severity.
    return sorted(found, key=lambda f: ORDER[f.severity])


def for_gig(gig, today=None):
    """What Radar sees on one date (the fiche of a date)."""
    today = today or datetime.date.today()
    total = gig.expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    return sorted(gig_findings(gig, today, total), key=lambda f: ORDER[f.severity])


def attach_findings(gigs, today=None):
    """Set `gig.radar` (list of findings) on every date of a list, with one query for the
    expenses (the cards of "Mes dates")."""
    today = today or datetime.date.today()
    gigs = list(gigs)
    totals = dict(
        Expense.objects.filter(gig__in=gigs)
        .values_list("gig_id")
        .annotate(total=Sum("amount"))
        .values_list("gig_id", "total")
    )
    for gig in gigs:
        found = gig_findings(gig, today, totals.get(gig.pk) or Decimal("0"))
        gig.radar = sorted(found, key=lambda f: ORDER[f.severity])
    return gigs
