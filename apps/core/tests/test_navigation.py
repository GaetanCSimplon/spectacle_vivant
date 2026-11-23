import re

import pytest
from django.urls import reverse

from apps.addressbook.tests.helpers import directory_url
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

    assert content.count("Navigation principale") == 2  # left column (desktop) + burger menu
    assert reverse("gigs:list") in content
    assert reverse("addressbook:directory") in content


@pytest.mark.parametrize(
    ("url_name", "label"),
    [
        ("home", "Accueil"),
        ("gigs:list", "Dates"),
        ("gigs:wizard-show", "Dates"),
        ("addressbook:directory", "Contacts"),
        ("tenants:social", "Social"),
        ("tenants:profile", "Bòrd"),
        ("bord-expenses", "Bòrd"),
        ("document-library", "Bòrd"),
    ],
)
def test_current_page_is_marked_active(client, url_name, label):
    _login(client)

    content = client.get(reverse(url_name)).content.decode()

    # One active link per navigation (header + burger menu), and it is the right one.
    assert content.count('aria-current="page"') == 2
    # The label follows the icon (burger menu) or the bullet (left column), inside the same link.
    active = rf'aria-current="page"\s*>(?:(?!</a>).)*?{label}</a>'
    assert re.search(active, content, re.S)


def test_phone_navigation_is_a_burger_menu_without_a_bottom_bar(client):
    """At 375 px five labels did not fit in a bottom bar ("Bòrd" was cut off)."""
    _login(client)

    content = client.get(reverse("home")).content.decode()

    assert 'aria-label="Menu"' in content and "<details" in content
    assert "fixed inset-x-0 bottom-0" not in content
    menu = content.split("<details", 1)[1].split("</details>", 1)[0]
    for label in ("Accueil", "Bòrd", "Dates", "Social", "Contacts"):
        assert label in menu
    assert "Se déconnecter" in menu and reverse("account_logout") in menu


def test_list_headers_use_a_round_plus_on_a_phone_and_keep_the_label_for_screen_readers(client):
    _login(client)
    for name, label in (
        (directory_url("promoter"), "Nouvel organisateur"),
        (directory_url("venue"), "Nouveau lieu"),
        ("catalog:show-list", "Nouveau spectacle"),
        ("gigs:list", "Nouvelle date"),
        ("tenants:person-list", "Ajouter"),
        (directory_url("contact"), "Nouveau contact"),
    ):
        content = client.get(name if name.startswith("/") else reverse(name)).content.decode()
        assert f'aria-label="{label}"' in content, name
        assert f'<span class="hidden sm:inline">+ {label}</span>' in content, name


def test_the_home_cards_grid_has_an_explicit_single_column_on_a_phone(client):
    """Without grid-cols-1 a long venue name made the cards 843 px wide on a 375 px screen."""
    membership = MembershipFactory()
    client.force_login(membership.user)
    GigFactory(tenant=membership.tenant)

    content = client.get(reverse("home")).content.decode()

    assert 'class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"' in content


def test_desktop_navigation_is_a_column_on_the_left_and_the_burger_stays_on_a_phone(client):
    _login(client)

    content = client.get(reverse("home")).content.decode()
    aside = content.split("<aside")[1].split("</aside>")[0]
    header = content.split("<header")[1].split("</header>")[0]

    # The column: hidden below 1024 px, then a fixed column with the links and the log-out.
    assert content.index("<aside") < content.index("<main")
    assert 'class="hidden ' in aside and "lg:flex" in aside and "lg:w-60" in aside
    assert reverse("gigs:list") in aside and reverse("account_logout") in aside
    for label in ("Accueil", "Bòrd", "Dates", "Social", "Contacts"):
        assert label in aside
    # The top bar is for phones and tablets only, and keeps the burger menu.
    assert "lg:hidden" in content.split("<header")[1].split(">")[0]
    assert 'aria-label="Menu"' in header and "<details" in header
    assert reverse("gigs:list") in header and reverse("account_logout") in header


def test_the_column_shows_the_name_of_the_structure(client):
    membership = MembershipFactory(tenant__name="Compagnie du Soleil")
    client.force_login(membership.user)

    aside = client.get(reverse("home")).content.decode().split("<aside")[1].split("</aside>")[0]

    assert "Compagnie du Soleil" in aside


def test_logged_out_pages_have_no_column_and_keep_their_top_bar(client):
    content = client.get(reverse("account_login")).content.decode()

    assert "<aside" not in content
    header = content.split("<header")[1].split(">")[0]
    assert "lg:hidden" not in header
    assert "Bòrd Pro" in content


def test_bord_comes_right_after_the_home_page_and_is_in_bold(client):
    client.force_login(MembershipFactory().user)

    content = client.get(reverse("home")).content.decode()
    sidebar = content.split("<aside")[1].split("</aside>")[0]
    nav = sidebar.split("<nav")[1].split("</nav>")[0]
    nav = re.sub(r"<svg.*?</svg>", "", nav, flags=re.S)  # the icons are not part of the labels
    labels = re.findall(r">\s*(Accueil|Bòrd|Dates|Social|Contacts)</a>", nav)

    assert labels == ["Accueil", "Bòrd", "Dates", "Social", "Contacts"]
    bord_link = re.search(r"<a[^>]*>\s*Bòrd</a>", nav.replace("\n", " ")).group(0)
    assert "font-bold" in bord_link
    assert "font-bold" not in re.search(r"<a[^>]*>\s*Dates</a>", nav.replace("\n", " ")).group(0)


# --- "Retour" button (F-86) ----------------------------------------------------------------------


def test_every_signed_in_page_has_a_back_button_that_leads_to_my_dates_without_javascript(client):
    _login(client)

    for name in ("gigs:list", "addressbook:directory", "document-library"):
        content = client.get(reverse(name)).content.decode()

        assert content.count("data-back-button") == 1, name
        assert f'href="{reverse("gigs:list")}" data-back-button' in content, name


def test_the_home_has_no_back_button(client):
    _login(client)

    assert "data-back-button" not in client.get(reverse("home")).content.decode()


def test_signed_out_pages_have_no_back_button(client):
    assert "data-back-button" not in client.get(reverse("account_login")).content.decode()
    assert "data-back-button" not in client.get(reverse("legal-notice")).content.decode()


def test_the_back_button_only_uses_the_history_of_the_application(client):
    _login(client)

    content = client.get(reverse("gigs:list")).content.decode()

    assert "document.referrer.startsWith(location.origin)" in content
    assert "history.back()" in content
