import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import ContactFactory, PromoterFactory, VenueFactory

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _get(client, url_name, q="", **headers):
    return client.get(reverse(url_name), {"q": q} if q else {}, **headers).content.decode()


def test_search_filters_promoters_by_name_ignoring_case(client):
    tenant = _login(client)
    PromoterFactory(tenant=tenant, name="Festival du Coin")
    PromoterFactory(tenant=tenant, name="Mairie de Lyon")

    content = _get(client, "addressbook:promoter-list", "festival")

    assert "Festival du Coin" in content
    assert "Mairie de Lyon" not in content


def test_search_filters_promoters_by_email(client):
    tenant = _login(client)
    PromoterFactory(tenant=tenant, name="Alpha", email="prog@salle-rouge.fr")
    PromoterFactory(tenant=tenant, name="Beta", email="autre@exemple.fr")

    content = _get(client, "addressbook:promoter-list", "salle-rouge")

    assert "Alpha" in content
    assert "Beta" not in content


def test_search_filters_venues_by_name_or_address(client):
    tenant = _login(client)
    VenueFactory(tenant=tenant, name="La Cave", address="12 rue Haute, Lille")
    VenueFactory(tenant=tenant, name="Le Hangar", address="5 quai Sud, Nantes")

    by_name = _get(client, "addressbook:venue-list", "cave")
    by_address = _get(client, "addressbook:venue-list", "nantes")

    assert "La Cave" in by_name and "Le Hangar" not in by_name
    assert "Le Hangar" in by_address and "La Cave" not in by_address


def test_search_filters_contacts_by_name_role_or_parent(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant, name="Festival du Coin")
    ContactFactory(tenant=tenant, promoter=promoter, name="Julie Martin", role="Technique")
    ContactFactory(tenant=tenant, promoter=PromoterFactory(tenant=tenant), name="Paul Durand")

    assert "Julie Martin" in _get(client, "addressbook:contact-list", "julie")
    assert "Julie Martin" in _get(client, "addressbook:contact-list", "technique")
    by_parent = _get(client, "addressbook:contact-list", "festival")
    assert "Julie Martin" in by_parent and "Paul Durand" not in by_parent


def test_search_never_returns_another_tenants_objects(client):
    _login(client)
    PromoterFactory(name="Festival du Coin")
    VenueFactory(name="La Cave")
    ContactFactory(name="Julie Martin")

    assert "Festival du Coin" not in _get(client, "addressbook:promoter-list", "festival")
    assert "La Cave" not in _get(client, "addressbook:venue-list", "cave")
    assert "Julie Martin" not in _get(client, "addressbook:contact-list", "julie")


def test_empty_search_shows_everything(client):
    tenant = _login(client)
    PromoterFactory(tenant=tenant, name="Alpha")
    PromoterFactory(tenant=tenant, name="Beta")

    content = _get(client, "addressbook:promoter-list", "   ")

    assert "Alpha" in content and "Beta" in content


def test_search_without_result_says_so_and_keeps_the_query(client):
    tenant = _login(client)
    PromoterFactory(tenant=tenant, name="Alpha")

    content = _get(client, "addressbook:promoter-list", "zzz")

    assert "Aucun organisateur ne correspond" in content
    assert "Vous n'avez pas encore d'organisateur" not in content
    assert 'value="zzz"' in content


def test_query_is_escaped(client):
    _login(client)

    content = _get(client, "addressbook:promoter-list", "<script>alert(1)</script>")

    assert "<script>alert(1)</script>" not in content


@pytest.mark.parametrize(
    "url_name", ["addressbook:promoter-list", "addressbook:venue-list", "addressbook:contact-list"]
)
def test_htmx_request_gets_only_the_results_fragment(client, url_name):
    _login(client)

    fragment = _get(client, url_name, "", **HTMX)
    full_page = _get(client, url_name)

    assert "<html" not in fragment
    assert "<html" in full_page


def test_boosted_navigation_still_gets_the_full_page(client):
    _login(client)

    content = _get(client, "addressbook:promoter-list", "", **HTMX, HTTP_HX_BOOSTED="true")

    assert "<html" in content


def test_search_requires_login(client):
    response = client.get(reverse("addressbook:promoter-list"), {"q": "a"})

    assert response.status_code == 302


def test_history_restore_gets_the_full_page(client):
    _login(client)

    content = _get(
        client, "addressbook:promoter-list", "", **HTMX, HTTP_HX_HISTORY_RESTORE_REQUEST="true"
    )

    assert "<html" in content
