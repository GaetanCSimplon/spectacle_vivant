import pytest
from django.urls import reverse

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

    assert content.count("Navigation principale") == 2  # top bar + bottom bar
    assert reverse("gigs:list") in content
    assert reverse("gigs:wizard-show") in content


@pytest.mark.parametrize(
    ("url_name", "label"),
    [
        ("home", "Accueil"),
        ("gigs:list", "Mes dates"),
        ("gigs:wizard-show", "Nouvelle date"),
        ("tenants:profile", "Ma structure"),
    ],
)
def test_current_page_is_marked_active(client, url_name, label):
    _login(client)

    content = client.get(reverse(url_name)).content.decode()

    # One active link per bar (top + bottom), and it is the right one.
    assert content.count('aria-current="page"') == 2
    assert f'aria-current="page"\n  >{label}</a>' in content
