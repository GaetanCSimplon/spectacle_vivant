"""CSV export of the address book (organisers, venues, contacts): what the list shows.

Same format as the financial exports (`;`, UTF-8 with BOM, a cell starting with `=` is neutralised).
Several links in one cell are separated by ` | `, the same separator the CSV import will read.
"""

import csv

from django.http import HttpResponse
from django.utils import timezone

from apps.finance.exports import BOM, text

SEPARATOR = " | "


def _names(items):
    return text(SEPARATOR.join(item.name for item in items))


def promoter_row(promoter):
    return [
        text(promoter.name),
        promoter.get_follow_up_display() if promoter.follow_up else "",
        text(SEPARATOR.join(promoter.kind_labels)),
        text(promoter.siret),
        text(promoter.billing_address),
        text(promoter.postal_code),
        text(promoter.city),
        text(promoter.email),
        text(promoter.phone),
        _names(promoter.contacts.all()),
    ]


def venue_row(venue):
    return [
        text(venue.name),
        text(venue.address),
        text(venue.postal_code),
        text(venue.city),
        venue.capacity or "",
        text(venue.phone),
        _names(venue.promoters.all()),
    ]


def contact_row(contact):
    return [
        text(contact.name),
        text(contact.role),
        text(contact.email),
        text(contact.phone),
        _names(contact.promoters.all()),
        _names(contact.venues.all()),
    ]


EXPORTS = {
    "organisateurs": (
        [
            "Nom",
            "Statut",
            "Type",
            "SIRET",
            "Adresse",
            "Code postal",
            "Ville",
            "E-mail",
            "Téléphone",
            "Contacts",
        ],
        promoter_row,
    ),
    "lieux": (
        ["Nom", "Adresse", "Code postal", "Ville", "Jauge", "Téléphone", "Organisateurs"],
        venue_row,
    ),
    "contacts": (
        ["Nom", "Fonction", "E-mail", "Téléphone", "Organisateurs", "Lieux"],
        contact_row,
    ),
}


def csv_response(kind, objects):
    header, build_row = EXPORTS[kind]
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = f"{kind}-{timezone.localdate():%Y-%m-%d}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write(BOM)
    writer = csv.writer(response, delimiter=";", lineterminator="\r\n")
    writer.writerow(header)
    for obj in objects:
        writer.writerow(build_row(obj))
    return response
