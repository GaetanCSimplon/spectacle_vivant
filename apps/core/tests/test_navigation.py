import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def _login(client):
    client.force_login(MembershipFactory().user)


def test_navigation_is_hidden_when_logged_out(client):
    response = client.get(reverse("account_login"))

    assert "Navigation principale" not in response.content.decode()


def test_navigation_links_are_shown_when_logged_in(client):
    _login(client)

    content = client.get(reverse("home")).content.decode()

    assert content.count("Navigation principale") == 2  # header (desktop) + burger menu (phone)
    assert reverse("gigs:list") in content
    assert reverse("addressbook:promoter-list") in content


@pytest.mark.parametrize(
    ("url_name", "label"),
    [
        ("home", "Accueil"),
        ("gigs:list", "Mes dates"),
        ("gigs:wizard-show", "Mes dates"),
        ("catalog:show-list", "Spectacles"),
        ("addressbook:promoter-list", "Contacts"),
        ("addressbook:venue-list", "Contacts"),
        ("addressbook:contact-list", "Contacts"),
        ("tenants:profile", "Bòrd"),
    ],
)
def test_current_page_is_marked_active(client, url_name, label):
    _login(client)

    content = client.get(reverse(url_name)).content.decode()

    # One active link per navigation (header + burger menu), and it is the right one.
    assert content.count('aria-current="page"') == 2
    assert f'aria-current="page"\n  >{label}</a>' in content


def test_phone_navigation_is_a_burger_menu_without_a_bottom_bar(client):
    """At 375 px five labels did not fit in a bottom bar ("Bòrd" was cut off)."""
    _login(client)

    content = client.get(reverse("home")).content.decode()

    assert 'aria-label="Menu"' in content and "<details" in content
    assert "fixed inset-x-0 bottom-0" not in content
    menu = content.split("<details", 1)[1].split("</details>", 1)[0]
    for label in ("Accueil", "Mes dates", "Spectacles", "Contacts", "Bòrd"):
        assert label in menu
    assert "Se déconnecter" in menu and reverse("account_logout") in menu


def test_list_headers_use_a_round_plus_on_a_phone_and_keep_the_label_for_screen_readers(client):
    _login(client)
    for name, label in (
        ("addressbook:promoter-list", "Nouvel organisateur"),
        ("addressbook:venue-list", "Nouveau lieu"),
        ("catalog:show-list", "Nouveau spectacle"),
        ("gigs:list", "Nouvelle date"),
        ("tenants:person-list", "Ajouter"),
        ("addressbook:contact-list", "Nouveau contact"),
    ):
        content = client.get(reverse(name)).content.decode()
        assert f'aria-label="{label}"' in content, name
        assert f'<span class="hidden sm:inline">+ {label}</span>' in content, name


def test_the_home_cards_grid_has_an_explicit_single_column_on_a_phone(client):
    """Without grid-cols-1 a long venue name made the cards 843 px wide on a 375 px screen."""
    membership = MembershipFactory()
    client.force_login(membership.user)
    GigFactory(tenant=membership.tenant)

    content = client.get(reverse("home")).content.decode()

    assert 'class="grid grid-cols-1 gap-4 md:grid-cols-2"' in content
