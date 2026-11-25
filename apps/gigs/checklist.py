"""The contracting checklist of a gig (F-83): which steps are done, nothing else.

A box is done or not done. There is no alert, no block and no progress. The list below is the
single source of the boxes: adding one here needs no migration. The boxes the app can know
(quote, contract, invoices, payments, roadmap) are computed from the data and cannot be ticked by
hand; the others are ticked by the user and stored.
"""

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.documents.models import Contract, Invoice, Quote
from apps.roadmaps.models import Roadmap

from .models import GigChecklist

# (section title, [(key, label), ...]), in the order shown to the user.
SECTIONS = [
    (
        _("Avant confirmation de la date"),
        [
            ("quote_sent", _("Devis envoyé")),
            ("quote_accepted", _("Devis accepté / accord du lieu")),
        ],
    ),
    (
        _("Contrat"),
        [
            ("contract_sent", _("Contrat envoyé")),
            ("contract_signed", _("Contrat signé / retourné")),
        ],
    ),
    (
        _("Documents techniques"),
        [
            ("tech_sheet_sent", _("Fiche technique envoyée")),
            ("rider_sent", _("Rider envoyé")),
            ("roadmap_sent", _("Feuille de route envoyée")),
        ],
    ),
    (
        _("Facturation"),
        [
            ("deposit_invoice_sent", _("Acompte envoyé")),
            ("deposit_received", _("Acompte reçu")),
            ("balance_invoice_sent", _("Facture de solde envoyée")),
            ("balance_received", _("Solde reçu")),
        ],
    ),
    (
        _("Intervenants / intermittents"),
        [
            ("crew_contracts_signed", _("Contrats intermittents envoyés / signés")),
            ("dpae_sent", _("DPAE envoyée")),
            ("dpae_receipt_received", _("Accusé DPAE reçu")),
        ],
    ),
    (
        _("Clôture"),
        [
            ("documents_archived", _("Tous les documents archivés")),
            ("closed", _("Date clôturée")),
        ],
    ),
]

# The boxes shown inside the volet cards of the date page; the modal of that page lists the others.
VOLET_ITEMS = {
    "contrats": [
        "quote_sent",
        "quote_accepted",
        "contract_sent",
        "contract_signed",
        "tech_sheet_sent",
        "rider_sent",
    ],
    "budget": [
        "deposit_invoice_sent",
        "deposit_received",
        "balance_invoice_sent",
        "balance_received",
    ],
}

ITEM_KEYS = {key for _title, items in SECTIONS for key, _label in items}


def automatic_items(gig):
    """The keys of the boxes that are done according to the data of the gig."""
    scope = {"gig": gig, "tenant": gig.tenant}
    sent = (Invoice.Status.ISSUED, Invoice.Status.PAID)
    invoices = Invoice.objects.filter(**scope)
    deposits = invoices.filter(kind=Invoice.Kind.DEPOSIT)
    balances = invoices.filter(kind__in=(Invoice.Kind.BALANCE, Invoice.Kind.FULL))
    quotes = Quote.objects.filter(**scope)
    contract = Contract.objects.filter(**scope).first()
    done = {
        "quote_sent": quotes.exclude(status=Quote.Status.DRAFT).exists(),
        "quote_accepted": quotes.filter(accepted_on__isnull=False).exists(),
        "contract_sent": bool(contract and contract.sent_at),
        "contract_signed": bool(contract and contract.status == Contract.Status.SIGNED),
        "roadmap_sent": Roadmap.objects.filter(**scope, is_published=True).exists(),
        "deposit_invoice_sent": deposits.filter(status__in=sent).exists(),
        "deposit_received": deposits.filter(status=Invoice.Status.PAID).exists(),
        "balance_invoice_sent": balances.filter(status__in=sent).exists(),
        "balance_received": balances.filter(status=Invoice.Status.PAID).exists(),
    }
    return {key for key, value in done.items() if value}


AUTOMATIC_KEYS = {
    "quote_sent",
    "quote_accepted",
    "contract_sent",
    "contract_signed",
    "roadmap_sent",
    "deposit_invoice_sent",
    "deposit_received",
    "balance_invoice_sent",
    "balance_received",
}


class InvalidChecklistItem(Exception):
    """The box does not exist, or the value is not a plain true / false."""


def checklist_sections(gig):
    """The sections with every box and whether it is done. Reading creates nothing."""
    checklist = GigChecklist.objects.filter(gig=gig, tenant=gig.tenant).first()
    done = checklist.items if checklist else {}
    automatic = automatic_items(gig)
    return [
        {
            "title": title,
            "items": [
                {
                    "key": key,
                    "label": label,
                    "auto": key in AUTOMATIC_KEYS,
                    "done": key in automatic if key in AUTOMATIC_KEYS else done.get(key) is True,
                }
                for key, label in items
            ],
        }
        for title, items in SECTIONS
    ]


def last_update(gig):
    """When the checklist last changed (None if it never did)."""
    return (
        GigChecklist.objects.filter(gig=gig, tenant=gig.tenant)
        .values_list("updated_at", flat=True)
        .first()
    )


def set_item(gig, key, value, user):
    """Tick or untick one box, leaving every other box as it is."""
    if key not in ITEM_KEYS or key in AUTOMATIC_KEYS or not isinstance(value, bool):
        raise InvalidChecklistItem(key)
    with transaction.atomic():
        # Locked, so two quick clicks on two boxes both survive.
        checklist, _created = GigChecklist.objects.select_for_update().get_or_create(
            gig=gig, tenant=gig.tenant
        )
        if checklist.items.get(key, False) is value:
            return checklist
        checklist.items = {**checklist.items, key: value}
        checklist.updated_by = user
        checklist.save(update_fields=["items", "updated_by", "updated_at"])
    return checklist


def reset(gig, user):
    """Untick every box. A gig that never had a checklist gets none."""
    with transaction.atomic():
        checklist = (
            GigChecklist.objects.select_for_update().filter(gig=gig, tenant=gig.tenant).first()
        )
        if checklist is None:
            return None
        checklist.items = {}
        checklist.updated_by = user
        checklist.save(update_fields=["items", "updated_by", "updated_at"])
    return checklist
