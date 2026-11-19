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
from django.utils.translation import ngettext

from apps.documents import checks
from apps.documents.models import Invoice, Quote
from apps.finance.models import Expense
from apps.gigs.models import Gig
from apps.tenants import social
from apps.tenants.models import SocialMonthFollow

IMPORTANT, FIX, KNOW = "important", "fix", "know"
SEVERITIES = {IMPORTANT: _("Important"), FIX: _("À corriger"), KNOW: _("À savoir")}
ORDER = {IMPORTANT: 0, FIX: 1, KNOW: 2}

# A date's route sheet is expected complete this many days before the concert (RAD-20).
ROADMAP_DAYS = 7

# From this day, an organizer without SIREN can no longer be invoiced (electronic invoicing,
# spec 04 §6.2): the alert turns from "à corriger" to "important" (Radar itself never blocks).
SIREN_REQUIRED_FROM = datetime.date(2027, 9, 1)


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
    "RAD-40": Explanation(
        _(
            "À partir du 1er septembre 2027, une facture doit porter le SIREN du client "
            "professionnel (facturation électronique)."
        ),
        _("Il demanderait le SIRET à l'organisateur et le saisirait dans sa fiche."),
    ),
    "RAD-41": Explanation(
        _(
            "La licence d'entrepreneur de spectacles est mentionnée sur vos devis et factures. "
            "Sans elle, et sans dispense déclarée, la ligne reste vide."
        ),
        _("Il renseignerait la licence, ou déclarerait la dispense si elle s'applique."),
    ),
    "RAD-42": Explanation(
        _(
            "Un client particulier doit pouvoir recourir gratuitement à un médiateur de la "
            "consommation : son nom figure sur le devis et la facture."
        ),
        _("Il ajouterait le nom et le site de son médiateur dans la fiche de la structure."),
    ),
    "RAD-43": Explanation(
        _("Le total facturé dépasserait le prix de cession de la date."),
        _("Il vérifierait le montant avant d'émettre, ou corrigerait le prix de la date."),
    ),
    "RAD-65": Explanation(
        _(
            "La paie de vos artistes et techniciens se prépare avant la fin du mois : plus les "
            "informations (brut, heures, n° de sécurité sociale) sont complètes, moins votre "
            "prestataire de paie vous relance."
        ),
        _("Il vérifierait le mois avec son gestionnaire de paie, puis lui enverrait le tableau."),
    ),
    "RAD-44": Explanation(
        _("Le devis de cette date n'a pas été accepté et sa durée de validité est dépassée."),
        _("Il confirmerait que le prix convenu tient toujours, ou enverrait un nouveau devis."),
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


def rad_10_contract_gaps(gig, today=None):
    """What the contract of a confirmed date still lacks (the checks of the contract engine)."""
    if gig.status != Gig.Status.CONFIRMED:
        return None
    count = len(checks.to_fix(checks.check_contract(gig, today=today)))
    if not count:
        return None
    message = ngettext(
        "%(gig)s : pour le contrat, %(n)d élément à compléter.",
        "%(gig)s : pour le contrat, %(n)d éléments à compléter.",
        count,
    ) % {"gig": _label(gig), "n": count}
    url = reverse("documents:contract-history", args=[gig.pk])
    return Finding("RAD-10", IMPORTANT, message, url, gig)


def rad_20_roadmap_times(gig, today, horizon=ROADMAP_DAYS):
    """`horizon`: how many days before the concert the times are expected (None: always, as when
    the route sheet is about to be shared)."""
    if gig.date < today or (horizon is not None and (gig.date - today).days > horizon):
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


def rad_40_no_siren(gig, today):
    promoter = gig.promoter
    if promoter.is_private or len([c for c in promoter.siret if c.isdigit()]) >= 9:
        return None
    message = _(
        "%(gig)s : le SIRET de l'organisateur manque (son SIREN sera exigé sur la facture)."
    ) % {"gig": _label(gig)}
    severity = IMPORTANT if today >= SIREN_REQUIRED_FROM else FIX
    url = reverse("addressbook:promoter-update", args=[promoter.pk])
    return Finding("RAD-40", severity, message, url, gig)


def rad_41_no_licence(tenant):
    if tenant.licence_number.strip() or tenant.licence_exempt:
        return None
    message = _("Ma structure : ni numéro de licence, ni dispense déclarée.")
    return Finding("RAD-41", KNOW, message, reverse("tenants:settings"))


def rad_42_no_mediator(gig):
    if not gig.promoter.is_private or gig.tenant.mediator.strip():
        return None
    message = _("%(gig)s : client particulier, mais aucun médiateur n'est renseigné.") % {
        "gig": _label(gig)
    }
    return Finding("RAD-42", FIX, message, reverse("tenants:settings"), gig)


def rad_43_over_invoiced(gig, draft):
    """Issuing `draft` would bring the total invoiced above the price of the date."""
    if gig.price <= 0:
        return None
    already = Invoice.objects.filter(
        tenant=gig.tenant, gig=gig, status__in=[Invoice.Status.ISSUED, Invoice.Status.PAID]
    ).exclude(kind=Invoice.Kind.CREDIT_NOTE)
    total = (already.aggregate(total=Sum("total_excl_tax"))["total"] or Decimal("0")) + (
        draft.total_excl_tax
    )
    if total <= gig.price:
        return None
    message = _(
        "%(gig)s : le total facturé (%(total)s € HT) dépasserait le prix de cession "
        "(%(price)s € HT)."
    ) % {"gig": _label(gig), "total": f"{total:.2f}", "price": f"{gig.price:.2f}"}
    return Finding("RAD-43", FIX, message, reverse("documents:billing", args=[gig.pk]), gig)


def rad_44_expired_quote(gig):
    """The quotes of the date were issued, none was accepted, and the latest has expired."""
    quotes = list(
        Quote.objects.filter(tenant=gig.tenant, gig=gig, status=Quote.Status.ISSUED).order_by(
            "-created_at", "-id"
        )
    )
    if not quotes or any(q.accepted_on for q in quotes) or not quotes[0].is_expired:
        return None
    message = _("%(gig)s : le devis %(number)s est expiré et n'a pas été accepté.") % {
        "gig": _label(gig),
        "number": quotes[0].number,
    }
    return Finding("RAD-44", FIX, message, reverse("documents:billing", args=[gig.pk]), gig)


def rad_65_social_month(tenant, today):
    """From 10 days before the end of the month, remind that the social check is due (RAD-65).
    Only counts are shown, never a name or an amount. It closes when everything is complete or
    when the month is marked "Paie faite"."""
    first = today.replace(day=1)
    last = social.month_bounds(first)[1]
    if today < last - datetime.timedelta(days=social.REMINDER_DAYS):
        return None
    data = social.build_social_month(tenant, first.year, first.month)
    missing = data.to_complete_count
    if not data.pay_count or not missing:
        return None
    if SocialMonthFollow.objects.filter(tenant=tenant, month=first, paid_at__isnull=False).exists():
        return None
    message = ngettext(
        "Navette sociale de %(month)s : %(pays)d paie à vérifier avant le %(last)s, "
        "%(missing)d point à compléter.",
        "Navette sociale de %(month)s : %(pays)d paies à vérifier avant le %(last)s, "
        "%(missing)d points à compléter.",
        missing,
    ) % {
        "month": f"{first:%m/%Y}",
        "pays": data.pay_count,
        "last": f"{last:%d/%m/%Y}",
        "missing": missing,
    }
    url = reverse("tenants:social") + f"?mois={first:%Y-%m}"
    return Finding("RAD-65", FIX, message, url)


def tenant_findings(tenant, today=None):
    """The rules about the structure itself."""
    today = today or datetime.date.today()
    found = [
        rad_65_social_month(tenant, today),
        rad_01_legal_information(tenant),
        rad_02_bank_details(tenant),
        rad_41_no_licence(tenant),
    ]
    return [f for f in found if f]


def gig_findings(gig, today, expenses_total=Decimal("0")):
    """The rules about one date."""
    found = [
        rad_10_contract_gaps(gig, today),
        rad_20_roadmap_times(gig, today),
        rad_22_times_out_of_order(gig),
        rad_26_no_place(gig),
        rad_35_no_price(gig),
        rad_40_no_siren(gig, today),
        rad_42_no_mediator(gig),
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
        .select_related("promoter", "venue", "show", "tenant", "contract")
        .prefetch_related("confirmations")
        .annotate(expenses_total=Sum("expenses__amount"))
        .order_by("date")
    )
    found = tenant_findings(tenant, today)
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


# The alerts that matter before an action that commits the user (one pop-up per action, shared
# with Paratge later): the rules of the structure and of the date that bear on it.
ACTIONS = {
    "contract_send": {"RAD-01", "RAD-10"},
    "contract_sign": {"RAD-01", "RAD-10", "RAD-29"},
    "quote_issue": {"RAD-01", "RAD-41", "RAD-42"},
    "invoice_issue": {"RAD-01", "RAD-02", "RAD-40", "RAD-41", "RAD-42", "RAD-43", "RAD-44"},
    "roadmap_share": {"RAD-20", "RAD-22", "RAD-26"},
}


def for_action(action, gig, today=None, document=None):
    """The alerts to show before `action` on `gig`, most serious first. Never blocks: the user
    can always go on. `document`: the draft about to be issued (read by RAD-43)."""
    today = today or datetime.date.today()
    codes = ACTIONS[action]
    found = [f for f in tenant_findings(gig.tenant) + for_gig(gig, today) if f.code in codes]
    if action == "invoice_issue":
        found += [
            f
            for f in (
                rad_43_over_invoiced(gig, document) if document else None,
                rad_44_expired_quote(gig),
            )
            if f
        ]
    if action == "roadmap_share" and not any(f.code == "RAD-20" for f in found):
        # Whatever the distance to the concert, a route sheet about to be shared needs its times.
        times = rad_20_roadmap_times(gig, today, horizon=None)
        found += [times] if times else []
    return sorted(found, key=lambda f: ORDER[f.severity])
