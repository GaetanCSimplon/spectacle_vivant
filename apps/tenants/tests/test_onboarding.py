import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Membership
from apps.tenants.models import Tenant

from ..factories import MembershipFactory

pytestmark = pytest.mark.django_db

URL = reverse("tenants-onboarding")


def _payload(**overrides):
    data = {
        "name": "Compagnie du Soleil",
        "legal_form": "Association loi 1901",
        "vat_regime": "franchise",
    }
    data.update(overrides)
    return data


def test_onboarding_requires_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_onboarding_shows_the_form(client):
    client.force_login(UserFactory())

    response = client.get(URL)

    content = response.content.decode()
    assert response.status_code == 200
    assert 'name="name"' in content
    assert 'name="vat_regime"' in content


def test_submitting_creates_a_tenant_and_makes_the_user_its_owner(client):
    user = UserFactory()
    client.force_login(user)

    response = client.post(URL, _payload())

    assert response.status_code == 302
    assert response.url == reverse("gigs:wizard-show")
    tenant = Tenant.objects.get(name="Compagnie du Soleil")
    assert tenant.legal_form == "Association loi 1901"
    membership = Membership.objects.get(user=user, tenant=tenant)
    assert membership.role == Membership.Role.OWNER


def test_name_is_required(client):
    client.force_login(UserFactory())

    response = client.post(URL, _payload(name=""))

    assert response.status_code == 200
    assert Tenant.objects.count() == 0


def test_a_user_who_already_has_a_tenant_is_redirected_away_on_get(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    response = client.get(URL)

    assert response.status_code == 302
    assert response.url == reverse("home")
    assert Tenant.objects.count() == 1


def test_a_user_who_already_has_a_tenant_cannot_create_a_second_one(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    client.post(URL, _payload())

    assert Tenant.objects.count() == 1
