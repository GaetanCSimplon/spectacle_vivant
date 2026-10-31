import datetime

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import GigFactory
from ..ical import escape, fold
from ..models import Gig

pytestmark = pytest.mark.django_db

TOMORROW = datetime.date.today() + datetime.timedelta(days=1)


@pytest.fixture
def tenant(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _unfold(response):
    return response.content.decode().replace("\r\n ", "").split("\r\n")


def test_one_date_downloads_as_an_ics_attachment(client, tenant):
    gig = GigFactory(tenant=tenant, date=TOMORROW)
    response = client.get(reverse("gigs:ical", args=[gig.pk]))
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/calendar")
    assert "attachment" in response["Content-Disposition"]
    assert response["X-Content-Type-Options"] == "nosniff"
    lines = _unfold(response)
    assert lines[0] == "BEGIN:VCALENDAR" and "END:VCALENDAR" in lines
    assert f"UID:gig-{gig.pk}@bordpro" in lines
    assert f"DTSTART;VALUE=DATE:{TOMORROW:%Y%m%d}" in lines  # no time known: all day
    assert "STATUS:CONFIRMED" in lines or "STATUS:TENTATIVE" in lines
    assert any(line.startswith("URL:http") and f"/{gig.pk}/" in line for line in lines)


def test_a_known_time_makes_a_timed_event_in_utc(client, tenant):
    gig = GigFactory(
        tenant=tenant,
        date=datetime.date(2027, 7, 14),  # summer: Paris is UTC+2
        get_in_time=datetime.time(16, 0),
        performance_time=datetime.time(21, 0),
    )
    gig.show.duration_minutes = 90
    gig.show.save()
    lines = _unfold(client.get(reverse("gigs:ical", args=[gig.pk])))
    assert "DTSTART:20270714T140000Z" in lines
    assert "DTEND:20270714T203000Z" in lines  # 21:00 + 90 min = 22:30 Paris


def test_an_option_is_tentative(client, tenant):
    gig = GigFactory(tenant=tenant, status=Gig.Status.OPTION)
    assert "STATUS:TENTATIVE" in _unfold(client.get(reverse("gigs:ical", args=[gig.pk])))


def test_the_file_never_contains_money(client, tenant):
    gig = GigFactory(tenant=tenant, price="1234.56", conditions="Cachet net 999")
    content = client.get(reverse("gigs:ical", args=[gig.pk])).content.decode()
    assert "1234" not in content and "999" not in content


def test_the_whole_calendar_has_upcoming_dates_but_not_cancelled_or_past_ones(client, tenant):
    upcoming = GigFactory(tenant=tenant, date=TOMORROW)
    GigFactory(tenant=tenant, date=TOMORROW, status=Gig.Status.CANCELLED)
    GigFactory(tenant=tenant, date=datetime.date.today() - datetime.timedelta(days=3))
    response = client.get(reverse("gigs:calendar-export"))
    lines = _unfold(response)
    assert [line for line in lines if line.startswith("UID:")] == [f"UID:gig-{upcoming.pk}@bordpro"]
    assert "mes-dates.ics" in response["Content-Disposition"]


def test_an_empty_calendar_is_still_a_valid_file(client, tenant):
    lines = _unfold(client.get(reverse("gigs:calendar-export")))
    assert lines[:2] == ["BEGIN:VCALENDAR", "VERSION:2.0"] and "BEGIN:VEVENT" not in lines


def test_another_structures_dates_are_never_exported(client, tenant):
    other = GigFactory(date=TOMORROW)
    assert client.get(reverse("gigs:ical", args=[other.pk])).status_code == 404
    content = client.get(reverse("gigs:calendar-export")).content.decode()
    assert f"gig-{other.pk}@" not in content


def test_both_downloads_need_a_login(client):
    gig = GigFactory()
    for url in (reverse("gigs:ical", args=[gig.pk]), reverse("gigs:calendar-export")):
        response = client.get(url)
        assert response.status_code == 302 and "login" in response["Location"]


def test_texts_are_escaped_and_long_lines_are_folded_under_75_octets():
    assert escape("a,b;c\\d\ne") == "a\\,b\\;c\\\\d\\ne"
    folded = fold("DESCRIPTION:" + "é" * 100)
    assert all(len(part.encode()) <= 75 for part in folded.split("\r\n"))
    assert folded.replace("\r\n ", "") == "DESCRIPTION:" + "é" * 100


def test_the_buttons_are_offered(client, tenant):
    gig = GigFactory(tenant=tenant)
    assert (
        reverse("gigs:ical", args=[gig.pk])
        in client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()
    )
    assert reverse("gigs:calendar-export") in client.get(reverse("gigs:calendar")).content.decode()
    gig.status = Gig.Status.CANCELLED
    gig.save()
    assert (
        reverse("gigs:ical", args=[gig.pk])
        not in client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()
    )
