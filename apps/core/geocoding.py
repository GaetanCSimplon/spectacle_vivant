"""Address -> coordinates, for the map preview of a roadmap (Nominatim, from OpenStreetMap).

One call when an address is saved, never when a page is read. No account and no key; the usage
policy asks for an identifying User-Agent and at most one request per second, which a person
typing addresses by hand never approaches. Nothing here may stop a save: any failure gives
`Geocode("error")` and the page simply has no map. The address is never written to the logs.
"""

import json
import logging
import re
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 3


@dataclass(frozen=True)
class Geocode:
    status: str  # "found", "not_found", "error" or "disabled"
    latitude: Decimal | None = None
    longitude: Decimal | None = None


def geocode(query):
    """Coordinates of an address typed on one line; see `Geocode`."""
    if not settings.GEOCODING_ENABLED:
        return Geocode("disabled")
    params = urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": 5, "addressdetails": 1}
    )
    request = urllib.request.Request(  # noqa: S310  (the URL comes from our settings)
        f"{settings.GEOCODING_URL}?{params}",
        headers={"User-Agent": settings.GEOCODING_USER_AGENT, "Accept-Language": "fr"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            results = json.load(response)
        best = _right_place(results, query)
        if best is None:
            return Geocode("not_found")
        # Six decimals are about 10 cm: plenty, and what the columns hold.
        latitude = Decimal(str(best["lat"])).quantize(Decimal("0.000001"))
        longitude = Decimal(str(best["lon"])).quantize(Decimal("0.000001"))
    except Exception as error:  # noqa: BLE001  (network, HTTP, JSON: none may block a save)
        logger.warning("Geocoding failed: %s", type(error).__name__)
        return Geocode("error")
    return Geocode("found", latitude, longitude)


POSTAL_CODE = re.compile(r"\b\d{5}\b")
LOCALITY_KEYS = ("city", "town", "village", "hamlet")


def _plain(text):
    """Lower case, no accents, single spaces: "Nîmes" and "NIMES" are the same town."""
    decomposed = unicodedata.normalize("NFKD", str(text))
    letters = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", letters.lower()).split())


def _in_the_address_town(result, query, postal_code):
    """The result is in the town or the postal code the address gives.

    OpenStreetMap's own postal codes are sometimes wrong (Place de la Comédie in Montpellier
    carries 34062, the commune code), so the town name counts as much as the code.
    """
    address = result.get("address", {})
    plain_query = f" {_plain(query)} "
    for key in LOCALITY_KEYS:
        town = _plain(address.get(key, ""))
        if town and f" {town} " in plain_query:
            return True
    return postal_code in re.split(r"[;,\s]+", str(address.get("postcode", "")))


def _right_place(results, query):
    """The result that is in the town of the address, if the address gives a postal code.

    A street name alone matches the same street in a neighbouring town ("Avenue de la
    République, 30000 Nîmes" finds Redessan, 30129): a map pointing at the wrong town is worse
    than no map, so such a result is refused. A result that names no town and no postal code
    at all (a monument) cannot be shown wrong: it is kept if nothing better.
    """
    wanted = POSTAL_CODE.search(query)
    if wanted is None:
        return results[0] if results else None
    unknown = None
    for result in results:
        address = result.get("address", {})
        if _in_the_address_town(result, query, wanted.group(0)):
            return result
        if not address.get("postcode") and not any(address.get(k) for k in LOCALITY_KEYS):
            unknown = unknown or result
    return unknown


def embed_url(latitude, longitude, delta=Decimal("0.006")):
    """The OpenStreetMap embeddable map centred on a point, with a marker."""
    west, east = longitude - delta, longitude + delta
    south, north = latitude - delta, latitude + delta
    return (
        "https://www.openstreetmap.org/export/embed.html"
        f"?bbox={west},{south},{east},{north}&layer=mapnik&marker={latitude},{longitude}"
    )
