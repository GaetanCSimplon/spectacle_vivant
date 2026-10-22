"""The public presentation site: what a visitor sees before logging in."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db

SLOGAN = "Prenez le contrôle de votre tournée."
PAGES = ["home", "site-features", "site-contact"]


@pytest.mark.parametrize("name", PAGES)
def test_every_page_opens_without_an_account(client, name):
    response = client.get(reverse(name))

    assert response.status_code == 200
    assert 'name="viewport"' in response.content.decode()


def test_the_home_page_carries_the_slogan_and_the_charter_messages(client):
    content = client.get(reverse("home")).content.decode()

    assert SLOGAN in content
    assert "Contacts, dates, contrats, budgets et équipe : tout au même endroit." in content
    assert "Du premier contact au dernier cachet, gardez le fil." in content


def test_the_main_action_is_to_get_in_touch_not_to_sign_up(client):
    content = client.get(reverse("home")).content.decode()

    assert reverse("site-contact") in content
    assert reverse("account_signup") not in content


@pytest.mark.parametrize("name", PAGES)
def test_one_main_action_per_page_at_most(client, name):
    content = client.get(reverse(name)).content.decode()

    assert content.count("btn-primary") <= 1


def test_the_header_offers_the_sign_in_to_a_visitor(client):
    content = client.get(reverse("site-features")).content.decode()

    assert reverse("account_login") in content


def test_a_logged_in_user_gets_a_link_to_the_app_instead(client):
    client.force_login(MembershipFactory().user)

    content = client.get(reverse("site-features")).content.decode()

    assert "Mon espace" in content
    assert reverse("account_login") not in content


def test_a_logged_in_user_still_gets_the_dashboard_on_the_home_page(client):
    membership = MembershipFactory(tenant__name="Compagnie du Soleil")
    client.force_login(membership.user)

    response = client.get(reverse("home"))

    assert "Compagnie du Soleil" in response.content.decode()
    assert "site/home.html" not in [t.name for t in response.templates]


def test_the_contact_page_shows_the_address_from_the_settings(client, settings):
    settings.CONTACT_EMAIL = "bonjour@example.org"

    content = client.get(reverse("site-contact")).content.decode()

    assert 'href="mailto:bonjour@example.org"' in content


def test_the_legal_pages_are_linked_from_every_page(client):
    for name in PAGES:
        content = client.get(reverse(name)).content.decode()
        for legal in ("legal-notice", "legal-terms", "legal-privacy"):
            assert reverse(legal) in content


def test_the_legal_reminder_is_in_the_footer(client):
    content = client.get(reverse("home")).content.decode()

    assert "il ne remplace pas les obligations légales" in content


# --- search engines -------------------------------------------------------


@pytest.mark.parametrize("name", PAGES)
def test_pages_are_hidden_from_search_engines_until_the_site_is_ready(client, name):
    content = client.get(reverse(name)).content.decode()

    assert '<meta name="robots" content="noindex, nofollow">' in content


@pytest.mark.parametrize("name", PAGES)
def test_pages_can_be_indexed_when_the_setting_says_so(client, settings, name):
    settings.SITE_INDEXABLE = True

    content = client.get(reverse(name)).content.decode()

    assert "noindex" not in content


def test_robots_txt_blocks_everything_by_default(client):
    response = client.get(reverse("robots"))

    assert response["Content-Type"].startswith("text/plain")
    assert response.content.decode().splitlines() == ["User-agent: *", "Disallow: /"]


def test_robots_txt_opens_only_the_presentation_pages_when_indexable(client, settings):
    settings.SITE_INDEXABLE = True

    body = client.get(reverse("robots")).content.decode()

    assert "Allow: /$" in body and "Allow: /fonctionnalites/" in body
    assert "Disallow: /" in body
    assert "Sitemap: http://testserver/sitemap.xml" in body


def test_the_sitemap_lists_only_the_presentation_pages(client):
    body = client.get(reverse("sitemap")).content.decode()

    assert body.count("<loc>") == 3
    assert "/fonctionnalites/" in body and "/contact/" in body
    assert "/dates/" not in body and "/accounts/" not in body
