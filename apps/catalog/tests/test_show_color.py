"""The colour of a show (SPE-03): a short palette that respects the charter."""

import pytest
from django.urls import reverse

from apps.catalog import colors
from apps.catalog.factories import ShowFactory
from apps.core.tests.test_brand_contrast import contrast
from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db

# The colours that mean something else in the charter: states, and the main action.
RESERVED = {"#1F6B4A", "#E3A21A", "#8E1F3F", "#FF695B"}


def test_every_colour_can_be_seen_on_a_white_page():
    for key, (code, _name) in colors.PALETTE.items():
        assert contrast("#ffffff", code) >= 3, key


def test_no_colour_is_a_state_colour_or_the_coral_of_the_main_action():
    codes = {code.upper() for code, _name in colors.PALETTE.values()}
    assert not codes & RESERVED


def test_the_colours_are_distinct_and_have_a_name():
    codes = [code for code, _name in colors.PALETTE.values()]
    names = [str(name) for _code, name in colors.PALETTE.values()]
    assert len(set(codes)) == len(codes) == len(names) == len(set(names))
    assert len(codes) <= 8


def test_an_unknown_key_has_no_colour():
    assert colors.hex_of("") == "" and colors.hex_of("nope") == ""


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {"title": "Nuits d'été", "duration_minutes": "75", "default_price": "800.00"}
    return {**data, **overrides}


def test_the_form_offers_the_named_colours_and_keeps_the_choice(client):
    tenant = _login(client)

    page = client.get(reverse("catalog:show-create")).content.decode()
    client.post(reverse("catalog:show-create"), _payload(color="ocean"))

    assert "Océan" in page and "Prune" in page
    from apps.catalog.models import Show

    show = Show.objects.get(tenant=tenant)
    assert show.color == "ocean" and show.color_hex == "#007299" and show.color_name == "Océan"


def test_a_colour_outside_the_palette_is_refused(client):
    tenant = _login(client)

    response = client.post(reverse("catalog:show-create"), _payload(color="#ff0000"))

    from apps.catalog.models import Show

    assert response.status_code == 200 and not Show.objects.filter(tenant=tenant).exists()


def test_the_colour_is_optional(client):
    _login(client)

    response = client.post(reverse("catalog:show-create"), _payload())

    assert response.status_code == 302


def test_the_dot_shows_in_the_lists_and_pages_of_a_coloured_show(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant, color="violet")
    gig = GigFactory(tenant=tenant, show=show)

    for name, args in (
        ("gigs:list", []),
        ("gigs:detail", [gig.pk]),
        ("catalog:show-list", []),
        ("catalog:show-detail", [show.pk]),
    ):
        page = client.get(reverse(name, args=args)).content.decode()
        assert "background-color: #6A3F9C" in page, name


def test_no_dot_for_a_show_without_colour(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)
    GigFactory(tenant=tenant, show=show)

    assert "background-color" not in client.get(reverse("gigs:list")).content.decode()


def test_the_dot_is_decoration_the_title_is_always_written(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant, title="Les Nocturnes", color="plum")
    GigFactory(tenant=tenant, show=show)

    page = client.get(reverse("catalog:show-detail", args=[show.pk])).content.decode()

    import re

    assert re.search(r'aria-hidden="true"></span>\s*Les Nocturnes', page)
