import calendar
import datetime
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import BooleanField, Exists, ExpressionWrapper, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show
from apps.documents.models import Contract, ContractVersion, Invoice, Quote
from apps.finance.models import Expense
from apps.roadmaps.models import Roadmap

from . import payment_terms
from .models import Gig, GigMember, PriceChange


def get_wizard_related_objects(tenant, data):
    """Fetch the Show/Promoter/Venue chosen in the wizard, scoped to the tenant."""
    show = get_object_or_404(Show, pk=data["show_id"], tenant=tenant)
    promoter = get_object_or_404(Promoter, pk=data["promoter_id"], tenant=tenant)
    venue = get_object_or_404(Venue, pk=data["venue_id"], tenant=tenant)
    return show, promoter, venue


def create_gig_from_wizard_data(tenant, data, user=None):
    show, promoter, venue = get_wizard_related_objects(tenant, data)
    with transaction.atomic():
        gig = Gig.objects.create(
            tenant=tenant,
            show=show,
            promoter=promoter,
            venue=venue,
            date=data["date"],
            option_expires_on=data.get("option_expires_on") or None,
            price=data["price"],
            conditions=data.get("conditions", ""),
            event_name=data.get("event_name", ""),
        )
        PriceChange.objects.create(
            tenant=tenant, gig=gig, old_price=None, new_price=gig.price, changed_by=user
        )
    return gig


def count_gigs_for_year(tenant, year):
    """Number of gigs dated in `year`, cancelled ones excluded (prepares the freemium quota)."""
    return (
        Gig.objects.filter(tenant=tenant, date__year=year)
        .exclude(status=Gig.Status.CANCELLED)
        .count()
    )


CALENDAR_YEARS = range(2000, 2101)


def parse_month(value, today=None):
    """First day of the month in "YYYY-MM", or of the current month if it is missing or odd."""
    today = today or timezone.localdate()
    try:
        month = datetime.datetime.strptime(value, "%Y-%m").date()
    except (TypeError, ValueError):
        return today.replace(day=1)
    return month if month.year in CALENDAR_YEARS else today.replace(day=1)


def build_month_grid(month_start, gigs):
    """Weeks (Monday first) of `month_start`'s month, each day carrying its gigs.

    Days of the neighbouring months only fill the first and last weeks: they are
    marked `in_month=False` and never carry gigs.
    """
    by_day = defaultdict(list)
    for gig in gigs:
        by_day[gig.date].append(gig)
    today = timezone.localdate()
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
        month_start.year, month_start.month
    )
    return [
        [
            {
                "date": day,
                "in_month": day.month == month_start.month,
                "is_today": day == today,
                "gigs": by_day.get(day, []) if day.month == month_start.month else [],
            }
            for day in week
        ]
        for week in weeks
    ]


class InvalidTransition(Exception):
    """Raised when a status change is not allowed from the gig's current status."""


# F-31: option -> confirmed -> signed, and any live status -> cancelled.
# A cancelled gig only comes back through reactivate_gig() (RG-04).
ALLOWED_TRANSITIONS = {
    Gig.Status.OPTION: {Gig.Status.CONFIRMED, Gig.Status.CANCELLED},
    Gig.Status.CONFIRMED: {Gig.Status.SIGNED, Gig.Status.CANCELLED},
    Gig.Status.SIGNED: {Gig.Status.CANCELLED},
    Gig.Status.CANCELLED: set(),
}


def _lock_gig(gig):
    # Re-read under a lock so a double click or two tabs cannot apply a stale transition.
    return Gig.objects.select_for_update().get(pk=gig.pk, tenant=gig.tenant)


def change_status(gig, new_status):
    """Move a gig to `new_status` if F-31 allows it, otherwise raise InvalidTransition."""
    with transaction.atomic():
        locked = _lock_gig(gig)
        if new_status not in ALLOWED_TRANSITIONS[locked.status]:
            raise InvalidTransition(
                _("Le passage de « %(old)s » à « %(new)s » n'est pas possible.")
                % {"old": locked.get_status_display(), "new": Gig.Status(new_status).label}
            )
        locked.status = new_status
        locked.save(update_fields=["status"])
    gig.status = new_status
    return gig


