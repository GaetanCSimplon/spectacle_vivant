"""Social management (F-93): who worked on which date and what each cachet is, for whoever does
the payroll. Information only: nothing here computes pay, contributions or a payslip.

Only the people of the team who are on a date (a `GigMember` linked to a `Person`) are listed:
the private details (birth date, social security number, address) live on the team card, so
someone added by hand to a date has none to give. Cancelled dates are left out.
"""

import csv
import datetime
from dataclasses import dataclass, field
from decimal import Decimal

from django.http import HttpResponse
from django.utils.cache import add_never_cache_headers
from django.utils.translation import gettext as _

from apps.gigs.models import Gig, GigMember

BOM = "﻿"
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


@dataclass
class SocialRow:
    member: GigMember
    person: object
    gig: Gig
    employment: str
    missing: list = field(default_factory=list)


def employment_label(person):
    if person.is_artist and person.is_technician:
        return _("Artiste et technicien")
    if person.is_artist:
        return _("Artiste")
    if person.is_technician:
        return _("Technicien")
    return ""


def missing_items(member, person):
    """What the payroll still needs and the user has not filled in (never blocks anything)."""
    items = []
    if not employment_label(person):
        items.append(_("emploi"))
    if person.birth_date is None:
        items.append(_("date de naissance"))
    if not person.social_security_number:
        items.append(_("n° de sécurité sociale"))
    if not person.address:
        items.append(_("adresse"))
    if member.cachet_count is None:
        items.append(_("nombre de cachets"))
    if member.cachet_amount is None:
        items.append(_("montant du cachet"))
    return items


def employer_missing(tenant):
    items = []
    if not tenant.siret:
        items.append(_("SIRET"))
    if not tenant.code_ape:
        items.append(_("code APE"))
    if not tenant.licence_number:
        items.append(_("n° de licence"))
    return items


def parse_month(value, today=None):
    """`2026-11` -> the first day of that month; anything else -> the current month."""
    today = today or datetime.date.today()
    try:
        year, month = (int(part) for part in str(value).split("-"))
        return datetime.date(year, month, 1)
    except (ValueError, TypeError):
        return today.replace(day=1)


def month_bounds(first):
    """First and last day of the month of `first`."""
    next_month = (first.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return first, next_month - datetime.timedelta(days=1)


def shift_month(first, delta):
    month = first.month - 1 + delta
    return first.replace(year=first.year + month // 12, month=month % 12 + 1, day=1)


def social_rows(tenant, start=None, end=None, person=None, newest_first=False):
    """One row per person and per date (bounds included), for this tenant only."""
    members = GigMember.objects.filter(tenant=tenant, gig__tenant=tenant, person__tenant=tenant)
    members = members.exclude(person=None).exclude(gig__status=Gig.Status.CANCELLED)
    if start is not None:
        members = members.filter(gig__date__gte=start)
    if end is not None:
        members = members.filter(gig__date__lte=end)
    if person is not None:
        members = members.filter(person=person)
    members = members.select_related("person", "gig__show")
    if newest_first:
        members = members.order_by("-gig__date", "person__last_name", "person__first_name", "id")
    else:
        members = members.order_by("person__last_name", "person__first_name", "gig__date", "id")
    return [
        SocialRow(m, m.person, m.gig, employment_label(m.person), missing_items(m, m.person))
        for m in members
    ]


def text(value):
    """A user text as a safe spreadsheet cell (a cell starting with `=` would be executed)."""
    value = str(value or "")
    return "'" + value if value.startswith(FORMULA_STARTS) else value


def day(value):
    return value.strftime("%d/%m/%Y") if value else ""


def amount(value):
    return f"{Decimal(value):.2f}".replace(".", ",") if value is not None else ""


HEADER = [
    "Structure",
    "SIRET",
    "Code APE",
    "N° de licence",
    "Nom",
    "Prénom",
    "Emploi",
    "Date de naissance",
    "Adresse",
    "Code postal",
    "Ville",
    "N° de sécurité sociale",
    "Date",
    "Spectacle",
    "N° d'objet",
    "Nombre de cachets",
    "Montant brut du cachet",
    "À compléter",
]


def csv_response(tenant, start, end):
    """The owner's export: the employer's details are repeated on every line, so the file can be
    imported as it is. Never cached (it holds social security numbers)."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="gestion-sociale-{start:%Y-%m}.csv"'
        if start.day == 1 and end == month_bounds(start)[1]
        else f'attachment; filename="gestion-sociale-{start}_{end}.csv"'
    )
    add_never_cache_headers(response)
    response.write(BOM)
    writer = csv.writer(response, delimiter=";", lineterminator="\r\n")
    writer.writerow(HEADER)
    for row in social_rows(tenant, start, end):
        p, m = row.person, row.member
        writer.writerow(
            [
                text(tenant.name),
                text(tenant.siret),
                text(tenant.code_ape),
                text(tenant.licence_number),
                text(p.last_name),
                text(p.first_name),
                text(row.employment),
                day(p.birth_date),
                text(p.address),
                text(p.postal_code),
                text(p.city),
                text(p.formatted_social_security_number),
                day(row.gig.date),
                text(row.gig.show.title),
                text(row.gig.show.sacem_object_number),
                m.cachet_count if m.cachet_count is not None else "",
                amount(m.cachet_amount),
                text(", ".join(str(item) for item in row.missing)),
            ]
        )
    return response
