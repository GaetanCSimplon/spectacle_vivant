import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def test_a_visitor_sees_the_presentation_page_not_the_dashboard(client):
    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert "site/home.html" in [t.name for t in response.templates]


def test_home_shows_the_tenant_name(client):
    membership = MembershipFactory(tenant__name="Compagnie du Soleil")
    client.force_login(membership.user)

    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert "Compagnie du Soleil" in response.content.decode()


def test_home_has_mobile_viewport_meta(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    response = client.get(reverse("home"))

    assert 'name="viewport"' in response.content.decode()
