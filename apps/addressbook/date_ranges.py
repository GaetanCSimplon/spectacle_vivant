"""The dates an organiser usually programmes, as ranges that come back every year (ORG-03).

A range has no year: "10/07 au 25/07" is every 10 to 25 July. Stored as
`{"start": "07-10", "end": "07-25"}` (month-day, so it sorts and survives a change of format).
A range may cross the new year ("15/12 au 05/01").
"""

import datetime
import re

from django.core.exceptions import ValidationError
from django.utils.formats import date_format
from django.utils.translation import gettext as _

MAX_RANGES = 3
# 2000 is a leap year: the 29th of February is accepted, since the range comes back each year.
_REFERENCE_YEAR = 2000
_DAY_MONTH = r"(\d{1,2})\s*[/.-]\s*(\d{1,2})"
_RANGE = re.compile(rf"^\s*(?:du\s+)?{_DAY_MONTH}\s*(?:au|à|-|–|—)\s*{_DAY_MONTH}\s*$", re.I)


def _day_month(day, month):
    day, month = int(day), int(month)
    try:
        datetime.date(_REFERENCE_YEAR, month, day)
    except ValueError:
        raise ValidationError(
            _("Le %(day)s/%(month)s n'existe pas dans le calendrier.")
            % {"day": f"{day:02d}", "month": f"{month:02d}"}
        ) from None
    return f"{month:02d}-{day:02d}"


def parse_range(text):
    """ "10/07 au 25/07" -> {"start": "07-10", "end": "07-25"}; "" -> None."""
    text = (text or "").strip()
    if not text:
        return None
    match = _RANGE.match(text)
    if not match:
        raise ValidationError(_("Écrivez la plage ainsi : 10/07 au 25/07 (jour/mois)."))
    d1, m1, d2, m2 = match.groups()
    return {"start": _day_month(d1, m1), "end": _day_month(d2, m2)}


def _date(month_day):
    month, day = month_day.split("-")
    return datetime.date(_REFERENCE_YEAR, int(month), int(day))


def input_text(date_range):
    """What the field shows back: "10/07 au 25/07"."""
    start, end = _date(date_range["start"]), _date(date_range["end"])
    return f"{start:%d/%m} au {end:%d/%m}"


def label(date_range):
    """For a page: "du 10 juillet au 25 juillet"."""
    start, end = _date(date_range["start"]), _date(date_range["end"])
    return _("du %(start)s au %(end)s") % {
        "start": date_format(start, "j F"),
        "end": date_format(end, "j F"),
    }
