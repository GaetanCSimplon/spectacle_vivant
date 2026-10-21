"""The product is called Bòrd Pro, everywhere the user can see a name."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def test_login_page_and_home_show_the_new_name(client):
    login = client.get(reverse("account_login")).content.decode()
    assert 'alt="Bòrd Pro"' in login

    client.force_login(MembershipFactory().user)
    home = client.get(reverse("home")).content.decode()
    assert "<title>Accueil — Bòrd Pro</title>" in home
    assert "Spectacle Vivant" not in home


@pytest.mark.parametrize("name", ["legal-notice", "legal-terms", "legal-privacy"])
def test_legal_pages_use_the_new_name(client, name):
    content = client.get(reverse(name)).content.decode()
    assert "Bòrd Pro" in content
    assert "Spectacle Vivant" not in content
