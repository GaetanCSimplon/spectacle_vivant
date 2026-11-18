"""The "Social" tab and its CSV (F-93): the cachets of the team, for the payroll (owner only)."""

import csv
import datetime
import io
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalog.factories import ShowFactory
from apps.finance.factories import ExpenseFactory
from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.tenants import social
from apps.tenants.factories import MembershipFactory, PersonFactory

pytestmark = pytest.mark.django_db

NOV = datetime.date(2026, 11, 1)
SSN = "185057800608491"


def _login(client, role="owner", **tenant_fields):
    membership = MembershipFactory(role=role)
    for key, value in tenant_fields.items():
        setattr(membership.tenant, key, value)
    membership.tenant.save()
    client.force_login(membership.user)
    return membership.tenant


def _person(tenant, **kwargs):
    defaults = {
        "first_name": "Léa",
        "last_name": "Chanteuse",
        "is_artist": True,
        "birth_date": datetime.date(1985, 5, 17),
        "social_security_number": SSN,
        "address": "3 rue des Lilas",
        "postal_code": "69001",
        "city": "Lyon",
    }
    defaults.update(kwargs)
    return PersonFactory(tenant=tenant, **defaults)


def _on(gig, person, count=1, amount="150.00"):
    return GigMemberFactory(
        gig=gig, person=person, name=person.full_name, cachet_count=count, cachet_amount=amount
    )


def _gig(tenant, day, **kwargs):
    show = kwargs.pop("show", None) or ShowFactory(tenant=tenant, title="Mon Spectacle")
    return GigFactory(tenant=tenant, show=show, date=day, **kwargs)


def _page(client, month="2026-11"):
    return client.get(reverse("tenants:social"), {"mois": month})


def _export(client, month="2026-11"):
    return client.get(reverse("tenants:social-export"), {"mois": month})


def _rows(response):
    content = response.content.decode("utf-8")
    assert content.startswith(social.BOM)
    return list(csv.reader(io.StringIO(content.lstrip(social.BOM)), delimiter=";"))


# --- who can see it -----------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["tenants:social", "tenants:social-export"])
def test_a_plain_member_gets_a_403_and_a_visitor_is_sent_to_login(client, name):
    assert client.get(reverse(name)).status_code == 302
    _login(client, role="member")

    assert client.get(reverse(name)).status_code == 403


def test_the_social_tab_is_shown_to_the_owner_only(client):
    _login(client)
    assert reverse("tenants:social") in client.get(reverse("tenants:person-list")).content.decode()

    _login(client, role="member")
    assert (
        reverse("tenants:social") not in client.get(reverse("tenants:person-list")).content.decode()
    )


def test_the_page_and_the_file_are_never_cached(client):
    _login(client)

    for response in (_page(client), _export(client)):
        assert "no-store" in response["Cache-Control"]


# --- the list -----------------------------------------------------------------------------------


def test_the_page_lists_the_people_of_the_month_with_their_cachets(client):
    tenant = _login(client)
    person = _person(tenant)
    show = ShowFactory(tenant=tenant, title="Mon Spectacle", sacem_object_number="OBJ-42")
    _on(_gig(tenant, datetime.date(2026, 11, 14), show=show), person, count=2, amount="300.50")

    page = _page(client).content.decode()

    assert "Léa Chanteuse" in page
    assert "14/11/2026" in page
    assert "OBJ-42" in page
    assert "300.50 €" in page or "300,50 €" in page
    assert "Artiste" in page


def test_only_the_month_asked_is_listed_with_both_ends_included(client):
    tenant = _login(client)
    person = _person(tenant)
    for day, title in (
        (datetime.date(2026, 10, 31), "Fin octobre"),
        (datetime.date(2026, 11, 1), "Premier novembre"),
        (datetime.date(2026, 11, 30), "Trente novembre"),
        (datetime.date(2026, 12, 1), "Début décembre"),
    ):
        _on(_gig(tenant, day, show=ShowFactory(tenant=tenant, title=title)), person)

    page = _page(client).content.decode()

    assert "Premier novembre" in page and "Trente novembre" in page
    assert "Fin octobre" not in page and "Début décembre" not in page


def test_someone_added_by_hand_and_a_cancelled_date_are_left_out(client):
    tenant = _login(client)
    person = _person(tenant)
    GigMemberFactory(
        gig=_gig(tenant, datetime.date(2026, 11, 5)), person=None, name="Invité Manuel"
    )
    cancelled = _gig(
        tenant,
        datetime.date(2026, 11, 6),
        status="cancelled",
        show=ShowFactory(tenant=tenant, title="Date annulée"),
    )
    _on(cancelled, person)

    page = _page(client).content.decode()

    assert "Invité Manuel" not in page
    # not paid, but flagged "À vérifier" so the owner removes the team from it
    assert "À vérifier" in page and "Date annulée" in page
    assert "Léa Chanteuse" not in page


