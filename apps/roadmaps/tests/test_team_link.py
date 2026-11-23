"""Putting a person of the team on a gig, and following who took part in what (F-06)."""

import datetime

import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.gigs.models import Gig, GigMember
from apps.tenants.factories import MembershipFactory, PersonFactory

from .. import services

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _add_url(gig):
    return reverse("roadmaps:team-add", args=[gig.pk])


def _gig(tenant, **fields):
    return GigFactory(tenant=tenant, **fields)


# --- adding ----------------------------------------------------------------------------


def test_a_person_is_copied_onto_the_gig_without_the_fee(client):
    tenant = _login(client)
    gig = _gig(tenant)
    person = PersonFactory(
        tenant=tenant,
        first_name="Léa",
        last_name="Durand",
        role="Chanteuse",
        phone="0601020304",
        email="lea@example.org",
        average_fee="987.65",
    )

    response = client.post(_add_url(gig), {"person": person.pk}, **HTMX)

    assert response.status_code == 200
    member = GigMember.objects.get()
    assert (member.person, member.gig, member.tenant) == (person, gig, tenant)
    assert (member.name, member.role, member.phone, member.email) == (
        "Léa Durand",
        "Chanteuse",
        "0601020304",
        "lea@example.org",
    )
    assert "987" not in client.get(reverse("roadmaps:editor", args=[gig.pk])).content.decode()


def test_the_fee_never_reaches_the_public_page(client):
    tenant = _login(client)
    gig = _gig(tenant)
    person = PersonFactory(tenant=tenant, average_fee="987.65")
    client.post(_add_url(gig), {"person": person.pk})
    roadmap = services.get_or_create_roadmap(gig)
    services.publish(roadmap)
    client.logout()

    html = client.get(services.public_path(roadmap.token)).content.decode()

    assert person.first_name in html
    assert "987" not in html


def test_the_same_person_cannot_join_a_gig_twice(client):
    tenant = _login(client)
    gig = _gig(tenant)
    person = PersonFactory(tenant=tenant)

    client.post(_add_url(gig), {"person": person.pk})
    client.post(_add_url(gig), {"person": person.pk})

    assert GigMember.objects.count() == 1
    other_gig = _gig(tenant)
    client.post(_add_url(other_gig), {"person": person.pk})
    assert GigMember.objects.count() == 2


def test_a_person_of_another_tenant_is_a_404_and_nothing_is_created(client):
    tenant = _login(client)
    gig = _gig(tenant)
    stranger = PersonFactory()

    assert client.post(_add_url(gig), {"person": stranger.pk}).status_code == 404
    assert client.post(_add_url(gig), {"person": "abc"}).status_code == 404
    assert client.post(_add_url(gig), {}).status_code == 404
    assert not GigMember.objects.exists()


def test_a_gig_of_another_tenant_is_a_404(client):
    tenant = _login(client)
    foreign_gig = GigFactory()
    person = PersonFactory(tenant=tenant)

    assert client.post(_add_url(foreign_gig), {"person": person.pk}).status_code == 404
    assert not GigMember.objects.exists()


def test_adding_is_post_only_and_needs_login(client):
    gig = _gig(_login(client))
    assert client.get(_add_url(gig)).status_code == 405
    client.logout()
    assert client.post(_add_url(gig), {"person": 1}).url.startswith(reverse("account_login"))


def test_the_editor_offers_only_people_not_yet_on_the_gig_and_of_this_tenant(client):
    tenant = _login(client)
    gig = _gig(tenant)
    on_gig = PersonFactory(tenant=tenant, last_name="DejaLa")
    PersonFactory(tenant=tenant, last_name="Libre")
    PersonFactory(last_name="Etranger")
    client.post(_add_url(gig), {"person": on_gig.pk})

    response = client.get(reverse("roadmaps:editor", args=[gig.pk]))

    assert "Ajouter depuis mon équipe" in response.content.decode()
    assert [p.last_name for p in response.context["team_choices"]] == ["Libre"]


def test_a_manual_member_is_still_possible(client):
    gig = _gig(_login(client))
    client.post(
        reverse("roadmaps:item-add", args=[gig.pk, "equipe"]), {"name": "De passage", "role": "Son"}
    )
    member = GigMember.objects.get()
    assert member.person is None


# --- following who took part -------------------------------------------------------------


def test_deleting_a_person_keeps_the_roadmap_line(client):
    tenant = _login(client)
    gig = _gig(tenant)
    person = PersonFactory(tenant=tenant, first_name="Léa", last_name="Durand")
    client.post(_add_url(gig), {"person": person.pk})

    client.post(reverse("tenants:person-delete", args=[person.pk]))

    member = GigMember.objects.get()
    assert member.person is None and member.name == "Léa Durand"


def test_the_person_card_lists_their_dates(client):
    tenant = _login(client)
    person = PersonFactory(tenant=tenant)
    gig_in = _gig(tenant, date=datetime.date(2026, 11, 5))
    _gig(tenant, date=datetime.date(2026, 12, 5))  # not theirs
    GigMemberFactory(gig=gig_in, person=person, tenant=tenant)

    response = client.get(reverse("tenants:person-detail", args=[person.pk]))

    assert list(response.context["gigs"]) == [gig_in]
    assert "1 date" in response.content.decode()


def test_the_team_list_counts_this_years_live_dates(client):
    tenant = _login(client)
    year = datetime.date.today().year
    person = PersonFactory(tenant=tenant)
    for month, status in (
        (3, Gig.Status.CONFIRMED),
        (4, Gig.Status.OPTION),
        (5, Gig.Status.CANCELLED),
    ):
        gig = _gig(tenant, date=datetime.date(year, month, 10), status=status)
        GigMemberFactory(gig=gig, person=person, tenant=tenant)
    last_year = _gig(tenant, date=datetime.date(year - 1, 3, 10))
    GigMemberFactory(gig=last_year, person=person, tenant=tenant)

    listed = client.get(reverse("tenants:person-list")).context["object_list"]

    assert [p.year_gigs for p in listed] == [2]


def test_the_gig_page_shows_who_is_on_it(client):
    tenant = _login(client)
    gig = _gig(tenant)
    on = PersonFactory(tenant=tenant, first_name="Léa", last_name="Durand")
    PersonFactory(tenant=tenant)
    PersonFactory(tenant=tenant)
    client.post(_add_url(gig), {"person": on.pk})
    GigMemberFactory(gig=gig, tenant=tenant, name="Invité sans fiche")

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert "Léa Durand" in content and "Invité sans fiche" in content
    assert "1 sur 3 de votre équipe" in content


def test_the_team_figures_never_count_another_tenants_people(client):
    tenant = _login(client)
    gig = _gig(tenant)
    PersonFactory()
    PersonFactory()
    GigMemberFactory(gig=gig, tenant=tenant, name="Seul")

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert "sur" not in content.split("Équipe :")[1].split("</p>")[0]


def test_the_reference_fee_is_copied_to_the_date_once(client):
    tenant = _login(client)
    gig = _gig(tenant)
    person = PersonFactory(tenant=tenant, average_fee="150.50")
    other = PersonFactory(tenant=tenant, average_fee=None)

    client.post(_add_url(gig), {"person": person.pk})
    client.post(_add_url(gig), {"person": other.pk})
    person.average_fee = "999.00"
    person.save()

    amounts = {m.person_id: m.cachet_amount for m in gig.members.all()}
    assert str(amounts[person.pk]) == "150.50"
    assert amounts[other.pk] is None
