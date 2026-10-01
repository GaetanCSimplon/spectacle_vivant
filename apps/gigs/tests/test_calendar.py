import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.tenants.factories import MembershipFactory

from .. import services
from ..factories import GigFactory
from ..models import Gig

pytestmark = pytest.mark.django_db

S = Gig.Status
D = datetime.date


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _calendar(client, **params):
    return client.get(reverse("gigs:calendar"), params)


def _all_days(weeks):
    return [day for week in weeks for day in week]


# --- parse_month ---------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2031-10", D(2031, 10, 1)),
        ("2000-01", D(2000, 1, 1)),
        ("2100-12", D(2100, 12, 1)),
        (None, D(2031, 5, 1)),
        ("", D(2031, 5, 1)),
        ("octobre", D(2031, 5, 1)),
        ("2031-13", D(2031, 5, 1)),
        ("2031-00", D(2031, 5, 1)),
        ("1999-12", D(2031, 5, 1)),  # out of the supported range
        ("2101-01", D(2031, 5, 1)),
        ("0001-01", D(2031, 5, 1)),
        ("9999-12", D(2031, 5, 1)),
    ],
)
def test_parse_month(value, expected):
    assert services.parse_month(value, today=D(2031, 5, 17)) == expected


# --- grid ----------------------------------------------------------------


def test_grid_has_whole_weeks_starting_on_monday():
    weeks = services.build_month_grid(D(2031, 10, 1), [])  # 1 Oct 2031 is a Wednesday

    assert all(len(week) == 7 for week in weeks)
    assert all(week[0]["date"].weekday() == 0 for week in weeks)
    assert weeks[0][0]["date"] == D(2031, 9, 29)
    assert weeks[0][2]["date"] == D(2031, 10, 1)
    assert weeks[-1][-1]["date"] >= D(2031, 10, 31)


@pytest.mark.parametrize(
    ("month_start", "weeks"),
    [
        (D(2027, 2, 1), 4),  # starts on a Monday and has 28 days
        (D(2031, 10, 1), 5),
        (D(2026, 8, 1), 6),  # starts on a Saturday and has 31 days
    ],
)
def test_grid_week_count(month_start, weeks):
    assert len(services.build_month_grid(month_start, [])) == weeks


def test_grid_marks_days_of_other_months():
    days = _all_days(services.build_month_grid(D(2031, 10, 1), []))

    in_month = [d["date"] for d in days if d["in_month"]]
    assert in_month == [D(2031, 10, n) for n in range(1, 32)]
    assert any(not d["in_month"] for d in days)


def test_grid_places_gigs_on_their_day():
    first = GigFactory.build(date=D(2031, 10, 1))
    two_a, two_b = GigFactory.build(date=D(2031, 10, 15)), GigFactory.build(date=D(2031, 10, 15))
    last = GigFactory.build(date=D(2031, 10, 31))

    days = {
        d["date"]: d["gigs"]
        for d in _all_days(services.build_month_grid(D(2031, 10, 1), [first, two_a, two_b, last]))
    }

    assert days[D(2031, 10, 1)] == [first]
    assert days[D(2031, 10, 15)] == [two_a, two_b]
    assert days[D(2031, 10, 31)] == [last]
    assert days[D(2031, 10, 2)] == []


def test_grid_never_puts_gigs_on_neighbouring_month_days():
    stray = GigFactory.build(date=D(2031, 9, 30))  # shown as a greyed day of October's grid

    days = _all_days(services.build_month_grid(D(2031, 10, 1), [stray]))

    assert all(d["gigs"] == [] for d in days)


def test_grid_flags_today():
    today = timezone.localdate()

    days = _all_days(services.build_month_grid(today.replace(day=1), []))

    assert [d["date"] for d in days if d["is_today"]] == [today]


# --- page ----------------------------------------------------------------


def test_calendar_requires_login(client):
    response = _calendar(client)

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_calendar_defaults_to_the_current_month(client):
    _login(client)

    response = _calendar(client)

    assert response.context["month_start"] == timezone.localdate().replace(day=1)
    assert response.context["is_current_month"] is True
    assert "Revenir à aujourd" not in response.content.decode()


def test_calendar_shows_only_the_requested_months_gigs(client):
    tenant = _login(client)
    in_month = GigFactory(tenant=tenant, date=D(2031, 10, 15), show__title="Concert d'octobre")
    GigFactory(tenant=tenant, date=D(2031, 9, 30), show__title="Concert de septembre")
    GigFactory(tenant=tenant, date=D(2031, 11, 1), show__title="Concert de novembre")
    GigFactory(tenant=tenant, date=D(2032, 10, 15), show__title="Concert d'un an plus tard")

    response = _calendar(client, mois="2031-10")
    content = response.content.decode()

    assert list(response.context["gigs"]) == [in_month]
    assert "Octobre 2031" in content
    assert (
        "septembre" not in content
        and "novembre" not in content
        and "un an plus tard" not in content
    )


