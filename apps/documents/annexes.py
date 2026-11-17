"""The two annexes of the contract and the single PDF that holds all three (spec 03, §6.1).

Annex 1 is the technical sheet of the show (the PDF uploaded on the show, or its text); annex 2,
the welcome sheet, is written from the data of the date. `assemble` joins them to the contract.
"""

import hashlib
import io

from django.utils.translation import gettext as _
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

from apps.core.services import render_pdf

MAX_ANNEX_BYTES = 10 * 1024 * 1024
TECH_SHEET = "tech_sheet"
WELCOME_SHEET = "welcome_sheet"


class ContractAnnexError(Exception):
    """An annex cannot be read or is too big: the contract is never produced without it."""


def has_tech_sheet(show):
    return bool(show.tech_sheet_file or show.tech_sheet_text.strip())


def _read_tech_sheet_file(show):
    try:
        with show.tech_sheet_file.open("rb") as handle:
            data = handle.read(MAX_ANNEX_BYTES + 1)
    except OSError as error:
        raise ContractAnnexError(_("La fiche technique du spectacle est introuvable.")) from error
    if len(data) > MAX_ANNEX_BYTES:
        raise ContractAnnexError(_("La fiche technique dépasse 10 Mo : allégez le fichier."))
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted or not len(reader.pages):
            raise ContractAnnexError(_("La fiche technique est protégée ou vide."))
    except PyPdfError as error:
        raise ContractAnnexError(_("La fiche technique n'est pas un PDF lisible.")) from error
    return data


def _page(title, date, pdf):
    return {
        "title": title,
        "date": date,
        "sha256": hashlib.sha256(pdf).hexdigest() if pdf else "",
        "pages": len(PdfReader(io.BytesIO(pdf)).pages) if pdf else 0,
    }


def build_annexes(gig, taken_on, transport_text):
    """Return ({key: description}, [pdf bytes in order]) for the two annexes of a date.

    A missing technical sheet gives a page saying so (the checks block the final generation;
    the preview still works). `taken_on` is the date printed as the version of each annex.
    """
    show = gig.show
    if show.tech_sheet_file:
        tech_pdf = _read_tech_sheet_file(show)
    else:
        tech_pdf = render_pdf(
            "documents/contracts/tech_sheet_page.html",
            {"show": show, "missing": not show.tech_sheet_text.strip()},
        )
    welcome_pdf = render_pdf(
        "documents/contracts/welcome_sheet.html",
        {
            "gig": gig,
            "show": show,
            "venue": gig.venue,
            "promoter": gig.promoter,
            "tenant": gig.tenant,
            "transport_text": transport_text,
        },
    )
    date = f"{taken_on:%d/%m/%Y}"
    descriptions = {
        TECH_SHEET: {
            "key": TECH_SHEET,
            **_page(_("Fiche technique — %(show)s") % {"show": show.title}, date, tech_pdf),
        },
        WELCOME_SHEET: {
            "key": WELCOME_SHEET,
            **_page(
                _("Fiche d'accueil — %(venue)s, %(date)s")
                % {"venue": gig.venue.name, "date": f"{gig.date:%d/%m/%Y}"},
                date,
                welcome_pdf,
            ),
        },
    }
    return descriptions, [tech_pdf, welcome_pdf]


def assemble(contract_pdf, annex_pdfs):
    """The contract followed by its annexes, as one PDF."""
    writer = PdfWriter()
    for pdf in (contract_pdf, *annex_pdfs):
        writer.append(PdfReader(io.BytesIO(pdf)))
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
