import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import PromoterFactory, VenueFactory
from ..models import Promoter, Venue

pytestmark = pytest.mark.django_db


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def test_new_fields_are_optional():
    promoter = PromoterFactory()
    venue = VenueFactory()
    promoter.refresh_from_db()
    venue.refresh_from_db()

    assert (promoter.phone, promoter.kind, promoter.notes) == ("", "", "")
    assert (venue.phone, venue.access_info, venue.notes) == ("", "", "")


def test_create_a_promoter_with_type_phone_and_notes(client):
    _login(client)

    response = client.post(
        reverse("addressbook:promoter-create"),
        {
            "name": "Mairie de Lyon",
            "kind": "municipality",
            "phone": "04 72 00 00 00",
            "notes": "Programme en mars",
        },
    )

    promoter = Promoter.objects.get()
    assert response.status_code == 302
    assert (promoter.kind, promoter.phone, promoter.notes) == (
        Promoter.Kind.MUNICIPALITY,
        "04 72 00 00 00",
        "Programme en mars",
    )


def test_promoter_type_must_be_one_of_the_choices(client):
    _login(client)

    response = client.post(
        reverse("addressbook:promoter-create"), {"name": "Mairie", "kind": "inconnu"}
    )

    assert response.status_code == 200
    assert not Promoter.objects.exists()


def test_promoter_type_can_be_left_empty(client):
    _login(client)

    response = client.post(reverse("addressbook:promoter-create"), {"name": "Mairie", "kind": ""})

    assert response.status_code == 302
    assert Promoter.objects.get().kind == ""


def test_promoter_detail_shows_type_phone_and_notes(client):
    tenant = _login(client)
    promoter = PromoterFactory(
        tenant=tenant, kind="festival", phone="0612345678", notes="Ne pas appeler le lundi"
    )

    content = client.get(
        reverse("addressbook:promoter-detail", args=[promoter.pk])
    ).content.decode()

    assert "Festival" in content
    assert 'href="tel:0612345678"' in content
    assert "Ne pas appeler le lundi" in content


def test_create_a_venue_with_phone_access_info_and_notes(client):
    _login(client)

    response = client.post(
        reverse("addressbook:venue-create"),
        {
            "name": "La Cave",
            "phone": "0298000000",
            "access_info": "Parking rue Haute, chargement par la cour",
            "notes": "Scène de 4 m",
        },
    )

    venue = Venue.objects.get()
    assert response.status_code == 302
    assert (venue.phone, venue.access_info, venue.notes) == (
        "0298000000",
        "Parking rue Haute, chargement par la cour",
        "Scène de 4 m",
    )


def test_venue_detail_shows_phone_access_info_and_notes(client):
    tenant = _login(client)
    venue = VenueFactory(
        tenant=tenant,
        phone="0298000000",
        access_info="Chargement par la cour",
        notes="Scène de 4 m",
    )

    content = client.get(reverse("addressbook:venue-detail", args=[venue.pk])).content.decode()

    assert 'href="tel:0298000000"' in content
    assert "Chargement par la cour" in content
    assert "Scène de 4 m" in content


def test_new_fields_cannot_be_edited_on_another_tenants_objects(client):
    _login(client)
    promoter = PromoterFactory(notes="Avant")
    venue = VenueFactory(notes="Avant")

    r1 = client.post(
        reverse("addressbook:promoter-update", args=[promoter.pk]), {"name": "X", "notes": "Après"}
    )
    r2 = client.post(
        reverse("addressbook:venue-update", args=[venue.pk]), {"name": "X", "notes": "Après"}
    )

    assert (r1.status_code, r2.status_code) == (404, 404)
    promoter.refresh_from_db()
    venue.refresh_from_db()
    assert (promoter.notes, venue.notes) == ("Avant", "Avant")