def test_calendar_never_shows_another_tenants_gigs(client):
    _login(client)
    GigFactory(date=D(2031, 10, 15), show__title="Spectacle secret de B")

    response = _calendar(client, mois="2031-10")

    assert list(response.context["gigs"]) == []
    assert "Spectacle secret de B" not in response.content.decode()
    assert "Aucune date en" in response.content.decode()


@pytest.mark.parametrize("value", ["octobre", "2031-13", "1999-01", "9999-12", "<script>"])
def test_calendar_falls_back_to_the_current_month_on_a_bad_value(client, value):
    _login(client)

    response = _calendar(client, mois=value)

    assert response.status_code == 200
    assert response.context["month_start"] == timezone.localdate().replace(day=1)


def test_navigation_links_between_months(client):
    _login(client)

    content = _calendar(client, mois="2031-10").content.decode()

    assert "?mois=2031-09" in content
    assert "?mois=2031-11" in content
    assert "Revenir à aujourd" in content


def test_navigation_crosses_year_boundaries(client):
    _login(client)

    january = _calendar(client, mois="2031-01").content.decode()
    december = _calendar(client, mois="2031-12").content.decode()

    assert "?mois=2030-12" in january
    assert "?mois=2032-01" in december


def test_navigation_stops_at_the_supported_range(client):
    _login(client)

    first = _calendar(client, mois="2000-01")
    last = _calendar(client, mois="2100-12")

    assert first.context["previous_month"] is None
    assert first.context["next_month"] == D(2000, 2, 1)
    assert last.context["next_month"] is None
    assert last.context["previous_month"] == D(2100, 11, 1)


def test_a_single_gig_day_links_to_the_gig_page(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=D(2031, 10, 15))

    content = _calendar(client, mois="2031-10").content.decode()

    assert f'href="{reverse("gigs:detail", args=[gig.pk])}"' in content


def test_a_day_with_several_gigs_links_to_the_list_below(client):
    tenant = _login(client)
    first = GigFactory(tenant=tenant, date=D(2031, 10, 15))
    second = GigFactory(tenant=tenant, date=D(2031, 10, 15))

    content = _calendar(client, mois="2031-10").content.decode()

    assert f'href="#gig-{first.pk}"' in content
    assert f'id="gig-{first.pk}"' in content and f'id="gig-{second.pk}"' in content


def test_every_status_gets_its_dot_and_a_text_alternative(client):
    tenant = _login(client)
    for day, status in enumerate([S.OPTION, S.CONFIRMED, S.SIGNED, S.CANCELLED], start=1):
        GigFactory(tenant=tenant, date=D(2031, 10, day), status=status)

    content = _calendar(client, mois="2031-10").content.decode()

    for color in ("bg-amber-500", "bg-blue-600", "bg-green-600", "bg-gray-400"):
        assert color in content
    for label in ("Option", "Confirmée", "Signée", "Annulée"):
        assert f'<span class="sr-only">{label}</span>' in content


def test_cancelled_gigs_stay_visible_on_the_calendar(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=D(2031, 10, 15), status=S.CANCELLED)

    response = _calendar(client, mois="2031-10")

    assert list(response.context["gigs"]) == [gig]


def test_weekday_headers_start_on_monday(client):
    _login(client)

    response = _calendar(client, mois="2031-10")

    assert len(response.context["weekdays"]) == 7
    assert response.context["weekdays"][0].lower().startswith("lun")
    assert response.context["weekdays"][6].lower().startswith("dim")


def test_today_is_marked_for_assistive_technology(client):
    _login(client)

    content = _calendar(client).content.decode()

    assert 'aria-current="date"' in content


def test_empty_month_says_so(client):
    _login(client)

    content = _calendar(client, mois="2031-10").content.decode()

    assert "Aucune date en octobre 2031" in content


# --- tabs ----------------------------------------------------------------


def test_list_and_calendar_link_to_each_other(client):
    tenant = _login(client)
    GigFactory(tenant=tenant)

    list_page = client.get(reverse("gigs:list")).content.decode()
    calendar_page = _calendar(client).content.decode()

    for page in (list_page, calendar_page):
        assert reverse("gigs:list") in page
        assert reverse("gigs:calendar") in page


def test_main_navigation_keeps_mes_dates_active_on_the_calendar(client):
    _login(client)

    content = _calendar(client).content.decode()

    assert content.count('aria-current="page"') == 2  # top bar + bottom bar
    assert 'aria-current="page"\n  >Mes dates</a>' in content