def reactivate_gig(gig):
    """Explicit reactivation of a cancelled gig: it goes back to `option` (RG-04).

    Exception: a gig whose contract is signed goes back to `signed`, since the frozen
    contract is still valid (RG-08).
    """
    with transaction.atomic():
        locked = _lock_gig(gig)
        if locked.status != Gig.Status.CANCELLED:
            raise InvalidTransition(_("Seule une date annulée peut être réactivée."))
        has_signed_contract = Contract.objects.filter(
            gig=locked, tenant=locked.tenant, status=Contract.Status.SIGNED
        ).exists()
        locked.status = Gig.Status.SIGNED if has_signed_contract else Gig.Status.OPTION
        locked.save(update_fields=["status"])
    gig.status = locked.status
    return gig


class CannotDelete(Exception):
    """Raised when a gig still carries legal or financial traces."""


def deletion_blockers(gig):
    """Plain-French reasons why this gig cannot be deleted (empty list = it can)."""
    scope = {"gig": gig, "tenant": gig.tenant}
    reasons = []
    if Invoice.objects.filter(**scope, status=Invoice.Status.ISSUED).exists():
        reasons.append(_("Une facture ou un avoir a été émis pour cette date."))
    if Quote.objects.filter(**scope, status=Quote.Status.ISSUED).exists():
        reasons.append(_("Un devis a été émis pour cette date."))
    if Contract.objects.filter(**scope, status=Contract.Status.SIGNED).exists():
        reasons.append(_("Le contrat de cession est signé."))
    if Expense.objects.filter(**scope).exists():
        reasons.append(_("Des dépenses sont enregistrées pour cette date."))
    return reasons


def delete_blank_gig(gig):
    """Delete a gig with no legal or financial trace, with its drafts, contract and roadmap.

    Re-checked under the gig lock; raises CannotDelete otherwise. Stored PDFs of the
    unsigned contract are removed from the storage once the transaction has succeeded.
    """
    files = []
    with transaction.atomic():
        locked = _lock_gig(gig)
        reasons = deletion_blockers(locked)
        if reasons:
            raise CannotDelete(reasons[0])
        for model in (Invoice, Quote):
            for draft in model.objects.filter(gig=locked, tenant=locked.tenant):
                draft.delete()
        versions = ContractVersion.objects.filter(contract__gig=locked, tenant=locked.tenant)
        files = [(v.pdf_file.storage, v.pdf_file.name) for v in versions if v.pdf_file]
        locked.delete()
    for storage, name in files:
        storage.delete(name)


class CannotChangePrice(Exception):
    """Raised when the price of a gig may not change (or the new price is not valid)."""


def price_blockers(gig):
    """Plain-French reasons why the price of this gig is locked (empty list = it can change)."""
    scope = {"gig": gig, "tenant": gig.tenant}
    reasons = []
    if gig.status == Gig.Status.CANCELLED:
        reasons.append(_("La date est annulée."))
    if Contract.objects.filter(**scope, status=Contract.Status.SIGNED).exists():
        reasons.append(_("Le contrat de cession est signé."))
    if Invoice.objects.filter(**scope).exclude(status=Invoice.Status.DRAFT).exists():
        reasons.append(_("Une facture ou un avoir a été émis pour cette date."))
    return reasons


def clean_price(value):
    """The price as a Decimal to the cent, or CannotChangePrice when it is not a valid amount."""
    try:
        price = Decimal(str(value).replace(",", ".").strip())
    except InvalidOperation:
        raise CannotChangePrice(_("Le prix doit être un nombre.")) from None
    if not price.is_finite() or price.quantize(Decimal("0.01")) != price:
        raise CannotChangePrice(_("Le prix s'écrit en euros, avec au plus deux décimales."))
    if price <= 0:
        raise CannotChangePrice(_("Le prix doit être supérieur à 0."))
    if price >= Decimal("1000000"):
        raise CannotChangePrice(_("Ce prix est trop élevé."))
    return price