def test_nothing_of_another_structure_ever_shows(client):
    tenant = _login(client)
    foreign = GigFactory(date=datetime.date(2026, 11, 10))
    stranger = _person(
        foreign.tenant,
        first_name="Intrus",
        last_name="Étranger",
        social_security_number="299123456789012",
    )
    _on(foreign, stranger)
    _on(_gig(tenant, datetime.date(2026, 11, 11)), _person(tenant, last_name="Moi"))

    for content in (_page(client).content.decode(), _export(client).content.decode()):
        assert "Moi" in content
        assert "Étranger" not in content
        assert "299123456789012" not in content.replace(" ", "")


def test_an_empty_month_says_so(client):
    _login(client)

    assert "Aucune personne de l'équipe" in _page(client, "2030-01").content.decode().replace(
        "&#x27;", "'"
    )


def test_a_wrong_month_falls_back_to_the_current_one(client):
    _login(client)
    today = datetime.date.today()

    for junk in ("", "abc", "2026-13", "2026-00", "x-y", "2026-11-01"):
        assert _page(client, junk).status_code == 200
    assert f"{today:%Y-%m}" in _page(client, "abc").content.decode()


def test_what_is_missing_is_flagged_and_never_blocks(client):
    tenant = _login(client)
    person = PersonFactory(tenant=tenant, first_name="Zoé", last_name="Incomplète")
    GigMemberFactory(
        gig=_gig(tenant, datetime.date(2026, 11, 3)), person=person, name=person.full_name
    )

    page = _page(client).content.decode()
    rows = _rows(_export(client))

    assert "Zoé Incomplète" in page
    assert "n° de sécurité sociale" in page and "montant du cachet" in page
    assert "date de naissance" in rows[1][-1] and "nombre de cachets" in rows[1][-1]


def test_a_structure_without_siret_is_told_to_complete_it(client):
    _login(client, siret="", code_ape="", licence_number="")

    page = _page(client).content.decode()

    assert "SIRET" in page and "code APE" in page and "n° de licence" in page


def test_a_complete_structure_gets_no_banner(client):
    _login(client, siret="12345678901234", code_ape="9001Z", licence_number="PLATESV-R-2022-000000")

    assert "à compléter pour la paie" not in _page(client).content.decode()


# --- the file -----------------------------------------------------------------------------------


def test_the_csv_has_the_employer_the_person_and_the_cachet_on_each_line(client):
    tenant = _login(
        client, name="Ma Compagnie", siret="12345678901234", code_ape="9001Z", licence_number="L-1"
    )
    person = _person(tenant, is_technician=True)
    show = ShowFactory(tenant=tenant, title="Mon Spectacle", sacem_object_number="OBJ-42")
    _on(_gig(tenant, datetime.date(2026, 11, 14), show=show), person, count=2, amount="1234.50")

    response = _export(client)
    header, line = _rows(response)

    assert response["Content-Type"].startswith("text/csv")
    assert response["Content-Disposition"] == 'attachment; filename="gestion-sociale-2026-11.csv"'
    assert header == social.HEADER
    record = dict(zip(header, line, strict=True))
    assert record["Structure"] == "Ma Compagnie"
    assert (record["SIRET"], record["Code APE"], record["N° de licence"]) == (
        "12345678901234",
        "9001Z",
        "L-1",
    )
    assert (record["Nom"], record["Prénom"]) == ("Chanteuse", "Léa")
    assert record["Emploi"] == "Artiste et technicien"
    assert record["Date de naissance"] == "17/05/1985"
    assert record["N° de sécurité sociale"] == "1 85 05 78 006 084 91"
    assert (record["Date"], record["Spectacle"], record["N° d'objet"]) == (
        "14/11/2026",
        "Mon Spectacle",
        "OBJ-42",
    )
    assert record["Nombre de cachets"] == "2"
    assert record["Montant brut du cachet"] == "1234,50"
    assert record["À compléter"] == ""


def test_the_csv_only_holds_the_month_asked(client):
    tenant = _login(client)
    person = _person(tenant)
    _on(_gig(tenant, datetime.date(2026, 11, 14)), person)
    _on(_gig(tenant, datetime.date(2026, 12, 2)), person)

    assert len(_rows(_export(client, "2026-11"))) == 2
    assert len(_rows(_export(client, "2026-12"))) == 2
    assert len(_rows(_export(client, "2027-01"))) == 1  # the header alone


