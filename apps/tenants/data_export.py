"""Full export of a tenant's data (F-81): one ZIP with CSV tables and the stored files.

Everything is read through `tenant=` filters, so a ZIP can only hold the tenant's own data.
The CSV style (`;`, UTF-8 BOM, decimal comma, formula-safe text) is shared with the
finance exports.
"""

import csv
import io
import re
import tempfile
import zipfile
from datetime import date
from pathlib import PurePosixPath

from apps.addressbook.models import Contact, Promoter, Venue
from apps.catalog.models import Show
from apps.documents.models import Contract, ContractVersion, Invoice, Quote
from apps.finance import exports as finance_exports
from apps.finance.models import Expense
from apps.gigs.models import Gig

from .models import Person

# Wide enough to cover every invoice, payment and expense.
FIRST_DAY, LAST_DAY = date(2000, 1, 1), date(2100, 12, 31)

text, amount, day = finance_exports.text, finance_exports.amount, finance_exports.day


def _yes(value):
    return "oui" if value else "non"


def shows_rows(tenant):
    header = ["Titre", "Groupe", "Durée (min)", "Prix indicatif", "N° SACEM", "Fiche technique"]
    rows = [
        [
            text(s.title),
            text(s.group_name),
            s.duration_minutes,
            amount(s.default_price),
            text(s.sacem_number),
            text(s.tech_sheet_text),
        ]
        for s in Show.objects.filter(tenant=tenant).order_by("title")
    ]
    return header, rows


def promoters_rows(tenant):
    header = [
        "Nom",
        "SIRET",
        "Représentant",
        "Adresse de facturation",
        "E-mail",
        "Téléphone",
        "Suivi",
        "Type d'évènement",
        "Esthétique",
    ]
    rows = [
        [
            text(p.name),
            text(p.siret),
            text(p.representative_name),
            text(p.billing_address),
            text(p.email),
            text(p.phone),
            text(p.get_follow_up_display()),
            text(p.event_type),
            text(p.aesthetic),
        ]
        for p in Promoter.objects.filter(tenant=tenant).order_by("name")
    ]
    return header, rows


def venues_rows(tenant):
    header = ["Nom", "Adresse", "Jauge", "Téléphone", "Infos d'accès", "Notes"]
    rows = [
        [
            text(v.name),
            text(v.address),
            v.capacity or "",
            text(v.phone),
            text(v.access_info),
            text(v.notes),
        ]
        for v in Venue.objects.filter(tenant=tenant).order_by("name")
    ]
    return header, rows


def contacts_rows(tenant):
    header = ["Nom", "Fonction", "E-mail", "Téléphone", "Rattaché à"]
    contacts = (
        Contact.objects.filter(tenant=tenant).select_related("promoter", "venue").order_by("name")
    )
    rows = [
        [
            text(c.name),
            text(c.role),
            text(c.email),
            text(c.phone),
            text(c.promoter or c.venue),
        ]
        for c in contacts
    ]
    return header, rows


def gigs_rows(tenant):
    header = [
        "Date",
        "Spectacle",
        "Organisateur",
        "Lieu",
        "Statut",
        "Prix HT",
        "Acompte (%)",
        "Conditions particulières",
        "Concert gratuit",
        "Prix du billet",
        "Invitations",
    ]
    gigs = (
        Gig.objects.filter(tenant=tenant)
        .select_related("show", "promoter", "venue")
        .order_by("date", "id")
    )
    rows = [
        [
            day(g.date),
            text(g.show.title),
            text(g.promoter.name),
            text(g.venue.name),
            g.get_status_display(),
            amount(g.price),
            g.deposit_percent,
            text(g.conditions),
            _yes(g.is_free),
            amount(g.ticket_price) if g.ticket_price is not None else "",
            g.invitations_count,
        ]
        for g in gigs
    ]
    return header, rows


