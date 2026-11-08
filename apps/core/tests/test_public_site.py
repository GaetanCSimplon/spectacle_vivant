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
    assert "Pour les artistes autoproduits" in content


def test_the_main_action_is_to_get_in_touch_not_to_sign_up(client):
    content = client.get(reverse("home")).content.decode()

    assert reverse("site-contact") in content
    assert "Demander une invitation" in content
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


# --- the home page: structure and honesty ----------------------------------------------------

import re  # noqa: E402

# Announced but not built: each of these may only appear next to the "en cours de développement"
# badge, on every page that mentions it.
NOT_BUILT = [
    "Radar",
    "Accès pour les artistes",
    "Signature électronique",
    "Facturation électronique",
    "Application installable",
]
BADGE = "En cours de développement"
# Things the site must not claim (not built, or not decided): the offers and prices are for later.
NEVER_CLAIMED = [
    "Commencer gratuitement",
    "Tarifs",
    "Découverte",
    "Pilotage",
    "Tournée Connectée",
    "Google Agenda",
    "Application mobile de gestion",
    "/inscription",
]


def _blocks(content):
    """Every card or step of a page: the unit that must carry its own badge."""
    return re.findall(r"<li class=\"(?:card|grid)[^>]*>.*?</li>", content, flags=re.DOTALL)


@pytest.mark.parametrize("name", PAGES)
def test_a_feature_not_built_yet_always_comes_with_its_badge(client, name):
    content = client.get(reverse(name)).content.decode()

    for feature in NOT_BUILT:
        for block in _blocks(content):
            if f">{feature}<" in block:
                assert BADGE in block, (name, feature)


def test_the_home_announces_what_is_coming_in_a_clearly_labelled_section(client):
    content = client.get(reverse("home")).content.decode()

    assert "Ce qui arrive." in content
    for feature in NOT_BUILT:
        assert feature in content
    assert content.count(BADGE) >= len(NOT_BUILT)


@pytest.mark.parametrize("name", PAGES)
def test_the_site_never_claims_what_is_not_built_or_not_decided(client, name):
    content = client.get(reverse(name)).content.decode()

    for claim in NEVER_CLAIMED:
        assert claim not in content, (name, claim)


@pytest.mark.parametrize("name", PAGES)
def test_the_name_is_spelled_as_the_charter_says_and_the_official_logo_is_used(client, name):
    content = client.get(reverse(name)).content.decode()

    assert "BÒRD PRO" not in content and "Bord Pro" not in content
    assert "brand/logo-capsule.svg" in content  # navy header: the capsule logo (charter 5)


def test_the_home_has_one_h1_that_is_the_slogan_and_labelled_sections(client):
    content = client.get(reverse("home")).content.decode()

    assert len(re.findall(r"<h1[ >]", content)) == 1
    assert re.search(r"<h1[^>]*>\s*" + re.escape(SLOGAN), content)
    for title_id in ("roles-title", "one-place-title", "changes-title", "who-title", "soon-title"):
        assert f'aria-labelledby="{title_id}"' in content and f'id="{title_id}"' in content


def test_nothing_on_the_home_moves_for_ever(client):
    content = client.get(reverse("home")).content.decode()

    assert "marquee" not in content.lower()
    assert "animate-" not in content  # only the two decorative shapes drift (and not when the
    # visitor asks for less motion: see css/source.css)


def test_the_home_has_a_skip_link_and_the_viewport_for_a_phone(client):
    content = client.get(reverse("home")).content.decode()

    assert 'href="#contenu"' in content and 'id="contenu"' in content
    assert 'name="viewport"' in content


# --- the features page --------------------------------------------------------------------------


def test_the_features_page_has_one_h1_and_labelled_sections(client):
    content = client.get(reverse("site-features")).content.decode()

    assert len(re.findall(r"<h1[ >]", content)) == 1
    assert "Tout votre quotidien de tournée" in content
    for title_id in (
        "spaces-title",
        "budget-title",
        "roadmap-title",
        "road-title",
        "payroll-title",
        "soon-title",
        "scope-title",
        "cta-title",
    ):
        assert f'aria-labelledby="{title_id}"' in content and f'id="{title_id}"' in content


def test_the_features_page_says_what_the_payroll_help_does_not_do(client):
    content = client.get(reverse("site-features")).content.decode()

    assert "il ne calcule pas les bulletins" in content
    assert "Ne remplace pas un conseil juridique, social ou comptable" in content


def test_the_features_page_numbers_match_the_application(client):
    from apps.documents.models import ContractTemplate

    content = client.get(reverse("site-features")).content.decode()

    assert len(ContractTemplate.choices) == 4  # the page says "quatre modèles"
    assert "quatre modèles" in content


def test_the_features_page_lists_the_same_coming_features_as_the_home(client):
    home = client.get(reverse("home")).content.decode()
    features = client.get(reverse("site-features")).content.decode()

    for feature in NOT_BUILT:
        assert (feature in home) == (feature in features)
    assert "Ce qui arrive." in features


def test_the_features_page_keeps_one_main_action_and_the_invitation_wording(client):
    content = client.get(reverse("site-features")).content.decode()

    assert content.count("btn-primary") == 1
    assert content.count("Demander une invitation") >= 2
    assert reverse("account_signup") not in content
