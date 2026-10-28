"""Quick change of an organiser's status; attaching an existing contact to an organiser or venue."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import ContactFactory, PromoterFactory, VenueFactory
from ..models import Contact, Promoter

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def tenant(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


# --- the status menu ----------------------------------------------------------------------


def test_the_status_is_changed_with_one_click_and_the_menu_comes_back(client, tenant):
    promoter = PromoterFactory(tenant=tenant, follow_up="prospect")

    response = client.post(
        reverse("addressbook:promoter-follow-up", args=[promoter.pk]),
        {"follow_up": "active"},
        **HTMX,
    )

    promoter.refresh_from_db()
    page = response.content.decode()
    assert promoter.follow_up == "active" and response.status_code == 200
    assert f'id="follow-up-{promoter.pk}"' in page and "Client actif" in page
    assert "<html" not in page  # only the small menu is swapped


def test_without_javascript_the_page_is_reloaded(client, tenant):
    promoter = PromoterFactory(tenant=tenant)

    response = client.post(
        reverse("addressbook:promoter-follow-up", args=[promoter.pk]),
        {"follow_up": "signing", "next": reverse("addressbook:promoter-list")},
    )

    promoter.refresh_from_db()
    assert response.status_code == 302 and response.url == reverse("addressbook:promoter-list")
    assert promoter.follow_up == "signing"


def test_the_status_can_be_cleared(client, tenant):
    promoter = PromoterFactory(tenant=tenant, follow_up="active")

    client.post(
        reverse("addressbook:promoter-follow-up", args=[promoter.pk]), {"follow_up": ""}, **HTMX
    )

    promoter.refresh_from_db()
    assert promoter.follow_up == ""


@pytest.mark.parametrize("value", ["nope", "ACTIVE", "<script>"])
def test_a_made_up_status_is_refused(client, tenant, value):
    promoter = PromoterFactory(tenant=tenant, follow_up="prospect")

    response = client.post(
        reverse("addressbook:promoter-follow-up", args=[promoter.pk]), {"follow_up": value}, **HTMX
    )

    promoter.refresh_from_db()
    assert response.status_code == 400 and promoter.follow_up == "prospect"


def test_another_structures_organiser_cannot_be_changed(client, tenant):
    foreign = PromoterFactory(follow_up="prospect")

    response = client.post(
        reverse("addressbook:promoter-follow-up", args=[foreign.pk]), {"follow_up": "active"}
    )

    foreign.refresh_from_db()
    assert response.status_code == 404 and foreign.follow_up == "prospect"


def test_the_status_change_is_post_only_and_needs_a_login(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    url = reverse("addressbook:promoter-follow-up", args=[promoter.pk])

    assert client.get(url).status_code == 405
    client.logout()
    assert client.post(url, {"follow_up": "active"}).status_code == 302


def test_the_list_and_the_page_offer_the_menu_with_every_status(client, tenant):
    promoter = PromoterFactory(tenant=tenant, name="Mairie de Test", follow_up="negotiating")

    list_page = client.get(reverse("addressbook:promoter-list")).content.decode()
    detail = client.get(reverse("addressbook:promoter-detail", args=[promoter.pk])).content.decode()

    for page in (list_page, detail):
        assert f'id="follow-up-{promoter.pk}"' in page
        for label in ("Prospect", "En négociation", "En signature", "Client actif", "Sans suite"):
            assert label in page
        assert "Changer le statut de Mairie de Test" in page and "Aucun statut" in page


def test_the_menu_is_offered_even_when_there_is_no_status_yet(client, tenant):
    promoter = PromoterFactory(tenant=tenant, follow_up="")

    page = client.get(reverse("addressbook:promoter-detail", args=[promoter.pk])).content.decode()

    assert f'id="follow-up-{promoter.pk}"' in page and ">Statut<" in page


# --- attaching an existing contact ------------------------------------------------------------


def test_an_existing_contact_is_attached_to_an_organiser(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=None, venue=None, name="Dans l'annuaire")

    response = client.post(
        reverse("addressbook:promoter-contact-attach", args=[promoter.pk]), {"contact": contact.pk}
    )

    assert response.status_code == 302 and response.url == promoter.get_absolute_url()
    assert list(contact.promoters.all()) == [promoter]
    page = client.get(promoter.get_absolute_url()).content.decode()
    assert "Dans l&#x27;annuaire" in page or "Dans l'annuaire" in page


def test_attaching_keeps_the_other_attachments(client, tenant):
    first = PromoterFactory(tenant=tenant)
    second = PromoterFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=first)

    client.post(
        reverse("addressbook:promoter-contact-attach", args=[second.pk]), {"contact": contact.pk}
    )

    assert set(contact.promoters.all()) == {first, second}


def test_an_existing_contact_is_attached_to_a_venue(client, tenant):
    venue = VenueFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=None, venue=None)

    client.post(
        reverse("addressbook:venue-contact-attach", args=[venue.pk]), {"contact": contact.pk}
    )

    assert list(contact.venues.all()) == [venue]


def test_the_form_only_lists_contacts_not_yet_attached_and_of_this_structure(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    ContactFactory(tenant=tenant, promoter=promoter, name="Déjà là")
    ContactFactory(tenant=tenant, promoter=None, venue=None, name="Disponible")
    ContactFactory(name="Étranger secret")

    page = client.get(promoter.get_absolute_url()).content.decode()
    options = page.split('id="attach-contact"')[1].split("</select>")[0]

    assert "Disponible" in options
    assert "Déjà là" not in options and "Étranger secret" not in options


def test_no_form_when_every_contact_is_already_here(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    ContactFactory(tenant=tenant, promoter=promoter)

    page = client.get(promoter.get_absolute_url()).content.decode()

    assert "Rattacher un contact existant" not in page


@pytest.mark.parametrize("value", ["", "abc", "999999"])
def test_a_missing_or_made_up_contact_is_refused(client, tenant, value):
    promoter = PromoterFactory(tenant=tenant)

    response = client.post(
        reverse("addressbook:promoter-contact-attach", args=[promoter.pk]), {"contact": value}
    )

    assert response.status_code in (302, 404) and not promoter.contacts.exists()


def test_another_structures_contact_cannot_be_attached(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    foreign = ContactFactory(promoter=None, venue=None)

    response = client.post(
        reverse("addressbook:promoter-contact-attach", args=[promoter.pk]), {"contact": foreign.pk}
    )

    assert response.status_code == 404 and not foreign.promoters.exists()


def test_another_structures_organiser_cannot_receive_my_contact(client, tenant):
    foreign = PromoterFactory()
    mine = ContactFactory(tenant=tenant, promoter=None, venue=None)

    response = client.post(
        reverse("addressbook:promoter-contact-attach", args=[foreign.pk]), {"contact": mine.pk}
    )

    assert response.status_code == 404 and not mine.promoters.exists()


def test_a_contact_is_taken_off_an_organiser_without_being_deleted(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    other = PromoterFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=promoter)
    contact.promoters.add(other)

    response = client.post(
        reverse("addressbook:promoter-contact-detach", args=[promoter.pk, contact.pk])
    )

    assert response.status_code == 302
    assert list(contact.promoters.all()) == [other]
    assert Contact.objects.filter(pk=contact.pk).exists()


def test_taking_the_last_link_off_leaves_the_contact_in_the_directory(client, tenant):
    venue = VenueFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=None, venue=venue, name="Régisseur")

    client.post(reverse("addressbook:venue-contact-detach", args=[venue.pk, contact.pk]))

    page = client.get(reverse("addressbook:contact-list")).content.decode()
    assert "Régisseur" in page and "Sans rattachement" in page


def test_the_pages_show_a_remove_button_for_each_contact(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=promoter)

    page = client.get(promoter.get_absolute_url()).content.decode()

    assert reverse("addressbook:promoter-contact-detach", args=[promoter.pk, contact.pk]) in page
    assert "Retirer d&#x27;ici" in page or "Retirer d'ici" in page


def test_attach_and_detach_are_post_only(client, tenant):
    promoter = PromoterFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant, promoter=promoter)

    assert (
        client.get(reverse("addressbook:promoter-contact-attach", args=[promoter.pk])).status_code
        == 405
    )
    assert (
        client.get(
            reverse("addressbook:promoter-contact-detach", args=[promoter.pk, contact.pk])
        ).status_code
        == 405
    )
    assert Promoter.objects.filter(pk=promoter.pk).exists() and promoter.contacts.count() == 1