def change_price(gig, new_price, user, note=""):
    """Set a new price HT on the gig and write it in the price history.

    Returns the new PriceChange, or None when the price is the same (nothing is written).
    """
    price = clean_price(new_price)
    with transaction.atomic():
        locked = _lock_gig(gig)
        reasons = price_blockers(locked)
        if reasons:
            raise CannotChangePrice(" ".join(str(reason) for reason in reasons))
        if locked.price == price:
            return None
        change = PriceChange.objects.create(
            tenant=locked.tenant,
            gig=locked,
            old_price=locked.price,
            new_price=price,
            changed_by=user,
            note=note.strip()[:255],
        )
        locked.price = price
        locked.save(update_fields=["price"])
    gig.price = price
    return change


def with_locks(queryset):
    """Annotate gigs with `price_locked` (`price_blockers` is not empty) and `terms_locked`."""
    signed = Contract.objects.filter(gig=OuterRef("pk"), status=Contract.Status.SIGNED)
    invoiced = Invoice.objects.filter(gig=OuterRef("pk")).exclude(status=Invoice.Status.DRAFT)
    return queryset.annotate(
        terms_locked=Exists(signed),
        price_locked=ExpressionWrapper(
            Q(status=Gig.Status.CANCELLED) | Q(Exists(signed)) | Q(Exists(invoiced)),
            output_field=BooleanField(),
        ),
    )


def with_roadmap_sharing(queryset):
    """Annotate gigs with `roadmap_shared`: whether the secret link of the roadmap is active."""
    shared = Roadmap.objects.filter(gig=OuterRef("pk"), is_published=True)
    return queryset.annotate(roadmap_shared=Exists(shared))


class CannotChangeTerms(Exception):
    """Raised when the payment terms of a gig may not change."""


TERM_FIELDS = (
    "payment_method",
    "deposit_term",
    "deposit_term_days",
    "deposit_due_on",
    "balance_term",
    "balance_due_on",
)


def signature_date(gig):
    """The day the contract of a date was marked signed, or None."""
    if gig.pk is None:
        return None
    signed_at = (
        Contract.objects.filter(gig=gig, tenant=gig.tenant, status=Contract.Status.SIGNED)
        .values_list("signed_at", flat=True)
        .first()
    )
    return timezone.localtime(signed_at).date() if signed_at else None


def due_dates(gig, deposit_term, deposit_term_days, balance_term):
    """(deposit date, balance date) the chosen rules give; None where a rule has no date."""
    return (
        payment_terms.deposit_date(deposit_term, deposit_term_days, gig.date, signature_date(gig)),
        payment_terms.balance_date(balance_term, gig.date),
    )


def update_terms(gig, **fields):
    """Set the payment terms printed in the contract (refused once the contract is signed).

    `fields` are the `TERM_FIELDS`; the dates are the ones the rules give, worked out by the form.
    """
    with transaction.atomic():
        locked = _lock_gig(gig)
        if Contract.objects.filter(
            gig=locked, tenant=locked.tenant, status=Contract.Status.SIGNED
        ).exists():
            raise CannotChangeTerms(
                _("Ce contrat est signé : ses informations ne peuvent plus être modifiées.")
            )
        for name in TERM_FIELDS:
            setattr(locked, name, fields[name])
        locked.save(update_fields=list(TERM_FIELDS))
    for name in TERM_FIELDS:
        setattr(gig, name, fields[name])
    return gig


