import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import ContactFactory, PromoterFactory, VenueFactory
from ..models import Contact

pytestmark = pytest.mark.django_db


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {"name": "Julie Martin", "role": "Accueil", "email": "", "phone": ""}
    data.update(overrides)
    return data


def test_contact_list_requires_login(client):
    response = client.get(reverse("addressbook:contact-list"))

    assert response.status_code == 302


def test_contact_list_only_shows_the_current_tenants_contacts(client):
    tenant = _login(client)
    ContactFactory(tenant=tenant, promoter=PromoterFactory(tenant=tenant), name="Le mien")
    ContactFactory(name="Un autre")

    content = client.get(reverse("addressbook:contact-list")).content.decode()

    assert "Le mien" in content
    assert "Un autre" not in content


def test_create_a_contact_for_a_promoter(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)

    response = client.post(
        reverse("addressbook:promoter-contact-create", args=[promoter.pk]), _payload()
    )

    assert response.status_code == 302
    assert response.url == reverse("addressbook:promoter-detail", args=[promoter.pk])
    contact = Contact.objects.get()
    assert (contact.tenant, contact.promoter, contact.venue) == (tenant, promoter, None)


def test_create_a_contact_for_a_venue(client):
    tenant = _login(client)
    venue = VenueFactory(tenant=tenant)

    response = client.post(reverse("addressbook:venue-contact-create", args=[venue.pk]), _payload())

    assert response.status_code == 302
    assert response.url == reverse("addressbook:venue-detail", args=[venue.pk])
    contact = Contact.objects.get()
    assert (contact.tenant, contact.promoter, contact.venue) == (tenant, None, venue)


def test_name_is_required_to_create_a_contact(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)

    response = client.post(
        reverse("addressbook:promoter-contact-create", args=[promoter.pk]), _payload(name="")
    )

    assert response.status_code == 200
    assert not Contact.objects.exists()


def test_create_form_is_not_offered_for_another_tenants_promoter(client):
    _login(client)
    other = PromoterFactory()

    url = reverse("addressbook:promoter-contact-create", args=[other.pk])

    assert client.get(url).status_code == 404
    assert client.post(url, _payload()).status_code == 404
    assert not Contact.objects.exists()


def test_create_form_is_not_offered_for_another_tenants_venue(client):
    _login(client)
    other = VenueFactory()

    url = reverse("addressbook:venue-contact-create", args=[other.pk])

    assert client.get(url).status_code == 404
    assert client.post(url, _payload()).status_code == 404
    assert not Contact.objects.exists()


def test_form_ignores_tenant_and_parent_fields_sent_by_the_client(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)
    other_promoter = PromoterFactory()
    other_venue = VenueFactory()

    client.post(
        reverse("addressbook:promoter-contact-create", args=[promoter.pk]),
        _payload(tenant=other_promoter.tenant_id, promoter=other_promoter.pk, venue=other_venue.pk),
    )

    contact = Contact.objects.get()
    assert (contact.tenant, contact.promoter, contact.venue) == (tenant, promoter, None)


def test_promoter_detail_links_to_the_contact_form(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)

    content = client.get(
        reverse("addressbook:promoter-detail", args=[promoter.pk])
    ).content.decode()

    assert reverse("addressbook:promoter-contact-create", args=[promoter.pk]) in content


def test_update_a_contact(client):
    tenant = _login(client)
    contact = ContactFactory(tenant=tenant, promoter=PromoterFactory(tenant=tenant), name="Ancien")

    response = client.post(
        reverse("addressbook:contact-update", args=[contact.pk]), _payload(name="Nouveau")
    )

    assert response.status_code == 302
    assert response.url == reverse("addressbook:promoter-detail", args=[contact.promoter_id])
    contact.refresh_from_db()
    assert contact.name == "Nouveau"


def test_updating_a_contact_keeps_its_parent(client):
    tenant = _login(client)
    venue = VenueFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=None, venue=venue)

    client.post(reverse("addressbook:contact-update", args=[contact.pk]), _payload())

    contact.refresh_from_db()
    assert (contact.promoter, contact.venue) == (None, venue)


def test_cannot_update_another_tenants_contact(client):
    _login(client)
    other = ContactFactory(name="Ancien")

    response = client.post(
        reverse("addressbook:contact-update", args=[other.pk]), _payload(name="Nouveau")
    )

    assert response.status_code == 404
    other.refresh_from_db()
    assert other.name == "Ancien"


def test_delete_a_contact(client):
    tenant = _login(client)
    venue = VenueFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=None, venue=venue)

    response = client.post(reverse("addressbook:contact-delete", args=[contact.pk]))

    assert response.status_code == 302
    assert response.url == reverse("addressbook:venue-detail", args=[venue.pk])
    assert not Contact.objects.exists()


def test_cannot_delete_another_tenants_contact(client):
    _login(client)
    other = ContactFactory()

    response = client.post(reverse("addressbook:contact-delete", args=[other.pk]))

    assert response.status_code == 404
    assert Contact.objects.filter(pk=other.pk).exists()


def test_deleting_a_promoter_deletes_its_contacts(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)
    ContactFactory(tenant=tenant, promoter=promoter)

    client.post(reverse("addressbook:promoter-delete", args=[promoter.pk]))

    assert not Contact.objects.exists()
