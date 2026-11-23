import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import ContactFactory, PromoterFactory, VenueFactory
from ..models import Contact
from .helpers import directory_url

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
    response = client.get(directory_url("contact"))

    assert response.status_code == 302


def test_contact_list_only_shows_the_current_tenants_contacts(client):
    tenant = _login(client)
    ContactFactory(tenant=tenant, promoter=PromoterFactory(tenant=tenant), name="Le mien")
    ContactFactory(name="Un autre")

    content = client.get(directory_url("contact")).content.decode()

    assert "Le mien" in content
    assert "Un autre" not in content


def test_create_a_contact_for_a_promoter(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)

    response = client.post(
        reverse("addressbook:promoter-contact-create", args=[promoter.pk]),
        _payload(promoters=[promoter.pk]),  # the box is already ticked on the page
    )

    assert response.status_code == 302
    assert response.url == reverse("addressbook:promoter-detail", args=[promoter.pk])
    contact = Contact.objects.get()
    assert contact.tenant == tenant
    assert list(contact.promoters.all()) == [promoter] and not contact.venues.exists()


def test_the_organiser_is_preselected_and_others_can_be_added(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)
    other = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)
    url = reverse("addressbook:promoter-contact-create", args=[promoter.pk])

    page = client.get(url).content.decode()
    client.post(url, _payload(promoters=[promoter.pk, other.pk], venues=[venue.pk]))

    assert f'value="{promoter.pk}" data-label="{promoter.name}"' in page and "checked" in page
    contact = Contact.objects.get()
    assert set(contact.promoters.all()) == {promoter, other}
    assert list(contact.venues.all()) == [venue]


def test_create_a_contact_for_a_venue(client):
    tenant = _login(client)
    venue = VenueFactory(tenant=tenant)

    response = client.post(
        reverse("addressbook:venue-contact-create", args=[venue.pk]), _payload(venues=[venue.pk])
    )

    assert response.status_code == 302
    assert response.url == reverse("addressbook:venue-detail", args=[venue.pk])
    contact = Contact.objects.get()
    assert contact.tenant == tenant
    assert list(contact.venues.all()) == [venue] and not contact.promoters.exists()


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


def test_form_ignores_the_tenant_and_refuses_another_structures_organisers_and_venues(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)
    other_promoter = PromoterFactory()
    other_venue = VenueFactory()
    url = reverse("addressbook:promoter-contact-create", args=[promoter.pk])

    ignored = client.post(url, _payload(tenant=other_promoter.tenant_id, promoters=[promoter.pk]))
    foreign_promoter = client.post(url, _payload(promoters=[promoter.pk, other_promoter.pk]))
    foreign_venue = client.post(url, _payload(venues=[other_venue.pk]))

    assert ignored.status_code == 302
    assert foreign_promoter.status_code == 200 and foreign_venue.status_code == 200
    contact = Contact.objects.get()  # only the first one was saved
    assert contact.tenant == tenant and list(contact.promoters.all()) == [promoter]


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
    assert response.url == directory_url("contact")
    contact.refresh_from_db()
    assert contact.name == "Nouveau"


def test_updating_a_contact_changes_its_attachments(client):
    tenant = _login(client)
    old = PromoterFactory(tenant=tenant)
    new_venue = VenueFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=old)

    client.post(
        reverse("addressbook:contact-update", args=[contact.pk]), _payload(venues=[new_venue.pk])
    )

    contact.refresh_from_db()
    assert not contact.promoters.exists() and list(contact.venues.all()) == [new_venue]


def test_a_contact_can_be_detached_from_everything(client):
    tenant = _login(client)
    contact = ContactFactory(tenant=tenant, promoter=PromoterFactory(tenant=tenant))

    client.post(reverse("addressbook:contact-update", args=[contact.pk]), _payload())

    contact.refresh_from_db()
    assert contact.attachments == []


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
    assert response.url == directory_url("contact")
    assert not Contact.objects.exists()


def test_cannot_delete_another_tenants_contact(client):
    _login(client)
    other = ContactFactory()

    response = client.post(reverse("addressbook:contact-delete", args=[other.pk]))

    assert response.status_code == 404
    assert Contact.objects.filter(pk=other.pk).exists()


def test_deleting_a_promoter_keeps_its_contacts_in_the_directory(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=promoter)

    client.post(reverse("addressbook:promoter-delete", args=[promoter.pk]))

    assert Contact.objects.filter(pk=contact.pk).exists()
    page = client.get(directory_url("contact")).content.decode()
    assert contact.name in page and "Sans rattachement" in page
