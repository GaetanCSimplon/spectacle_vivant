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
from apps.gigs import checklist as gig_checklist
from apps.gigs.models import Gig, GigChecklist

from .models import Person

# Wide enough to cover every invoice, payment and expense.
FIRST_DAY, LAST_DAY = date(2000, 1, 1), date(2100, 12, 31)

text, amount, day = finance_exports.text, finance_exports.amount, finance_exports.day


def _number(value):
    return "" if value is None else value


def _yes(value):
    return "oui" if value else "non"


def shows_rows(tenant):
    header = [
        "Titre",
        "Groupe",
        "Durée (min)",
        "Prix indicatif",
        "N° SACEM",
        "Fiche technique",
        "Effectif",
        "Artistes",
        "Techniciens",
        "Balances minimum (min)",
        "Entre balances et set minimum (min)",
        "Code analytique",
        "Distribution",
    ]
    rows = [
        [
            text(s.title),
            text(s.group_name),
            s.duration_minutes,
            amount(s.default_price),
            text(s.sacem_number),
            text(s.tech_sheet_text),
            _number(s.crew_size),
            _number(s.artists_count),
            _number(s.technicians_count),
            _number(s.soundcheck_minutes),
            _number(s.soundcheck_to_set_minutes),
            text(s.analytic_code),
            text(s.distribution_text),
        ]
        for s in Show.objects.filter(tenant=tenant).prefetch_related("cast").order_by("title")
    ]
    return header, rows


def promoters_rows(tenant):
    header = [
        "Nom",
        "SIRET",
        "Code APE",
        "N° de TVA",
        "Représentant",
        "Adresse de facturation",
        "E-mail",
        "Téléphone",
        "Suivi",
        "Type d'organisateur",
        "Type d'évènement",
        "Esthétique / discipline",
        "Format / jauge",
        "Jauge indicative",
        "Période habituelle",
        "Rôle dans l'évènement",
        "Autres précisions",
        "Code postal",
        "Ville",
        "Département",
    ]
    rows = [
        [
            text(p.name),
            text(p.siret),
            text(p.code_ape),
            text(p.vat_number),
            text(p.representative_name),
            text(p.billing_address),
            text(p.email),
            text(p.phone),
            text(p.get_follow_up_display()),
            text(", ".join(p.kind_labels)),
            text(", ".join(p.event_type_labels)),
            text(", ".join(p.aesthetic_labels)),
            text(", ".join(p.labels_for("formats"))),
            _number(p.indicative_capacity),
            text(", ".join(p.labels_for("usual_periods"))),
            text(", ".join(p.labels_for("event_roles"))),
            text(p.qualification_other),
            text(p.postal_code),
            text(p.city),
            text(p.get_department_display()),
        ]
        for p in Promoter.objects.filter(tenant=tenant).order_by("name")
    ]
    return header, rows


def venues_rows(tenant):
    header = [
        "Nom",
        "Adresse",
        "Jauge",
        "Téléphone",
        "Infos d'accès",
        "Notes",
        "Code postal",
        "Ville",
        "Département",
    ]
    rows = [
        [
            text(v.name),
            text(v.address),
            v.capacity or "",
            text(v.phone),
            text(v.access_info),
            text(v.notes),
            text(v.postal_code),
            text(v.city),
            text(v.get_department_display()),
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
        "Nom de l'évènement",
        "Représentations",
        "Exemplaires du contrat",
        "Délai de retour du contrat (jours)",
        "Mode de paiement",
        "Acompte à régler le",
        "Solde à régler le",
        "Repas",
        "Hébergement",
        "Transports locaux",
        "Autres éléments d'accueil",
        "Code analytique",
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
            text(g.event_name),
            g.performances_count,
            g.copies_count,
            g.signature_deadline_days if g.signature_deadline_days is not None else "",
            g.get_payment_method_display(),
            day(g.deposit_due_on) if g.deposit_due_on else "",
            day(g.balance_due_on) if g.balance_due_on else "",
            text(g.meals),
            text(g.lodging),
            text(g.local_transport),
            text(g.other_hospitality),
            text(g.show.analytic_code),
        ]
        for g in gigs
    ]
    return header, rows


def checklists_rows(tenant):
    """One row per gig that has a checklist: "oui" for a done box, "non" otherwise."""
    boxes = [(key, str(label)) for _title, items in gig_checklist.SECTIONS for key, label in items]
    header = ["Date", "Spectacle", *(label for _key, label in boxes), "Dernière modification"]
    checklists = (
        GigChecklist.objects.filter(tenant=tenant)
        .select_related("gig__show")
        .order_by("gig__date", "id")
    )
    rows = [
        [
            day(c.gig.date),
            text(c.gig.show.title),
            *(_yes(c.items.get(key) is True) for key, _label in boxes),
            day(c.updated_at.date()),
        ]
        for c in checklists
    ]
    return header, rows


def team_rows(tenant, include_private=False):
    """The private columns (address, GUSO number, birth date, social security number) are for
    the owner's export only."""
    header = [
        "Nom",
        "Prénom",
        "Fonction",
        "Artiste",
        "Technicien",
        "Statut",
        "Téléphone",
        "E-mail",
        "Cachet moyen",
        "Notes",
    ]
    if include_private:
        header += [
            "Adresse",
            "Code postal",
            "Ville",
            "Département",
            "N° GUSO",
            "Date de naissance",
            "N° de sécurité sociale",
        ]
    rows = []
    for p in Person.objects.filter(tenant=tenant):
        row = [
            text(p.last_name),
            text(p.first_name),
            text(p.role),
            "oui" if p.is_artist else "",
            "oui" if p.is_technician else "",
            text(p.status),
            text(p.phone),
            text(p.email),
            amount(p.average_fee) if p.average_fee is not None else "",
            text(p.notes),
        ]
        if include_private:
            row += [
                text(p.address),
                text(p.postal_code),
                text(p.city),
                text(p.get_department_display()),
                text(p.guso_number),
                p.birth_date.strftime("%d/%m/%Y") if p.birth_date else "",
                text(p.formatted_social_security_number),
            ]
        rows.append(row)
    return header, rows


def _finance(builder):
    return lambda tenant: builder(tenant, FIRST_DAY, LAST_DAY)


# file name -> builder(tenant) -> (header, rows)
TABLES = {
    "dates": gigs_rows,
    "checklists-contractualisation": checklists_rows,
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
  dates, checklists de contractualisation, spectacles, organisateurs, lieux, contacts, équipe,
  factures et avoirs, recettes, dépenses ;
- le dossier « fichiers » : vos contrats (toutes les versions et le PDF signé), devis,
  factures, justificatifs de dépenses, ainsi que les fiches techniques et riders.

Non inclus dans cet export : le contenu des feuilles de route (horaires, hébergement,
repas, équipe) et le détail des lignes de devis et de facture (consultez les PDF).
{missing}"""


def build_export_zip(tenant, include_private=False):
    """Return an open temporary file holding the ZIP, positioned at the start.

    `include_private` adds the owner-only columns (address and GUSO number of the team).
    """
    archive = tempfile.SpooledTemporaryFile(max_size=20 * 1024 * 1024)
    missing = []
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, builder in TABLES.items():
            if name == "equipe":
                header, rows = builder(tenant, include_private=include_private)
            else:
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
