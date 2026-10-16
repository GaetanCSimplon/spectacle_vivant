"""The contracting checklist of a gig (F-83): which steps are done, nothing else.

A box is done or not done. There is no alert, no block, no progress and no link with the real
quotes, contracts or payments. The list below is the single source of the boxes: adding one
here needs no migration.
"""

from django.db import transaction
from django.utils.translation import gettext_lazy as _

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

ITEM_KEYS = {key for _title, items in SECTIONS for key, _label in items}


class InvalidChecklistItem(Exception):
    """The box does not exist, or the value is not a plain true / false."""


def checklist_sections(gig):
    """The sections with every box and whether it is done. Reading creates nothing."""
    checklist = GigChecklist.objects.filter(gig=gig, tenant=gig.tenant).first()
    done = checklist.items if checklist else {}
    return [
        {
            "title": title,
            "items": [
                {"key": key, "label": label, "done": done.get(key) is True} for key, label in items
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
    if key not in ITEM_KEYS or not isinstance(value, bool):
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