def refresh_due_dates(gig):
    """Work the dates out again from the rules, once the contract is signed (CTR-05).

    Only the rules that give a date change it; "Date précise" keeps the date typed.
    """
    deposit, balance = due_dates(gig, gig.deposit_term, gig.deposit_term_days, gig.balance_term)
    if gig.deposit_term != payment_terms.DepositTerm.SPECIFIC:
        gig.deposit_due_on = deposit
    if gig.balance_term != payment_terms.BalanceTerm.SPECIFIC:
        gig.balance_due_on = balance
    gig.save(update_fields=["deposit_due_on", "balance_due_on"])
    return gig


def _volet(key, letter, label, steps):
    """A volet with its steps [(label, done, url, todo)]; it is done when every step is.

    `todo` is the same step as an instruction, offered as the next action while it is not done.
    """
    done_count = sum(1 for _label, done, _url, _todo in steps if done)
    return {
        "key": key,
        "letter": letter,
        "label": label,
        "steps": [
            {"label": lab, "done": done, "url": url, "todo": todo} for lab, done, url, todo in steps
        ],
        "done_count": done_count,
        "total": len(steps),
        "percent": round(100 * done_count / len(steps)),
        "done": done_count == len(steps),
    }


def _progress_facts(gigs):
    """What the steps of the volets look at, for several gigs of one tenant, in few queries.

    Returns {gig id: {fact: bool}}; `date_progress` (one gig) and `attach_progress` (a list)
    both read it, so the two never disagree.
    """
    gigs = list(gigs)
    ids = [gig.pk for gig in gigs]
    tenant_ids = {gig.tenant_id for gig in gigs}
    facts = {
        gig_id: {
            "generated": False,
            "sent": False,
            "signed": False,
            "invoiced": False,
            "unpaid": False,
            "team": False,
            "filled": False,
            "shared": False,
        }
        for gig_id in ids
    }
    scope = {"gig_id__in": ids, "tenant_id__in": tenant_ids}
    for contract in Contract.objects.filter(**scope).prefetch_related("versions"):
        row = facts[contract.gig_id]
        row["signed"] = contract.status == Contract.Status.SIGNED
        row["generated"] = bool(contract.versions.all())
        row["sent"] = bool(contract.sent_at) or row["signed"]
    invoices = (
        Invoice.objects.filter(**scope)
        .exclude(status__in=[Invoice.Status.DRAFT, Invoice.Status.CANCELLED])
        .exclude(kind=Invoice.Kind.CREDIT_NOTE)
        .values_list("gig_id", "status")
    )
    for gig_id, status in invoices:
        facts[gig_id]["invoiced"] = True
        if status != Invoice.Status.PAID:
            facts[gig_id]["unpaid"] = True
    members = GigMember.objects.filter(**scope, person__isnull=False)
    for gig_id in members.values_list("gig_id", flat=True).distinct():
        facts[gig_id]["team"] = True
    for roadmap in Roadmap.objects.filter(**scope).prefetch_related("slots"):
        facts[roadmap.gig_id]["filled"] = bool(roadmap.slots.all())
        facts[roadmap.gig_id]["shared"] = roadmap.is_published
    return facts


def _volets_from_facts(gig, row):
    contract_url = reverse("documents:contract-history", args=[gig.pk])
    billing_url = reverse("documents:billing", args=[gig.pk])
    roadmap_url = reverse("roadmaps:editor", args=[gig.pk])
    return [
        _volet(
            "contrats",
            "C",
            _("Contrats"),
            [
                (_("Contrat généré"), row["generated"], contract_url, _("Générer le contrat")),
                (
                    _("Contrat envoyé"),
                    row["sent"],
                    contract_url,
                    _("Marquer le contrat comme envoyé"),
                ),
                (_("Contrat signé"), row["signed"], contract_url, _("Faire signer le contrat")),
            ],
        ),
        _volet(
            "budget",
            "B",
            _("Budget"),
            [
                (_("Facture émise"), row["invoiced"], billing_url, _("Émettre la facture")),
                (
                    _("Factures payées"),
                    row["invoiced"] and not row["unpaid"],
                    reverse("finance:page", args=[gig.pk]),
                    _("Enregistrer les paiements"),
                ),
            ],
        ),
        _volet(
            "social",
            "S",
            _("Social"),
            [
                (
                    _("Équipe ajoutée"),
                    row["team"],
                    reverse("gigs:detail", args=[gig.pk]) + "#equipe",
                    _("Ajouter l'équipe"),
                )
            ],
        ),
        _volet(
            "regie",
            "R",
            _("Régie"),
            [
                (
                    _("Feuille de route remplie"),
                    row["filled"],
                    roadmap_url,
                    _("Remplir la feuille de route"),
                ),
                (
                    _("Feuille de route partagée"),
                    row["shared"],
                    roadmap_url,
                    _("Partager la feuille de route"),
                ),
            ],
        ),
    ]


