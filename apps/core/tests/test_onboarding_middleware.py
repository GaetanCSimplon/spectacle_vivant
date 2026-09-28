import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def test_a_user_without_a_tenant_is_redirected_to_onboarding(client):
    client.force_login(UserFactory())

    response = client.get(reverse("home"))

    assert response.status_code == 302
    assert response.url == reverse("tenants-onboarding")


def test_a_user_with_a_tenant_is_not_redirected(client):
    client.force_login(MembershipFactory().user)

    response = client.get(reverse("home"))

    assert response.status_code == 200


def test_the_onboarding_page_itself_is_not_redirected(client):
    client.force_login(UserFactory())

    response = client.get(reverse("tenants-onboarding"))

    assert response.status_code == 200


def test_logout_works_without_a_tenant(client):
    client.force_login(UserFactory())

    response = client.post(reverse("account_logout"))

    assert response.status_code == 302
    assert response.url != reverse("tenants-onboarding")


def test_admin_is_not_redirected_to_onboarding(client):
    user = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(user)

    response = client.get("/admin/")

    assert response.status_code == 200
