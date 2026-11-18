"""The team of a date and the cachets (F-88, F-93): who is on it, what each is paid (owner only)."""

import html
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalog.factories import ShowFactory
from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.gigs.models import GigMember
from apps.roadmaps.factories import RoadmapFactory
from apps.roadmaps.services import publish
from apps.tenants.factories import MembershipFactory, PersonFactory

pytestmark = pytest.mark.django_db


def _login(client, role="owner"):
    membership = MembershipFactory(role=role)
    client.force_login(membership.user)
    return membership.tenant


def _detail(gig):
    return reverse("gigs:detail", args=[gig.pk])


def _cachet_url(gig, member):
    return reverse("gigs:member-cachet", args=[gig.pk, member.pk])


def _fields(member, count="", amount=""):
    return {f"m{member.pk}-cachet_count": count, f"m{member.pk}-cachet_amount": amount}


def _member_on(gig, **kwargs):
    person = PersonFactory(tenant=gig.tenant, first_name="Léa", last_name="Chanteuse")
    return GigMemberFactory(gig=gig, person=person, name=person.full_name, **kwargs)


# --- showing the team ---------------------------------------------------------------------------


def test_the_owner_sees_the_cachet_fields_of_each_person(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    member = _member_on(gig)

    page = client.get(_detail(gig)).content.decode()

    assert "Équipe de la date" in page
    assert "Léa Chanteuse" in page
    assert f'action="{_cachet_url(gig, member)}"' in page
    assert "Montant brut" in page


def test_a_plain_member_sees_the_team_but_no_cachet(client):
    tenant = _login(client, role="member")
    gig = GigFactory(tenant=tenant)
    member = _member_on(gig, cachet_count=2, cachet_amount=Decimal("123.45"))

    page = client.get(_detail(gig)).content.decode()

    assert "Léa Chanteuse" in page
    assert "Montant brut" not in page
    assert "123" not in page
    assert _cachet_url(gig, member) not in page


def test_someone_added_by_hand_has_no_cachet_form_and_a_clear_note(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    GigMemberFactory(gig=gig, person=None, name="Invité Sans Fiche")

    page = client.get(_detail(gig)).content.decode()

    assert "Invité Sans Fiche" in page
    assert "sans fiche d'équipe" in page
    assert "Montant brut" not in page


# --- saving a cachet ----------------------------------------------------------------------------


def test_the_owner_saves_a_cachet_to_the_cent(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    member = _member_on(gig)

    response = client.post(_cachet_url(gig, member), _fields(member, "2", "150.50"))

    assert response.status_code == 302
    member.refresh_from_db()
    assert member.cachet_count == 2
    assert member.cachet_amount == Decimal("150.50")
    assert "Le cachet de Léa Chanteuse est enregistré." in client.get(response.url).content.decode()


def test_a_cachet_can_be_cleared(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    member = _member_on(gig, cachet_count=1, cachet_amount=Decimal("100"))

    client.post(_cachet_url(gig, member), _fields(member))

    member.refresh_from_db()
    assert member.cachet_count is None
    assert member.cachet_amount is None


@pytest.mark.parametrize(
    "count, amount", [("-1", "10"), ("100000", "10"), ("1", "-5"), ("abc", "10"), ("1", "x")]
)
def test_wrong_values_are_refused_and_nothing_changes(client, count, amount):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    member = _member_on(gig, cachet_count=3, cachet_amount=Decimal("90"))

    response = client.post(_cachet_url(gig, member), _fields(member, count, amount))

    assert response.status_code == 302
    member.refresh_from_db()
    assert (member.cachet_count, member.cachet_amount) == (3, Decimal("90.00"))
    assert "n'a pas pu être enregistré" in html.unescape(client.get(response.url).content.decode())


def test_a_plain_member_cannot_save_a_cachet(client):
    tenant = _login(client, role="member")
    gig = GigFactory(tenant=tenant)
    member = _member_on(gig)

    response = client.post(_cachet_url(gig, member), _fields(member, "1", "100"))

    assert response.status_code == 403
    member.refresh_from_db()
    assert member.cachet_amount is None


def test_the_cachet_view_only_accepts_post(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    member = _member_on(gig)

    assert client.get(_cachet_url(gig, member)).status_code == 405


def test_another_structure_gets_a_404_on_my_cachets(client):
    _login(client)
    foreign_gig = GigFactory()
    foreign_member = _member_on(foreign_gig)

    response = client.post(
        _cachet_url(foreign_gig, foreign_member), _fields(foreign_member, "1", "9")
    )

    assert response.status_code == 404
    foreign_member.refresh_from_db()
    assert foreign_member.cachet_amount is None


def test_a_member_of_another_date_is_not_reachable_through_this_date(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    other_gig = GigFactory(tenant=tenant)
    member = _member_on(other_gig)

    assert client.post(_cachet_url(gig, member), _fields(member, "1", "9")).status_code == 404


# --- putting people on the date -----------------------------------------------------------------


def test_a_person_of_the_team_joins_the_date_with_their_details(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    person = PersonFactory(tenant=tenant, first_name="Max", last_name="Basse", role="Basse")

    response = client.post(reverse("gigs:team-add", args=[gig.pk]), {"person": person.pk})

    assert response.status_code == 302
    assert response.url.endswith("#equipe")
    member = GigMember.objects.get(gig=gig)
    assert (member.person, member.name, member.role) == (person, "Max Basse", "Basse")


def test_the_same_person_cannot_join_twice(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    person = PersonFactory(tenant=tenant)
    url = reverse("gigs:team-add", args=[gig.pk])

    client.post(url, {"person": person.pk})
    response = client.post(url, {"person": person.pk})

    assert gig.members.count() == 1
    assert "fait déjà partie de cette date" in client.get(response.url).content.decode()


def test_a_person_of_another_structure_cannot_join(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    stranger = PersonFactory()

    client.post(reverse("gigs:team-add", args=[gig.pk]), {"person": stranger.pk})

    assert gig.members.count() == 0


@pytest.mark.parametrize("value", ["", "abc", "-3", "1;2"])
def test_a_wrong_person_is_ignored(client, value):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.post(reverse("gigs:team-add", args=[gig.pk]), {"person": value})

    assert response.status_code == 302
    assert gig.members.count() == 0


def test_the_cast_of_the_show_joins_in_one_click_without_duplicates(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)
    lead, bass = PersonFactory(tenant=tenant), PersonFactory(tenant=tenant)
    show.cast.add(lead, bass)
    gig = GigFactory(tenant=tenant, show=show)
    GigMemberFactory(gig=gig, person=lead, name=lead.full_name)
    url = reverse("gigs:team-add", args=[gig.pk])

    assert "Ajouter la personne de la distribution" in client.get(_detail(gig)).content.decode()
    client.post(url, {"cast": "1"})

    assert sorted(gig.members.values_list("person_id", flat=True)) == sorted([lead.pk, bass.pk])
    assert "distribution du spectacle" not in client.get(_detail(gig)).content.decode()


def test_another_structure_cannot_add_people_to_my_date(client):
    _login(client)
    foreign_gig = GigFactory()
    person = PersonFactory(tenant=foreign_gig.tenant)

    response = client.post(reverse("gigs:team-add", args=[foreign_gig.pk]), {"person": person.pk})

    assert response.status_code == 404
    assert foreign_gig.members.count() == 0


# --- the cachets never leave the owner's screen -------------------------------------------------


def test_a_cachet_never_shows_on_the_public_roadmap_or_its_pdf(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    _member_on(gig, cachet_count=7, cachet_amount=Decimal("4321.09"))
    roadmap = RoadmapFactory(gig=gig)
    publish(roadmap)
    client.logout()

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()
    pdf = client.get(reverse("roadmap-public-pdf", args=[roadmap.token])).content

    assert "Léa Chanteuse" in page
    assert "4321" not in page and "4 321" not in page
    assert b"4321" not in pdf


def test_the_owner_saves_the_hours_of_a_technician(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    member = _member_on(gig)

    client.post(_cachet_url(gig, member), {**_fields(member), f"m{member.pk}-hours": "7.5"})

    member.refresh_from_db()
    assert member.hours == Decimal("7.50")


def test_negative_hours_are_refused(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    member = _member_on(gig)

    client.post(_cachet_url(gig, member), {**_fields(member), f"m{member.pk}-hours": "-1"})

    member.refresh_from_db()
    assert member.hours is None


def test_a_plain_member_cannot_save_hours(client):
    tenant = _login(client, role="member")
    gig = GigFactory(tenant=tenant)
    member = _member_on(gig)

    response = client.post(_cachet_url(gig, member), {f"m{member.pk}-hours": "7"})

    assert response.status_code == 403