def date_progress(gig):
    """The four volets of a date, each with its steps (charter v1.3: C, B, S, R).

    Contrats: generated, sent, signed. Budget: an invoice issued, then every invoice paid.
    Social: someone from the team is on the date. Régie: the roadmap has slots, then is shared.
    """
    return _volets_from_facts(gig, _progress_facts([gig])[gig.pk])


def attach_progress(gigs):
    """Set `gig.progress` on every gig of a list (the cards of "Mes dates"), in few queries."""
    gigs = list(gigs)
    facts = _progress_facts(gigs)
    for gig in gigs:
        gig.progress = _volets_from_facts(gig, facts[gig.pk])
    return gigs


def overall_progress(progress):
    """Share of all the steps done, over the four volets (each volet weighs a quarter)."""
    return round(sum(volet["percent"] for volet in progress) / len(progress))


def next_step(gig, progress):
    """The first step still to do, for a date that can move forward (confirmed or signed)."""
    if gig.status not in (Gig.Status.CONFIRMED, Gig.Status.SIGNED):
        return None
    for volet in progress:
        for step in volet["steps"]:
            if not step["done"]:
                return {"volet": volet, **step}
    return None


def gig_documents(gig):
    """Everything produced for a date, as one list of {label, detail, url}: quotes, contract
    versions, invoices and credit notes, roadmap. Drafts are listed too (they can be finished).
    """
    tenant = gig.tenant
    rows = []
    for quote in Quote.objects.filter(gig=gig, tenant=tenant).order_by("-created_at"):
        rows.append(
            {
                "kind": _("Devis"),
                "label": quote.number or _("Brouillon"),
                "day": quote.issue_date,
                "url": reverse("documents:document-detail", args=[gig.pk, "devis", quote.pk]),
            }
        )
    contract = Contract.objects.filter(gig=gig, tenant=tenant).first()
    if contract:
        for version in contract.versions.all():
            rows.append(
                {
                    "kind": _("Contrat"),
                    "label": _("Version %(n)s") % {"n": version.number},
                    "day": _day(version.created_at),
                    "url": reverse(
                        "documents:contract-version-download", args=[gig.pk, version.number]
                    ),
                }
            )
    for invoice in Invoice.objects.filter(gig=gig, tenant=tenant).order_by("-created_at"):
        kind = _("Avoir") if invoice.kind == Invoice.Kind.CREDIT_NOTE else _("Facture")
        rows.append(
            {
                "kind": kind,
                "label": invoice.number or _("Brouillon"),
                "day": invoice.issue_date,
                "url": reverse("documents:document-detail", args=[gig.pk, "factures", invoice.pk]),
            }
        )
    roadmap = Roadmap.objects.filter(gig=gig, tenant=tenant).first()
    if roadmap:
        rows.append(
            {
                "kind": _("Feuille de route"),
                "label": _("Partagée") if roadmap.is_published else _("Non partagée"),
                "day": _day(roadmap.updated_at),
                "url": reverse("roadmaps:editor", args=[gig.pk]),
            }
        )
    return rows


