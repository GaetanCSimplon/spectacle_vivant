"""The distribution of a show is chosen among the team, and a new member can be added on the way."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory, PersonFactory
from apps.tenants.models import Person

from ..factories import ShowFactory
from ..models import Show

pytestmark = pytest.mark.django_db


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {"title": "Nuits d'été", "duration_minutes": "75", "default_price": "800.00"}
    data.update(overrides)
    return data


def test_the_form_offers_the_team_of_the_structure_only(client):
    tenant = _login(client)
    PersonFactory(tenant=tenant, first_name="Léa", last_name="Durand")
    PersonFactory(first_name="Intrus", last_name="Etranger")

    page = client.get(reverse("catalog:show-create")).content.decode()

    assert "Léa Durand" in page and "Etranger" not in page


def test_the_cast_is_saved_with_the_chosen_members(client):
    tenant = _login(client)
    lea = PersonFactory(tenant=tenant, is_artist=True)
    marc = PersonFactory(tenant=tenant, is_artist=True)

    response = client.post(reverse("catalog:show-create"), _payload(cast=[lea.pk, marc.pk]))

    assert response.status_code == 302
    show = Show.objects.get(tenant=tenant)
    assert set(show.cast.all()) == {lea, marc}


def test_a_person_of_another_structure_cannot_be_posted_in_the_cast(client):
    tenant = _login(client)
    foreign = PersonFactory()

    response = client.post(reverse("catalog:show-create"), _payload(cast=[foreign.pk]))

    assert response.status_code == 200
    assert not Show.objects.filter(tenant=tenant).exists()


def test_a_new_member_joins_the_team_and_the_cast(client):
    tenant = _login(client)

    client.post(
        reverse("catalog:show-create"),
        _payload(new_first_name="  Jo ", new_last_name="Martin", new_is_technician="on"),
    )

    person = Person.objects.get(tenant=tenant)
    assert (person.first_name, person.last_name) == ("Jo", "Martin")
    assert person.is_technician and not person.is_artist
    assert list(Show.objects.get(tenant=tenant).cast.all()) == [person]


def test_a_new_member_keeps_the_role_and_the_contact_given_with_it(client):
    tenant = _login(client)

    client.post(
        reverse("catalog:show-create"),
        _payload(
            new_first_name="Jo",
            new_last_name="Martin",
            new_role="  Régisseur   son ",
            new_phone=" 06 11 22 33 44 ",
            new_email="jo@example.org",
            new_is_technician="on",
        ),
    )

    person = Person.objects.get(tenant=tenant)
    assert person.role == "Régisseur son"
    assert person.phone == "06 11 22 33 44" and person.email == "jo@example.org"


def test_a_wrong_email_for_the_new_member_is_refused(client):
    tenant = _login(client)

    response = client.post(
        reverse("catalog:show-create"),
        _payload(new_first_name="Jo", new_last_name="Martin", new_email="pas-un-email"),
    )

    assert response.status_code == 200
    assert not Person.objects.filter(tenant=tenant).exists()


def test_a_new_member_needs_both_names(client):
    tenant = _login(client)

    response = client.post(reverse("catalog:show-create"), _payload(new_first_name="Jo"))

    assert response.status_code == 200
    assert "prénom et le nom" in response.content.decode()
    assert not Show.objects.filter(tenant=tenant).exists()
    assert not Person.objects.filter(tenant=tenant).exists()


def test_the_counts_follow_the_chosen_members(client):
    tenant = _login(client)
    singer = PersonFactory(tenant=tenant, is_artist=True)
    both = PersonFactory(tenant=tenant, is_artist=True, is_technician=True)
    tech = PersonFactory(tenant=tenant, is_technician=True)

    client.post(
        reverse("catalog:show-create"),
        _payload(cast=[singer.pk, both.pk, tech.pk], artists_count="9", technicians_count="9"),
    )

    show = Show.objects.get(tenant=tenant)
    assert (show.artists_count, show.technicians_count) == (2, 2)


def test_the_counts_typed_by_hand_are_kept_when_nobody_is_chosen(client):
    tenant = _login(client)

    client.post(reverse("catalog:show-create"), _payload(artists_count="4"))

    assert Show.objects.get(tenant=tenant).artists_count == 4


def test_a_show_can_be_edited_without_losing_its_cast(client):
    tenant = _login(client)
    lea = PersonFactory(tenant=tenant)
    show = ShowFactory(tenant=tenant)
    show.cast.add(lea)

    client.post(
        reverse("catalog:show-update", args=[show.pk]), _payload(cast=[lea.pk], title="Autre")
    )

    show.refresh_from_db()
    assert show.title == "Autre" and list(show.cast.all()) == [lea]


def test_the_detail_lists_the_cast_and_keeps_the_old_text_until_a_member_is_chosen(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant, performers="Julie et Marc")
    url = reverse("catalog:show-detail", args=[show.pk])

    before = client.get(url).content.decode()
    show.cast.add(PersonFactory(tenant=tenant, first_name="Léa", last_name="Durand"))
    after = client.get(url).content.decode()

    assert "ancienne saisie" in before and "Julie et Marc" in before
    assert "Léa Durand" in after and "Julie et Marc" not in after


def test_the_distribution_text_leaves_out_a_technician_and_falls_back_to_the_old_text():
    show = ShowFactory(performers="Texte ancien")
    assert show.distribution_text == "Texte ancien"

    show.cast.add(
        PersonFactory(tenant=show.tenant, first_name="Léa", last_name="A", is_artist=True),
        PersonFactory(tenant=show.tenant, first_name="Tom", last_name="B", is_technician=True),
        PersonFactory(tenant=show.tenant, first_name="Zoé", last_name="C"),
    )

    assert show.distribution_text == "Léa A, Zoé C"
