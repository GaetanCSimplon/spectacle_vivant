"""iCalendar (.ics) export of the gigs: opens in Google Agenda, Apple Calendrier, Outlook.

Only what the whole team may see goes in: show, venue, organiser, times, status. Never the
price, the fee or any money (a calendar file is easily forwarded). Written by hand: the format
is small and a dependency would be more to maintain.
"""

import datetime
from zoneinfo import ZoneInfo

from django.http import HttpResponse
from django.utils import timezone

from .models import Gig

PARIS = ZoneInfo("Europe/Paris")
UTC = datetime.UTC
PRODID = "-//Bord Pro//Dates//FR"
# Without a show duration, the calendar still needs an end: one hour is a neutral default.
DEFAULT_MINUTES = 60


def escape(value):
    """A text value as iCalendar wants it (RFC 5545 §3.3.11)."""
    value = str(value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")


def fold(line):
    """Cut a line at 75 octets, continuation lines start with a space (RFC 5545 §3.1)."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, current = [], b""
    limit = 75
    for char in line:
        encoded = char.encode("utf-8")
        if len(current) + len(encoded) > limit:
            parts.append(current.decode("utf-8"))
            current, limit = b"", 74  # the leading space counts
        current += encoded
    parts.append(current.decode("utf-8"))
    return "\r\n ".join(parts)


def _stamp(value):
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _at(gig, moment):
    return datetime.datetime.combine(gig.date, moment, tzinfo=PARIS)


def _times(gig):
    return [
        (label, moment)
        for label, moment in (
            ("Arrivée", gig.get_in_time),
            ("Balances", gig.soundcheck_time),
            ("Concert", gig.performance_time),
        )
        if moment
    ]


def _description(gig, url):
    lines = [f"Organisateur : {gig.promoter.name}", f"Statut : {gig.get_status_display()}"]
    lines += [f"{label} : {moment:%H:%M}" for label, moment in _times(gig)]
    lines.append(url)
    return "\n".join(lines)


def _lines(gig, url, now):
    """The VEVENT of a gig: timed when a time is known, otherwise all day."""
    times = _times(gig)
    lines = [
        "BEGIN:VEVENT",
        f"UID:gig-{gig.pk}@bordpro",
        f"DTSTAMP:{_stamp(now)}",
    ]
    if times:
        start = _at(gig, min(moment for _label, moment in times))
        # The show ends at the performance (or the last known time) plus its length.
        last = _at(gig, max(moment for _label, moment in times))
        minutes = gig.show.duration_minutes or DEFAULT_MINUTES
        end = max(last + datetime.timedelta(minutes=minutes), start + datetime.timedelta(hours=1))
        lines += [f"DTSTART:{_stamp(start)}", f"DTEND:{_stamp(end)}"]
    else:
        lines += [
            f"DTSTART;VALUE=DATE:{gig.date:%Y%m%d}",
            f"DTEND;VALUE=DATE:{gig.date + datetime.timedelta(days=1):%Y%m%d}",
        ]
    place = ", ".join(part for part in (gig.venue.name, gig.venue.one_line_address) if part)
    status = "TENTATIVE" if gig.status == Gig.Status.OPTION else "CONFIRMED"
    lines += [
        f"SUMMARY:{escape(f'{gig.show.title} — {gig.venue.name}')}",
        f"LOCATION:{escape(place)}",
        f"DESCRIPTION:{escape(_description(gig, url))}",
        f"URL:{url}",
        f"STATUS:{status}",
        "END:VEVENT",
    ]
    return lines


def build(gigs, url_for):
    """The whole calendar. `url_for(gig)` gives the absolute address of a gig's page."""
    now = timezone.now()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN"]
    for gig in gigs:
        if gig.status != Gig.Status.CANCELLED:
            lines += _lines(gig, url_for(gig), now)
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(line) for line in lines) + "\r\n"


def response(content, filename):
    result = HttpResponse(content, content_type="text/calendar; charset=utf-8")
    result["Content-Disposition"] = f'attachment; filename="{filename}"'
    result["X-Content-Type-Options"] = "nosniff"
    return result
