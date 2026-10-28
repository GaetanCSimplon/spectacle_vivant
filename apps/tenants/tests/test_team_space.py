"""The personal space of a team member: a secret link, no account, only their own dates."""

import datetime
import re

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.gigs.models import Gig
from apps.roadmaps.factories import LodgingFactory, MealFactory
from apps.roadmaps.services import get_or_create_roadmap

from .. import services
from ..factories import MembershipFactory, PersonFactory

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()


def _days(n):
    return TODAY + datetime.timedelta(days=n)


def _with_space(person):
    services.enable_team_space(person)
    person.refresh_from_db()
    return person


def _on_gig(person, **gig_fields):
    """A date of the person's structure on which the person is part of the team."""
    gig = GigFactory(tenant=person.tenant, **gig_fields)
    GigMemberFactory(gig=gig, tenant=person.tenant, person=person, name=person.full_name)
    return gig


def _space(client, person):
    return client.get(reverse("team-space", args=[person.access_token]))


# --- the owner's side ---------------------------------------------------------------------


def _owner(client, role="owner"):
    membership = MembershipFactory(role=role)
    client.force_login(membership.user)
    return membership.tenant


def test_the_owner_creates_and_revokes_the_link(client):
    tenant = _owner(client)
    person = PersonFactory(tenant=tenant)

    client.post(reverse("tenants:person-access-enable", args=[person.pk]))
    person.refresh_from_db()
    token = person.access_token
    card = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()
    assert len(token) >= 40 and f"/equipe/{token}/" in card

    client.post(reverse("tenants:person-access-revoke", args=[person.pk]))
    person.refresh_from_db()
    card = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()
    assert person.access_token == "" and token not in card and "Créer son lien personnel" in card


def test_a_new_link_is_never_the_old_one(client):
    tenant = _owner(client)
    person = PersonFactory(tenant=tenant)
    services.enable_team_space(person)
    old = person.access_token

    services.disable_team_space(person)
    services.enable_team_space(person)

    assert person.access_token not in ("", old)


def test_a_simple_member_cannot_create_or_revoke_a_link_nor_see_it(client):
    tenant = _owner(client, role="member")
    person = _with_space(PersonFactory(tenant=tenant))
    token = person.access_token

    created = client.post(reverse("tenants:person-access-enable", args=[person.pk]))
    revoked = client.post(reverse("tenants:person-access-revoke", args=[person.pk]))
    card = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()

    assert created.status_code == 403 and revoked.status_code == 403
    person.refresh_from_db()
    assert person.access_token == token
    assert token not in card and "Espace personnel" not in card


def test_another_structure_cannot_touch_my_members_link(client):
    person = _with_space(PersonFactory())
    token = person.access_token
    _owner(client)

    response = client.post(reverse("tenants:person-access-revoke", args=[person.pk]))

    assert response.status_code == 404
    person.refresh_from_db()
    assert person.access_token == token


def test_the_link_creation_is_post_only(client):
    tenant = _owner(client)
    person = PersonFactory(tenant=tenant)

    assert client.get(reverse("tenants:person-access-enable", args=[person.pk])).status_code == 405


def test_the_token_never_leaves_in_the_export_or_the_list(client):
    from ..data_export import build_export_zip

    tenant = _owner(client)
    person = _with_space(PersonFactory(tenant=tenant))

    listing = client.get(reverse("tenants:person-list")).content.decode()
    archive = build_export_zip(tenant, include_private=True).read()

    assert person.access_token not in listing
    assert person.access_token.encode() not in archive


# --- the person's side --------------------------------------------------------------------


def test_the_person_sees_their_coming_and_recent_dates_only(client):
    person = _with_space(PersonFactory(first_name="Léa"))
    coming = _on_gig(person, date=_days(5), show__title="Nuits d'été")
    recent = _on_gig(person, date=_days(-10), show__title="Concert récent")
    _on_gig(person, date=_days(-90), show__title="Trop ancien")
    other = _on_gig(PersonFactory(tenant=person.tenant), date=_days(6), show__title="Pas le sien")
    GigFactory(tenant=person.tenant, date=_days(7), show__title="Sans elle")

    page = _space(client, person).content.decode()

    assert "Bonjour Léa" in page
    assert "Nuits d&#x27;été" in page or "Nuits d'été" in page
    assert "Concert récent" in page and "Dates récentes" in page
    for hidden in ("Trop ancien", "Pas le sien", "Sans elle"):
        assert hidden not in page
    assert reverse("team-space-gig", args=[person.access_token, coming.pk]) in page
    assert reverse("team-space-gig", args=[person.access_token, recent.pk]) in page
    assert reverse("team-space-gig", args=[person.access_token, other.pk]) not in page


def test_a_cancelled_date_is_left_out(client):
    person = _with_space(PersonFactory())
    _on_gig(person, date=_days(5), show__title="Annulée", status=Gig.Status.CANCELLED)

    assert "Annulée" not in _space(client, person).content.decode()


def test_the_page_shows_no_money_and_no_private_data(client):
    person = _with_space(
        PersonFactory(
            average_fee="321.00",
            guso_number="GUSO-SECRET",
            social_security_number="185057800608491",
        )
    )
    _on_gig(person, date=_days(5), price="7777.00")

    page = _space(client, person).content.decode()

    for secret in ("7777", "321", "GUSO-SECRET", "185057800608491", "Prix"):
        assert secret not in page


