import pytest
from django.urls import reverse

from apps.organizations.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def test_home_requires_login(client):
    response = client.get(reverse("home"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_home_shows_the_organization_name(client):
    membership = MembershipFactory(organization__name="Compagnie du Soleil")
    client.force_login(membership.user)

    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert "Compagnie du Soleil" in response.content.decode()


def test_home_has_mobile_viewport_meta(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    response = client.get(reverse("home"))

    assert 'name="viewport"' in response.content.decode()
