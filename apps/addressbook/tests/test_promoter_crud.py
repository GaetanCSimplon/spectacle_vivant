import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

from ..factories import ContactFactory, PromoterFactory
from ..models import Promoter

pytestmark = pytest.mark.django_db


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {
        "name": "Festival du Coin",
        "email": "contact@festival.fr",
        "siret": "",
        "licence_number": "",
        "representative_name": "",
        "representative_role": "",
        "billing_address": "",
    }
    data.update(overrides)
    return data


def test_promoter_list_requires_login(client):
    response = client.get(reverse("addressbook:promoter-list"))

    assert response.status_code == 302


def test_promoter_list_only_shows_the_current_tenants_promoters(client):
    tenant = _login(client)
    PromoterFactory(tenant=tenant, name="Le mien")
    PromoterFactory(name="Un autre")

    content = client.get(reverse("addressbook:promoter-list")).content.decode()

    assert "Le mien" in content
    assert "Un autre" not in content


def test_create_a_promoter(client):
    tenant = _login(client)

    response = client.post(reverse("addressbook:promoter-create"), _payload())

    assert response.status_code == 302
    promoter = Promoter.objects.get(name="Festival du Coin")
    assert promoter.tenant == tenant
    assert response.url == reverse("addressbook:promoter-detail", args=[promoter.pk])


def test_name_is_required_to_create_a_promoter(client):
    _login(client)

    response = client.post(reverse("addressbook:promoter-create"), _payload(name=""))

    assert response.status_code == 200
    assert not Promoter.objects.exists()


def test_promoter_detail_shows_contacts_and_gigs(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)
    ContactFactory(tenant=tenant, promoter=promoter, name="Julie Martin")
    gig = GigFactory(tenant=tenant, promoter=promoter)

    url = reverse("addressbook:promoter-detail", args=[promoter.pk])
    content = client.get(url).content.decode()

    assert "Julie Martin" in content
    assert gig.show.title in content


def test_promoter_detail_of_another_tenant_returns_404(client):
    _login(client)
    other = PromoterFactory()

    response = client.get(reverse("addressbook:promoter-detail", args=[other.pk]))

    assert response.status_code == 404


def test_update_a_promoter(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant, name="Ancien nom")

    response = client.post(
        reverse("addressbook:promoter-update", args=[promoter.pk]),
        _payload(name="Nouveau nom"),
    )

    assert response.status_code == 302
    assert response.url == reverse("addressbook:promoter-detail", args=[promoter.pk])
    promoter.refresh_from_db()
    assert promoter.name == "Nouveau nom"


def test_cannot_update_another_tenants_promoter(client):
    _login(client)
    other = PromoterFactory(name="Ancien nom")

    response = client.post(
        reverse("addressbook:promoter-update", args=[other.pk]),
        _payload(name="Nouveau nom"),
    )

    assert response.status_code == 404
    other.refresh_from_db()
    assert other.name == "Ancien nom"


def test_delete_a_promoter_without_gigs(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)

    response = client.post(reverse("addressbook:promoter-delete", args=[promoter.pk]))

    assert response.status_code == 302
    assert not Promoter.objects.filter(pk=promoter.pk).exists()


def test_cannot_delete_a_promoter_used_by_a_gig(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)
    GigFactory(tenant=tenant, promoter=promoter)

    response = client.post(reverse("addressbook:promoter-delete", args=[promoter.pk]))

    assert response.status_code == 302
    assert Promoter.objects.filter(pk=promoter.pk).exists()