def team_rows(tenant):
    header = ["Nom", "Prénom", "Fonction", "Statut", "Téléphone", "E-mail", "Cachet moyen", "Notes"]
    rows = [
        [
            text(p.last_name),
            text(p.first_name),
            text(p.role),
            text(p.status),
            text(p.phone),
            text(p.email),
            amount(p.average_fee) if p.average_fee is not None else "",
            text(p.notes),
        ]
        for p in Person.objects.filter(tenant=tenant)
    ]
    return header, rows


def _finance(builder):
    return lambda tenant: builder(tenant, FIRST_DAY, LAST_DAY)


# file name -> builder(tenant) -> (header, rows)
TABLES = {
    "dates": gigs_rows,
    "spectacles": shows_rows,
    "organisateurs": promoters_rows,
    "lieux": venues_rows,
    "contacts": contacts_rows,
    "equipe": team_rows,
    "factures-et-avoirs": _finance(finance_exports.invoices_rows),
    "recettes": _finance(finance_exports.payments_rows),
    "depenses": _finance(finance_exports.expenses_rows),
}


def _csv_bytes(header, rows):
    buffer = io.StringIO()
    buffer.write(finance_exports.BOM)
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _safe(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "fichier"


def stored_files(tenant):
    """Yield (zip path, FieldFile) for every file the tenant stored."""
    for show in Show.objects.filter(tenant=tenant):
        for field in (show.rider_file, show.tech_sheet_file):
            if field:
                yield f"spectacles/{show.pk}-{_safe(PurePosixPath(field.name).name)}", field
    versions = ContractVersion.objects.filter(tenant=tenant).select_related("contract__gig")
    for version in versions:
        gig = version.contract.gig
        yield f"contrats/{gig.date}-date{gig.pk}-v{version.number}.pdf", version.pdf_file
    for contract in Contract.objects.filter(tenant=tenant).select_related("gig"):
        if contract.signed_pdf:
            yield (
                f"contrats/{contract.gig.date}-date{contract.gig_id}-signe.pdf",
                (contract.signed_pdf),
            )
    for model, folder in ((Quote, "devis"), (Invoice, "factures")):
        for doc in model.objects.filter(tenant=tenant).exclude(pdf_file=""):
            yield f"{folder}/{_safe(doc.number or f'brouillon-{doc.pk}')}.pdf", doc.pdf_file
    for expense in Expense.objects.filter(tenant=tenant).exclude(receipt_file=""):
        name = PurePosixPath(expense.receipt_file.name).name
        yield f"justificatifs/{expense.date}-{expense.pk}-{_safe(name)}", expense.receipt_file


README = """Export de vos données — {name}
Généré le {today}.

Ce dossier contient :
- les fichiers .csv (à ouvrir avec Excel ou LibreOffice, séparateur « ; », encodage UTF-8) :
  dates, spectacles, organisateurs, lieux, contacts, équipe, factures et avoirs, recettes,
  dépenses ;
- le dossier « fichiers » : vos contrats (toutes les versions et le PDF signé), devis,
  factures, justificatifs de dépenses, ainsi que les fiches techniques et riders.

Non inclus dans cet export : le contenu des feuilles de route (horaires, hébergement,
repas, équipe) et le détail des lignes de devis et de facture (consultez les PDF).
{missing}"""


def build_export_zip(tenant):
    """Return an open temporary file holding the ZIP, positioned at the start."""
    archive = tempfile.SpooledTemporaryFile(max_size=20 * 1024 * 1024)
    missing = []
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, builder in TABLES.items():
            header, rows = builder(tenant)
            zf.writestr(f"{name}.csv", _csv_bytes(header, rows))
        for path, field in stored_files(tenant):
            try:
                with field.open("rb") as source:
                    zf.writestr(f"fichiers/{path}", source.read())
            except (FileNotFoundError, OSError):
                missing.append(path)
        note = ""
        if missing:
            note = "\nFichiers introuvables, non inclus :\n" + "\n".join(f"- {m}" for m in missing)
        readme = README.format(name=tenant.name, today=day(date.today()), missing=note)
        zf.writestr("LISEZMOI.txt", readme)
    archive.seek(0)
    return archive