def test_the_csv_neutralises_formulas(client):
    tenant = _login(client, name="=HYPERLINK(1)")
    person = _person(tenant, last_name="=cmd|' /C calc'!A0", first_name="+Léa")
    _on(_gig(tenant, datetime.date(2026, 11, 14)), person)

    record = dict(zip(*_rows(_export(client)), strict=True))

    assert record["Structure"].startswith("'=")
    assert record["Nom"].startswith("'=")
    assert record["Prénom"].startswith("'+")


def test_a_plain_member_cannot_download_the_file(client):
    tenant = _login(client, role="member")
    _on(_gig(tenant, datetime.date(2026, 11, 14)), _person(tenant))

    response = _export(client)

    assert response.status_code == 403
    assert SSN not in response.content.decode()


# --- the card of a person ----------------------------------------------------------------------


def test_the_card_of_a_person_lists_their_cachets_for_the_owner_only(client):
    tenant = _login(client)
    person = _person(tenant)
    _on(_gig(tenant, datetime.date(2026, 11, 14)), person, count=3, amount="99.99")
    url = reverse("tenants:person-detail", args=[person.pk])

    page = client.get(url).content.decode()

    assert "Gestion sociale" in page
    assert "3 cachet(s)" in page
    assert "99.99 €" in page or "99,99 €" in page

    _login(client, role="member")
    assert "Gestion sociale" not in client.get(reverse("tenants:person-list")).content.decode()


# --- the month helpers --------------------------------------------------------------------------


def test_month_helpers_handle_the_year_end_and_leap_years():
    assert social.parse_month("2026-11") == NOV
    assert social.parse_month("nope", datetime.date(2026, 3, 9)) == datetime.date(2026, 3, 1)
    assert social.month_bounds(datetime.date(2028, 2, 1)) == (
        datetime.date(2028, 2, 1),
        datetime.date(2028, 2, 29),
    )
    assert social.month_bounds(datetime.date(2026, 12, 1))[1] == datetime.date(2026, 12, 31)
    assert social.shift_month(datetime.date(2026, 12, 1), 1) == datetime.date(2027, 1, 1)
    assert social.shift_month(datetime.date(2026, 1, 1), -1) == datetime.date(2025, 12, 1)


def test_the_amounts_stay_decimal_to_the_cent():
    assert social.amount(Decimal("1234.5")) == "1234,50"
    assert social.amount(None) == ""


# --- build_social_month (Navette sociale) -----------------------------------------------------


def _month(tenant):
    return social.build_social_month(tenant, 2026, 11)


def _tenant():
    return MembershipFactory(role="owner").tenant


def test_an_empty_month_has_no_pay_and_zero_totals():
    month = _month(_tenant())

    assert month.shows == [] and month.pay_count == 0 and month.to_complete_count == 0
    assert month.totals.gross == 0 and month.totals.hours == 0


def test_a_cachet_is_twelve_hours_and_the_cost_is_an_estimation():
    tenant = _tenant()
    _on(_gig(tenant, datetime.date(2026, 11, 5)), _person(tenant), count=2, amount="300.00")

    month = _month(tenant)

    line = month.shows[0].lines[0]
    assert line.hours == 24
    assert line.gross == Decimal("300.00")
    assert line.employer_cost == Decimal("435.00")  # rate 0.45
    assert month.totals.hours == 24 and month.totals.employer_cost == Decimal("435.00")


def test_the_hours_of_a_technician_are_the_real_ones():
    tenant = _tenant()
    tech = _person(tenant, is_artist=False, is_technician=True)
    member = _on(_gig(tenant, datetime.date(2026, 11, 5)), tech, count=None, amount="100.00")
    member.hours = Decimal("7.50")
    member.save()

    assert _month(tenant).shows[0].lines[0].hours == Decimal("7.50")


def test_a_technician_without_hours_is_to_complete():
    tenant = _tenant()
    tech = _person(tenant, is_artist=False, is_technician=True)
    _on(_gig(tenant, datetime.date(2026, 11, 5)), tech, count=None)

    month = _month(tenant)

    assert "heures" in month.shows[0].lines[0].row.missing
    assert month.to_complete_count == 1


def test_a_line_without_gross_has_no_estimated_cost_and_is_to_complete():
    tenant = _tenant()
    _on(_gig(tenant, datetime.date(2026, 11, 5)), _person(tenant), amount=None)

    line = _month(tenant).shows[0].lines[0]

    assert line.employer_cost is None and not line.complete
    assert "montant du cachet" in line.row.missing


