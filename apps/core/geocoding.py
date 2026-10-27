"""Address -> coordinates, for the map preview of a roadmap (Nominatim, from OpenStreetMap).

One call when an address is saved, never when a page is read. No account and no key; the usage
policy asks for an identifying User-Agent and at most one request per second, which a person
typing addresses by hand never approaches. Nothing here may stop a save: any failure gives
`Geocode("error")` and the page simply has no map. The address is never written to the logs.
"""

import json
import logging
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
    params = urllib.parse.urlencode({"q": query, "format": "jsonv2", "limit": 1})
    request = urllib.request.Request(  # noqa: S310  (the URL comes from our settings)
        f"{settings.GEOCODING_URL}?{params}",
        headers={"User-Agent": settings.GEOCODING_USER_AGENT, "Accept-Language": "fr"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            results = json.load(response)
        if not results:
            return Geocode("not_found")
        # Six decimals are about 10 cm: plenty, and what the columns hold.
        latitude = Decimal(str(results[0]["lat"])).quantize(Decimal("0.000001"))
        longitude = Decimal(str(results[0]["lon"])).quantize(Decimal("0.000001"))
    except Exception as error:  # noqa: BLE001  (network, HTTP, JSON: none may block a save)
        logger.warning("Geocoding failed: %s", type(error).__name__)
        return Geocode("error")
    return Geocode("found", latitude, longitude)


def embed_url(latitude, longitude, delta=Decimal("0.006")):
    """The OpenStreetMap embeddable map centred on a point, with a marker."""
    west, east = longitude - delta, longitude + delta
    south, north = latitude - delta, latitude + delta
    return (
        "https://www.openstreetmap.org/export/embed.html"
        f"?bbox={west},{south},{east},{north}&layer=mapnik&marker={latitude},{longitude}"
    )
