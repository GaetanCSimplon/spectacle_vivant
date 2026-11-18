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

from django.db.models import Sum
from django.http import HttpResponse
from django.utils.cache import add_never_cache_headers
from django.utils.text import slugify
from django.utils.translation import gettext as _

from apps.finance.models import Expense
from apps.finance.services import estimated_employer_cost
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
    if worked_hours(member, person) is None:
        items.append(
            _("heures") if person.is_technician and not person.is_artist else _("nombre de cachets")
        )
    if member.cachet_amount is None:
        items.append(_("montant du cachet"))
    if not member.gig.show.sacem_object_number:
        items.append(_("n° d'objet du spectacle"))
    return items


HOURS_PER_CACHET = 12  # France Travail rule, for artists paid by the cachet


def worked_hours(member, person):
    """Cachets x 12 for an artist with cachets; the real hours otherwise; None if unknown."""
    if member.cachet_count is not None and (person.is_artist or member.hours is None):
        return Decimal(member.cachet_count * HOURS_PER_CACHET)
    return member.hours


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


@dataclass
class SocialLine:
    row: SocialRow
    hours: Decimal | None
    gross: Decimal | None
    employer_cost: Decimal | None  # an estimation, never a real computation
    expenses: Decimal  # paid back apart from the gross

    @property
    def complete(self):
        return not self.row.missing


@dataclass
class SocialShow:
    show: object
    lines: list = field(default_factory=list)
    hours: Decimal = Decimal("0")
    gross: Decimal = Decimal("0")
    employer_cost: Decimal = Decimal("0")
    expenses: Decimal = Decimal("0")


@dataclass
class SocialMonth:
    start: datetime.date
    shows: list
    totals: SocialShow
    pay_count: int
    people_count: int
    gigs_without_team: list  # "À compléter"
    cancelled_with_team: list  # "À vérifier"

    @property
    def to_complete_count(self):
        return sum(1 for show in self.shows for line in show.lines if not line.complete) + len(
            self.gigs_without_team
        )


def build_social_month(tenant, year, month):
    """The single source of the month's figures, read by the screen and both exports.

    One pay = one team member on one date; the month is the one of `Gig.date`. Amounts are
    exact to the cent; the employer cost is an estimation (reference rate of the tenant).
    """
    start, end = month_bounds(datetime.date(year, month, 1))
    rows = social_rows(tenant, start, end)
    expenses = {
        (e["gig"], e["person"]): e["total"]
        for e in Expense.objects.filter(
            tenant=tenant, gig__tenant=tenant, gig__date__range=(start, end), person__isnull=False
        )
        .values("gig", "person")
        .annotate(total=Sum("amount"))
    }
    by_show = {}
    for row in rows:
        m = row.member
        line = SocialLine(
            row=row,
            hours=worked_hours(m, row.person),
            gross=m.cachet_amount,
            employer_cost=estimated_employer_cost(m.cachet_amount, tenant.employer_cost_rate),
            expenses=expenses.get((m.gig_id, m.person_id), Decimal("0")),
        )
        by_show.setdefault(row.gig.show_id, SocialShow(show=row.gig.show)).lines.append(line)
    shows = sorted(
        by_show.values(), key=lambda s: (s.show.sacem_object_number or "~", s.show.title)
    )
    totals = SocialShow(show=None)
    for block in shows:
        block.lines.sort(
            key=lambda x: (x.row.gig.date, x.row.person.last_name, x.row.person.first_name)
        )
        for line in block.lines:
            _add(block, line)
            _add(totals, line)

    gigs = Gig.objects.filter(tenant=tenant, date__range=(start, end)).select_related("show")
    with_team = set(
        GigMember.objects.filter(tenant=tenant, gig__in=gigs, person__isnull=False).values_list(
            "gig_id", flat=True
        )
    )
    return SocialMonth(
        start=start,
        shows=shows,
        totals=totals,
        pay_count=len(rows),
        people_count=len({r.person.pk for r in rows}),
        gigs_without_team=[
            g for g in gigs.exclude(status=Gig.Status.CANCELLED) if g.pk not in with_team
        ],
        cancelled_with_team=[
            g for g in gigs.filter(status=Gig.Status.CANCELLED) if g.pk in with_team
        ],
    )


def _add(target, line):
    target.hours += line.hours or 0
    target.gross += line.gross or 0
    target.employer_cost += line.employer_cost or 0
    target.expenses += line.expenses


HEADER = [
    "mois",
    "siret_employeur",
    "numero_objet",
    "spectacle",
    "code_analytique",
    "date_debut",
    "date_fin",
    "lieu",
    "commune",
    "nom",
    "prenom",
    "date_naissance",
    "numero_secu",
    "numero_guso",
    "categorie",
    "fonction",
    "nb_cachets",
    "nb_heures",
    "brut",
    "defraiements",
    "statut_ligne",
    "reference_bordpro",
]


def _number(value):
    """Decimal point, to the cent, as the payroll providers import it; empty when unknown."""
    return "" if value is None else f"{Decimal(value):.2f}"


def csv_response(tenant, year, month):
    """The owner's file for the payroll provider: one line per pay, read from the same service as
    the screen. No estimated cost in it. Never cached (it holds social security numbers)."""
    data = build_social_month(tenant, year, month)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    name = slugify(tenant.name) or "structure"
    response["Content-Disposition"] = (
        f'attachment; filename="navette-sociale-{data.start:%Y-%m}-{name}.csv"'
    )
    add_never_cache_headers(response)
    response.write(BOM)
    writer = csv.writer(response, delimiter=";", lineterminator="\r\n")
    writer.writerow(HEADER)
    for block in data.shows:
        for line in block.lines:
            p, m, gig = line.row.person, line.row.member, line.row.gig
            writer.writerow(
                [
                    f"{data.start:%Y-%m}",
                    text(tenant.siret),
                    text(block.show.sacem_object_number),
                    text(block.show.title),
                    text(block.show.analytic_code),
                    day(gig.date),
                    day(gig.date),
                    text(gig.venue.name),
                    text(gig.venue.city),
                    text(p.last_name),
                    text(p.first_name),
                    day(p.birth_date),
                    text(p.social_security_number),
                    text(p.guso_number),
                    text(line.row.employment.lower()),
                    text(m.role),
                    m.cachet_count if m.cachet_count is not None else "",
                    "" if line.hours is None else f"{line.hours:f}",
                    _number(line.gross),
                    _number(line.expenses),
                    "complet" if line.complete else "a_completer",
                    m.pk,
                ]
            )
    return response