def test_two_shows_make_two_blocks_sorted_by_object_number():
    tenant = _tenant()
    second = ShowFactory(tenant=tenant, title="B", sacem_object_number="223P00000002")
    first = ShowFactory(tenant=tenant, title="A", sacem_object_number="223P00000001")
    person = _person(tenant)
    _on(_gig(tenant, datetime.date(2026, 11, 5), show=second), person)
    _on(_gig(tenant, datetime.date(2026, 11, 6), show=first), person)

    month = _month(tenant)

    assert [b.show.title for b in month.shows] == ["A", "B"]
    assert month.pay_count == 2 and month.people_count == 1
    assert month.totals.gross == Decimal("300.00")


def test_a_show_without_object_number_is_to_complete():
    tenant = _tenant()
    show = ShowFactory(tenant=tenant, sacem_object_number="")
    _on(_gig(tenant, datetime.date(2026, 11, 5), show=show), _person(tenant))

    assert "n° d'objet du spectacle" in _month(tenant).shows[0].lines[0].row.missing


def test_a_cancelled_date_is_not_paid_but_is_flagged_to_check():
    tenant = _tenant()
    gig = _gig(tenant, datetime.date(2026, 11, 5), status="cancelled")
    _on(gig, _person(tenant))

    month = _month(tenant)

    assert month.shows == [] and month.cancelled_with_team == [gig]


def test_a_date_without_team_is_to_complete_and_other_months_are_left_out():
    tenant = _tenant()
    gig = _gig(tenant, datetime.date(2026, 11, 5))
    _gig(tenant, datetime.date(2026, 12, 5))

    month = _month(tenant)

    assert month.gigs_without_team == [gig] and month.to_complete_count == 1


def test_expenses_are_kept_apart_from_the_gross():
    tenant = _tenant()
    person = _person(tenant)
    gig = _gig(tenant, datetime.date(2026, 11, 5))
    _on(gig, person, amount="100.00")
    ExpenseFactory(gig=gig, person=person, amount="40.00")
    ExpenseFactory(gig=gig, amount="99.00")  # paid by the structure: not a refund

    line = _month(tenant).shows[0].lines[0]

    assert line.expenses == Decimal("40.00") and line.gross == Decimal("100.00")


def test_the_month_of_another_tenant_is_invisible():
    mine, other = _tenant(), _tenant()
    person = _person(other)
    gig = _gig(other, datetime.date(2026, 11, 5))
    _on(gig, person)
    ExpenseFactory(gig=gig, person=person)

    month = _month(mine)

    assert month.shows == [] and month.gigs_without_team == [] and month.totals.expenses == 0


# --- the screen "Vérifier mon social du mois" ---------------------------------------------------


def test_the_screen_shows_the_summary_one_block_per_show_and_the_state_in_words(client):
    tenant = _login(client)
    person = _person(tenant)
    gap = PersonFactory(tenant=tenant, first_name="Zoé", last_name="Incomplète")
    _on(_gig(tenant, datetime.date(2026, 11, 14)), person)
    other = _gig(
        tenant, datetime.date(2026, 11, 15), show=ShowFactory(tenant=tenant, title="Autre")
    )
    GigMemberFactory(gig=other, person=gap, name=gap.full_name)

    page = _page(client).content.decode()

    assert "Vérifier mon social du mois" in page
    assert "Mon Spectacle" in page and "Autre" in page
    assert "Coût employeur (estimation)" in page
    assert "Complet" not in page.split("Autre")[1].split("</section>")[0]
    assert "À compléter" in page and "points à compléter" in page.replace(
        "point à compléter", "points à compléter"
    )
    assert reverse("tenants:person-detail", args=[gap.pk]) in page
    assert reverse("gigs:detail", args=[other.pk]) in page
    assert reverse("catalog:show-update", args=[other.show.pk]) in page


def test_a_date_without_team_is_listed_with_its_link(client):
    tenant = _login(client)
    gig = _gig(tenant, datetime.date(2026, 11, 9))

    page = _page(client).content.decode()

    assert "Dates sans équipe" in page and reverse("gigs:detail", args=[gig.pk]) in page


def test_the_month_arrows_get_only_the_fragment_with_htmx(client):
    _login(client)

    response = client.get(reverse("tenants:social"), {"mois": "2026-11"}, HTTP_HX_REQUEST="true")

    body = response.content.decode()
    assert 'id="social-month"' in body and "<html" not in body


def test_the_screen_of_another_structure_shows_nothing_of_the_first(client):
    other = MembershipFactory().tenant
    stranger = _person(other, last_name="Étrangère")
    gig = _gig(other, datetime.date(2026, 11, 14), show=ShowFactory(tenant=other, title="Secret"))
    _on(gig, stranger)
    _login(client)

    page = _page(client).content.decode()

    assert "Étrangère" not in page and "Secret" not in page
    assert reverse("gigs:detail", args=[gig.pk]) not in page
