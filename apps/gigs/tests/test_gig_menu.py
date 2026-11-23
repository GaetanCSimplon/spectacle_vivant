"""The navigation shows the four volets of a date while that date (or one of its pages) is open."""

import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _aside(client, url):
    content = client.get(url).content.decode()
    return content.split("<aside")[1].split("</aside>")[0]


def test_the_menu_of_a_date_lists_the_four_volets_in_the_sidebar_and_the_burger(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert content.count("Menu de la date") == 2  # column + burger
    aside = content.split("<aside")[1].split("</aside>")[0]
    for key, name in (
        ("contrats", "Contrats"),
        ("budget", "Budget"),
        ("social", "Social"),
        ("regie", "Régie"),
    ):
        assert f'href="{reverse("gigs:detail", args=[gig.pk])}#volet-{key}"' in aside
        assert f"brand/volet-{key}.svg" in aside
        assert name in aside
    assert gig.show.title in aside


def test_the_menu_comes_right_under_my_dates(client):
    gig = GigFactory(tenant=_login(client))

    aside = _aside(client, reverse("gigs:detail", args=[gig.pk]))

    assert aside.index("Dates") < aside.index("Menu de la date") < aside.index("Social")


def test_no_menu_outside_a_date(client):
    _login(client)

    for name in ("home", "gigs:list", "catalog:show-list", "tenants:profile"):
        assert "Menu de la date" not in client.get(reverse(name)).content.decode(), name


@pytest.mark.parametrize(
    ("url_name", "active"),
    [
        ("documents:contract-history", "contrats"),
        ("documents:billing", "budget"),
        ("finance:page", "budget"),
        ("roadmaps:editor", "regie"),
        ("gigs:detail", None),
    ],
)
def test_the_volet_of_the_page_being_shown_is_marked_current(client, url_name, active):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)

    aside = _aside(client, reverse(url_name, args=[gig.pk]))

    assert aside.count('aria-current="true"') == (1 if active else 0)
    if active:
        marked = aside.split('aria-current="true"')[0].rsplit("<a", 1)[1]
        assert f"#volet-{active}" in marked


def test_another_tenants_date_gives_no_menu(client):
    _login(client)
    gig = GigFactory(status=Gig.Status.CONFIRMED)

    response = client.get(reverse("gigs:detail", args=[gig.pk]))

    assert response.status_code == 404
    assert "Menu de la date" not in response.content.decode()
    assert gig.show.title not in response.content.decode()