def test_the_page_is_kept_out_of_caches_search_engines_and_referers(client):
    person = _with_space(PersonFactory())

    response = _space(client, person)

    assert response["Cache-Control"] == "no-store"
    assert "noindex" in response["X-Robots-Tag"]
    assert response["Referrer-Policy"] == "no-referrer"


@pytest.mark.parametrize("token", ["inconnu", "x" * 43])
def test_an_unknown_token_is_a_404(client, token):
    assert client.get(reverse("team-space", args=[token])).status_code == 404


def test_a_revoked_link_stops_working_at_once(client):
    person = _with_space(PersonFactory())
    token = person.access_token
    services.disable_team_space(person)

    assert client.get(reverse("team-space", args=[token])).status_code == 404


def test_a_member_without_a_link_is_not_reachable_with_an_empty_token(client):
    PersonFactory()  # access_token == ""

    assert services.person_for_token("") is None


# --- the roadmap of a date ----------------------------------------------------------------


def test_the_roadmap_opens_even_if_the_general_share_link_is_off(client):
    person = _with_space(PersonFactory())
    gig = _on_gig(person, date=_days(5), show__title="Nuits d'été")
    roadmap = get_or_create_roadmap(gig)
    LodgingFactory(roadmap=roadmap, tenant=roadmap.tenant, name="Hôtel Mistral")
    MealFactory(roadmap=roadmap, tenant=roadmap.tenant, place="Chez Paul")
    assert not roadmap.is_published

    response = client.get(reverse("team-space-gig", args=[person.access_token, gig.pk]))
    page = response.content.decode()

    assert response.status_code == 200
    assert "Hôtel Mistral" in page and "Chez Paul" in page
    assert reverse("team-space", args=[person.access_token]) in page  # back to my dates
    assert reverse("team-space-pdf", args=[person.access_token, gig.pk]) in page
    assert response["Cache-Control"] == "no-store"


def test_the_roadmap_page_shows_no_money(client):
    person = _with_space(PersonFactory())
    gig = _on_gig(person, date=_days(5), price="7777.00")
    get_or_create_roadmap(gig)

    page = client.get(
        reverse("team-space-gig", args=[person.access_token, gig.pk])
    ).content.decode()

    assert "7777" not in page


def test_a_date_without_roadmap_says_so_and_creates_nothing(client):
    from apps.roadmaps.models import Roadmap

    person = _with_space(PersonFactory())
    gig = _on_gig(person, date=_days(5))

    response = client.get(reverse("team-space-gig", args=[person.access_token, gig.pk]))

    assert response.status_code == 200 and "pas encore prête" in response.content.decode()
    assert not Roadmap.objects.filter(gig=gig).exists()


def test_a_date_of_somebody_else_is_a_404(client):
    person = _with_space(PersonFactory())
    colleague = PersonFactory(tenant=person.tenant)
    their_gig = _on_gig(colleague, date=_days(5))
    get_or_create_roadmap(their_gig)
    foreign_gig = GigFactory(date=_days(5))

    for gig in (their_gig, foreign_gig):
        url = reverse("team-space-gig", args=[person.access_token, gig.pk])
        assert client.get(url).status_code == 404
        assert client.get(url + "pdf/").status_code == 404


def test_the_pdf_of_my_date_opens(client):
    person = _with_space(PersonFactory())
    gig = _on_gig(person, date=_days(5))
    get_or_create_roadmap(gig)

    response = client.get(reverse("team-space-pdf", args=[person.access_token, gig.pk]))

    assert response.status_code == 200 and response.content.startswith(b"%PDF-")


def test_another_tenants_token_never_shows_this_tenants_dates(client):
    mine = _with_space(PersonFactory())
    theirs = _with_space(PersonFactory())
    _on_gig(mine, date=_days(5), show__title="Spectacle de A")
    _on_gig(theirs, date=_days(5), show__title="Spectacle de B")

    page = _space(client, theirs).content.decode()

    assert "Spectacle de B" in page and "Spectacle de A" not in page


# --- seeing the space as the person does ---------------------------------------------------------


def test_the_owner_can_open_the_space_from_the_card(client):
    tenant = _owner(client)
    person = _with_space(PersonFactory(tenant=tenant))

    card = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()

    assert "Voir son espace" in card
    link = re.search(r'<a href="([^"]+)"[^>]*>Voir son espace</a>', card).group(1)
    assert link.endswith(f"/equipe/{person.access_token}/")
    assert 'target="_blank"' in card.split("Voir son espace")[0].rsplit("<a ", 1)[1]


def test_without_a_link_there_is_nothing_to_open(client):
    tenant = _owner(client)
    person = PersonFactory(tenant=tenant)

    card = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()

    assert "Voir son espace" not in card and "Créer son lien personnel" in card


def test_a_simple_member_never_gets_the_link_to_the_space(client):
    tenant = _owner(client, role="member")
    person = _with_space(PersonFactory(tenant=tenant))

    card = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()

    assert "Voir son espace" not in card and person.access_token not in card
