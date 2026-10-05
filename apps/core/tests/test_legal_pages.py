import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db

LEGAL_URLS = ["legal-notice", "legal-terms", "legal-privacy"]


@pytest.mark.parametrize("name", LEGAL_URLS)
def test_legal_pages_are_public(client, name):
    response = client.get(reverse(name))

    assert response.status_code == 200
    assert "Texte provisoire" in response.content.decode()


@pytest.mark.parametrize("name", LEGAL_URLS)
def test_legal_pages_are_not_redirected_to_onboarding(client, name):
    client.force_login(UserFactory())  # logged in, no tenant yet

    response = client.get(reverse(name))

    assert response.status_code == 200


@pytest.mark.parametrize("name", LEGAL_URLS)
def test_footer_links_are_on_every_kind_of_page(client, name):
    anonymous = client.get(reverse("account_login")).content.decode()
    client.force_login(MembershipFactory().user)
    logged_in = client.get(reverse("home")).content.decode()

    for html in (anonymous, logged_in):
        assert reverse(name) in html
