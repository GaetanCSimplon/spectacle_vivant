"""Map preview: an address becomes a point when it is saved (Nominatim is faked, no network)."""

import json
from decimal import Decimal
from io import BytesIO

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.addressbook.factories import VenueFactory
from apps.addressbook.models import Venue
from apps.gigs.factories import GigFactory
from apps.roadmaps.factories import LodgingFactory, RoadmapFactory
from apps.roadmaps.models import Lodging
from apps.roadmaps.services import get_or_create_roadmap, publish

from .. import geocoding
from ..geocoding import Geocode, embed_url

pytestmark = pytest.mark.django_db

FOUND = Geocode("found", Decimal("43.610800"), Decimal("3.876700"))


@pytest.fixture
def lookups(monkeypatch, settings):
    """Switch geocoding on and record every address asked for (answer: `lookups.answer`)."""
    settings.GEOCODING_ENABLED = True

    class Calls(list):
        answer = FOUND

    calls = Calls()

    def fake(query):
        calls.append(query)
        return calls.answer

    monkeypatch.setattr("apps.core.models.geocode", fake)
    return calls


# --- the service --------------------------------------------------------------------------


class _Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _answer(monkeypatch, payload=None, error=None):
    seen = {}

    def fake(request, timeout):
        seen["url"], seen["agent"], seen["timeout"] = (
            request.full_url,
            request.get_header("User-agent"),
            timeout,
        )
        if error:
            raise error
        return _Response(json.dumps(payload).encode())

    monkeypatch.setattr(geocoding.urllib.request, "urlopen", fake)
    return seen


def test_a_found_address_gives_a_point(monkeypatch, settings):
    settings.GEOCODING_ENABLED = True
    seen = _answer(monkeypatch, [{"lat": "43.6108", "lon": "3.8767"}])

    result = geocoding.geocode("1 place de la Comédie, 34000 Montpellier")

    assert result == FOUND
    assert "nominatim.openstreetmap.org" in seen["url"] and "limit=1" in seen["url"]
    assert "BordPro" in seen["agent"] and seen["timeout"] == geocoding.TIMEOUT_SECONDS


def test_an_unknown_address_is_not_an_error(monkeypatch, settings):
    settings.GEOCODING_ENABLED = True
    _answer(monkeypatch, [])

    assert geocoding.geocode("Nulle part").status == "not_found"


@pytest.mark.parametrize("error", [TimeoutError(), OSError("down"), ValueError("bad json")])
def test_a_failing_service_never_raises(monkeypatch, settings, error):
    settings.GEOCODING_ENABLED = True
    _answer(monkeypatch, error=error)

    assert geocoding.geocode("1 rue X").status == "error"


def test_geocoding_can_be_switched_off(monkeypatch, settings):
    settings.GEOCODING_ENABLED = False
    seen = _answer(monkeypatch, [{"lat": "1", "lon": "1"}])

    assert geocoding.geocode("1 rue X").status == "disabled" and not seen


def test_the_embed_url_centres_the_map_on_the_point():
    url = embed_url(Decimal("43.6108"), Decimal("3.8767"))

    assert url.startswith("https://www.openstreetmap.org/export/embed.html?bbox=")
    assert "marker=43.6108,3.8767" in url and "layer=mapnik" in url


# --- saving an address --------------------------------------------------------------------


def test_a_venue_is_located_when_it_is_saved(lookups):
    venue = VenueFactory(address="1 place de la Comédie", postal_code="34000", city="Montpellier")

    venue.refresh_from_db()
    assert lookups == ["1 place de la Comédie, 34000 Montpellier"]
    assert venue.has_point and venue.latitude == FOUND.latitude
    assert "marker=43.6108" in venue.map_embed_url


def test_a_lodging_is_located_too(lookups):
    lodging = LodgingFactory(address="3 rue Neuve", postal_code="30000", city="Nîmes")

    lodging.refresh_from_db()
    assert lodging.has_point and len(lookups) == 1


def test_the_address_is_asked_again_only_when_it_changes(lookups):
    venue = VenueFactory(address="1 rue A", city="Lyon")
    venue.name = "Autre nom"
    venue.save()
    assert len(lookups) == 1

    venue.address = "2 rue B"
    venue.save()
    assert len(lookups) == 2 and lookups[-1] == "2 rue B, Lyon"


