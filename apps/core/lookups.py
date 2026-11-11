"""Two public APIs of the French State that save typing (recette n°1, ORG-01 and ORG-02).

- "Recherche d'entreprises": a SIRET or a name -> the legal data of the company.
- "Découpage administratif": a postal code -> the communes it covers.

Free, no account, no key. Only the text the user typed leaves the server, and it is never written
to the logs. Like the geocoding, nothing here may stop anyone: any failure gives an empty answer
with `available=False` and the page keeps its fields to be typed by hand.
"""

import hashlib
import json
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache

from apps.tenants.validators import normalize_code_ape, normalize_siret

from .addresses import department_from_postal_code

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 3
MAX_RESULTS = 5
MIN_QUERY_LENGTH = 3
MAX_QUERY_LENGTH = 100
CACHE_SECONDS = 6 * 60 * 60
# Per person and per minute: far above what typing needs, far below the limit of the APIs.
RATE_LIMIT = {"companies": 20, "communes": 60}


@dataclass(frozen=True)
class Company:
    name: str
    siret: str
    code_ape: str
    street: str
    postal_code: str
    city: str
    department: str
    vat_number: str


@dataclass(frozen=True)
class CompanySearch:
    available: bool = True
    too_short: bool = False
    companies: list[Company] = field(default_factory=list)


@dataclass(frozen=True)
class CommuneSearch:
    available: bool = True
    names: list[str] = field(default_factory=list)


def _fetch_json(url, params):
    request = urllib.request.Request(  # noqa: S310  (the URL comes from our settings)
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": settings.GEOCODING_USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
        return json.load(response)


def _cached(scope, query, build):
    """The answer of `build()` kept a few hours per query (a failure is never kept)."""
    key = f"lookup:{scope}:{hashlib.sha256(query.encode()).hexdigest()}"
    found = cache.get(key)
    if found is not None:
        return found
    answer = build()
    if answer.available:
        cache.set(key, answer, CACHE_SECONDS)
    return answer


def allowed(user_id, scope):
    """False once a person has made too many look-ups this minute."""
    key = f"lookup-rate:{scope}:{user_id}"
    cache.add(key, 0, timeout=60)
    try:
        return cache.incr(key) <= RATE_LIMIT[scope]
    except ValueError:  # the key expired between the two calls
        cache.set(key, 1, timeout=60)
        return True


def vat_number_from_siren(siren):
    """The French VAT number a SIREN gives: "FR", a two-digit key, then the SIREN."""
    if not re.fullmatch(r"\d{9}", siren or ""):
        return ""
    return f"FR{(12 + 3 * (int(siren) % 97)) % 97:02d}{siren}"


def _street(place):
    """ "12 RUE DES ARTS" from the parts of the address, without the postal code and the town."""
    parts = [
        place.get("numero_voie"),
        place.get("indice_repetition"),
        place.get("type_voie"),
        place.get("libelle_voie"),
    ]
    street = " ".join(str(part) for part in parts if part)
    if street:
        complement = place.get("complement_adresse")
        return f"{complement}, {street}" if complement else street
    # No detail: the one-line address, minus its end "34000 MONTPELLIER".
    line = place.get("adresse") or ""
    ending = f"{place.get('code_postal') or ''} {place.get('libelle_commune') or ''}".strip()
    return line.removesuffix(ending).strip(" ,") if ending else line


def _place(result, wanted_siret):
    """The establishment asked for (a SIRET), else the head office."""
    for establishment in result.get("matching_etablissements") or []:
        if wanted_siret and establishment.get("siret") == wanted_siret:
            return establishment
    return result.get("siege") or {}


def _company(result, wanted_siret):
    place = _place(result, wanted_siret)
    siren = result.get("siren") or ""
    postal_code = place.get("code_postal") or ""
    return Company(
        name=(result.get("nom_complet") or result.get("nom_raison_sociale") or "").strip(),
        siret=normalize_siret(place.get("siret") or ""),
        code_ape=normalize_code_ape(place.get("activite_principale") or ""),
        street=_street(place),
        postal_code=postal_code,
        city=(place.get("libelle_commune") or "").title(),
        department=department_from_postal_code(postal_code),
        vat_number=vat_number_from_siren(siren),
    )


def search_companies(query):
    """Up to five companies matching a SIRET, a SIREN or a name; see `CompanySearch`."""
    query = " ".join((query or "").split())[:MAX_QUERY_LENGTH]
    if len(query) < MIN_QUERY_LENGTH:
        return CompanySearch(too_short=True)
    if not settings.LOOKUPS_ENABLED:
        return CompanySearch(available=False)
    digits = normalize_siret(query)
    wanted_siret = digits if re.fullmatch(r"\d{14}", digits) else ""
    asked = digits if re.fullmatch(r"\d{9,14}", digits) else query

    def build():
        try:
            data = _fetch_json(
                settings.COMPANY_SEARCH_URL, {"q": asked, "per_page": MAX_RESULTS, "page": 1}
            )
            companies = [_company(result, wanted_siret) for result in data["results"][:MAX_RESULTS]]
        except Exception as error:  # noqa: BLE001  (network, HTTP, JSON: none may block a page)
            logger.warning("Company search failed: %s", type(error).__name__)
            return CompanySearch(available=False)
        return CompanySearch(companies=[c for c in companies if c.name and c.siret])

    return _cached("companies", asked, build)


def search_communes(postal_code):
    """The communes of a postal code (5 digits), sorted by name; see `CommuneSearch`."""
    code = (postal_code or "").replace(" ", "")
    if not re.fullmatch(r"\d{5}", code) or not settings.LOOKUPS_ENABLED:
        return CommuneSearch(available=settings.LOOKUPS_ENABLED)

    def build():
        try:
            data = _fetch_json(settings.COMMUNES_URL, {"codePostal": code, "fields": "nom"})
            names = sorted({item["nom"] for item in data if item.get("nom")})
        except Exception as error:  # noqa: BLE001
            logger.warning("Commune search failed: %s", type(error).__name__)
            return CommuneSearch(available=False)
        return CommuneSearch(names=names)

    return _cached("communes", code, build)
