import pytest
from django.urls import reverse

from ..factories import MembershipFactory

pytestmark = pytest.mark.django_db

URL = reverse("tenants:profile")


def test_bord_requires_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


@pytest.mark.parametrize("role", ["owner", "member"])
def test_bord_links_to_the_settings_and_the_team(client, role):
    client.force_login(MembershipFactory(role=role).user)

    response = client.get(URL)

    content = response.content.decode()
    assert response.status_code == 200
    assert reverse("tenants:settings") in content
    assert reverse("tenants:person-list") in content
    assert reverse("export") in content


def test_bord_sends_a_user_without_a_tenant_to_onboarding(client, django_user_model):
    client.force_login(django_user_model.objects.create_user(email="seul@example.org"))

    response = client.get(URL)

    assert response.status_code == 302
    assert response.url == reverse("tenants-onboarding")


def test_old_profile_wording_is_gone(client):
    client.force_login(MembershipFactory().user)

    for url in (URL, reverse("tenants:settings"), reverse("tenants:person-list")):
        assert "Ma structure" not in client.get(url).content.decode()