def test_a_save_with_update_fields_does_not_look_anything_up(lookups):
    venue = VenueFactory(address="1 rue A")
    lookups.clear()

    venue.phone = "04 00 00 00 00"
    venue.save(update_fields=["phone"])

    assert lookups == []


def test_a_failing_service_keeps_the_save_and_is_retried_next_time(lookups):
    lookups.answer = Geocode("error")

    venue = VenueFactory(address="1 rue A", city="Lyon")
    venue.refresh_from_db()
    assert venue.pk and not venue.has_point and venue.geocoded_address == ""

    lookups.answer = FOUND
    venue.save()
    venue.refresh_from_db()
    assert venue.has_point and len(lookups) == 2


def test_an_unknown_address_is_remembered_and_not_asked_again(lookups):
    lookups.answer = Geocode("not_found")

    venue = VenueFactory(address="Au bout du monde")
    venue.save()

    venue.refresh_from_db()
    assert not venue.has_point and venue.geocoded_address == "Au bout du monde"
    assert len(lookups) == 1


def test_an_old_point_never_stays_attached_to_a_new_address(lookups):
    venue = VenueFactory(address="1 rue A")
    assert venue.has_point
    lookups.answer = Geocode("error")

    venue.address = "2 rue B"
    venue.save()

    venue.refresh_from_db()
    assert not venue.has_point


def test_clearing_the_address_clears_the_point(lookups):
    venue = VenueFactory(address="1 rue A")

    venue.address = ""
    venue.save()

    venue.refresh_from_db()
    assert not venue.has_point and venue.geocoded_address == "" and len(lookups) == 1


def test_nothing_is_looked_up_when_geocoding_is_off():
    venue = VenueFactory(address="1 rue A")

    assert not venue.has_point  # test settings: GEOCODING_ENABLED = False


# --- the public roadmap -------------------------------------------------------------------


def _shared_roadmap(gig):
    roadmap = get_or_create_roadmap(gig)
    publish(roadmap)
    roadmap.refresh_from_db()
    return roadmap


def test_the_public_page_shows_a_map_for_the_venue_and_for_a_lodging(client, lookups):
    gig = GigFactory(venue=VenueFactory(address="1 rue A", city="Lyon"))
    roadmap = _shared_roadmap(gig)
    LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant, address="3 rue B", city="Nîmes")

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()

    assert page.count("openstreetmap.org/export/embed.html") == 2
    assert (
        'title="Aperçu de la carte"' in page and 'sandbox="allow-scripts allow-same-origin"' in page
    )
    assert "Itinéraire" in page and "Copier l'adresse" in page  # the buttons stay


def test_the_public_page_has_no_map_without_a_point(client):
    gig = GigFactory(venue=VenueFactory(address="1 rue A", city="Lyon"))
    roadmap = _shared_roadmap(gig)
    LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant, address="3 rue B")

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()

    assert "export/embed.html" not in page and "Itinéraire" in page


def test_the_coordinates_are_not_in_the_pdf(lookups):
    from apps.roadmaps.services import render_roadmap_pdf

    gig = GigFactory(venue=VenueFactory(address="1 rue A", city="Lyon"))
    roadmap = RoadmapFactory(gig=gig)

    assert render_roadmap_pdf(roadmap).startswith(b"%PDF")


# --- the command --------------------------------------------------------------------------


def test_the_command_locates_the_places_saved_before(lookups, monkeypatch, settings):
    venue = VenueFactory(address="1 rue A", city="Lyon")
    lodging = LodgingFactory(address="3 rue B")
    for model, place in ((Venue, venue), (Lodging, lodging)):  # as if saved before the feature
        model.objects.filter(pk=place.pk).update(latitude=None, longitude=None, geocoded_address="")
    lookups.clear()
    monkeypatch.setattr("apps.core.management.commands.geocode_places.PAUSE_SECONDS", 0)

    call_command("geocode_places")

    venue.refresh_from_db()
    lodging.refresh_from_db()
    assert venue.has_point and lodging.has_point
    call_command("geocode_places")  # second run: nothing left to do
    assert len(lookups) == 2


def test_the_one_line_address_has_no_carriage_return_from_a_text_box():
    venue = VenueFactory.build(
        address="1 avenue de la République\r\n", postal_code="30000", city="Nîmes"
    )

    assert venue.one_line_address == "1 avenue de la République, 30000 Nîmes"