def gig_contacts(gig):
    """The contacts of the date's organiser, then those of its venue (read only, no duplicate).

    Both sides are limited to the date's tenant, so a contact of another structure never shows.
    """
    from apps.addressbook.models import Contact  # noqa: PLC0415 (same-level import)

    tenant = gig.tenant
    groups = []
    seen = set()
    for label, entity, filters in (
        (_("Organisateur"), gig.promoter, {"promoters": gig.promoter}),
        (_("Lieu"), gig.venue, {"venues": gig.venue}),
    ):
        contacts = [
            contact
            for contact in Contact.objects.filter(tenant=tenant, **filters).order_by("name")
            if contact.pk not in seen
        ]
        seen.update(contact.pk for contact in contacts)
        groups.append({"label": label, "entity": entity, "contacts": contacts})
    return groups


def _day(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return timezone.localtime(value).date() if timezone.is_aware(value) else value.date()
    return value


def gig_timeline(gig):
    """The milestones of a date, in the order they usually happen, each with its stored date.

    A step without a date is still to come. Nothing is recorded in a journal: every date is read
    from what the other screens already store (no model, no migration).
    """
    from apps.addressbook.models import PromoterInvitation  # noqa: PLC0415 (same-level import)
    from apps.finance.models import Payment  # noqa: PLC0415 (finance imports gigs)

    tenant = gig.tenant
    detail_url = reverse("gigs:detail", args=[gig.pk])
    contract_url = reverse("documents:contract-history", args=[gig.pk])
    billing_url = reverse("documents:billing", args=[gig.pk])
    steps = []

    def step(label, day, url):
        steps.append({"label": label, "day": _day(day), "url": url})

    created = PriceChange.objects.filter(gig=gig, tenant=tenant, old_price__isnull=True).first()
    step(_("Date créée"), created.changed_at if created else None, detail_url)

    invitation = PromoterInvitation.objects.filter(promoter=gig.promoter, tenant=tenant).first()
    promoter_url = reverse("addressbook:promoter-detail", args=[gig.promoter_id])
    step(_("Formulaire envoyé"), invitation.created_at if invitation else None, promoter_url)
    step(
        _("Formulaire reçu"),
        invitation.completed_at if invitation else None,
        promoter_url,
    )

    quote = (
        Quote.objects.filter(gig=gig, tenant=tenant, issue_date__isnull=False)
        .order_by("-issue_date", "-pk")
        .first()
    )
    step(_("Devis émis"), quote.issue_date if quote else None, billing_url)

    contract = Contract.objects.filter(gig=gig, tenant=tenant).first()
    first_version = contract.versions.order_by("created_at").first() if contract else None
    step(_("Contrat généré"), first_version.created_at if first_version else None, contract_url)
    step(_("Contrat envoyé"), contract.sent_at if contract else None, contract_url)
    step(_("Contrat signé"), contract.signed_at if contract else None, contract_url)

    invoices = Invoice.objects.filter(gig=gig, tenant=tenant, issue_date__isnull=False).exclude(
        kind=Invoice.Kind.CREDIT_NOTE
    )
    for kinds, issued_label, paid_label in (
        ((Invoice.Kind.DEPOSIT,), _("Facture d'acompte émise"), _("Acompte payé")),
        (
            (Invoice.Kind.BALANCE, Invoice.Kind.FULL),
            _("Facture de solde émise"),
            _("Solde payé"),
        ),
    ):
        invoice = invoices.filter(kind__in=kinds).order_by("issue_date", "pk").first()
        step(issued_label, invoice.issue_date if invoice else None, billing_url)
        paid_on = None
        if invoice and invoice.status == Invoice.Status.PAID:
            last = Payment.objects.filter(invoice=invoice, tenant=tenant).order_by("-date").first()
            paid_on = last.date if last else None
        step(paid_label, paid_on, reverse("finance:page", args=[gig.pk]))
    return steps
