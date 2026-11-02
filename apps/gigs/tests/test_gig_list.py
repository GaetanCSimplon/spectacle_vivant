import datetime

import pytest
from django.urls import reverse

from apps.roadmaps.factories import RoadmapFactory
from apps.tenants.factories import MembershipFactory

from ..factories import GigFactory
from ..models import Gig

pytestmark = pytest.mark.django_db

TODAY = datetime.date.today()


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def test_list_requires_login(client):
    response = client.get(reverse("gigs:list"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_empty_list_invites_to_create_a_gig(client):
    _login(client)

    response = client.get(reverse("gigs:list"))

    assert response.status_code == 200
    assert "pas encore de date" in response.content.decode()


def test_list_splits_upcoming_and_past_gigs_in_order(client):
    tenant = _login(client)
    later = GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=30))
    sooner = GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=5))
    today = GigFactory(tenant=tenant, date=TODAY)
    recent = GigFactory(tenant=tenant, date=TODAY - datetime.timedelta(days=5))
    old = GigFactory(tenant=tenant, date=TODAY - datetime.timedelta(days=90))

    response = client.get(reverse("gigs:list"))

    assert list(response.context["upcoming_gigs"]) == [today, sooner, later]
    assert list(response.context["past_gigs"]) == [recent, old]


def test_list_does_not_show_other_tenants_gigs(client):
    tenant = _login(client)
    mine = GigFactory(tenant=tenant)
    other = GigFactory(show__title="Spectacle secret de B")

    response = client.get(reverse("gigs:list"))

    assert list(response.context["object_list"]) == [mine]
    assert other.show.title not in response.content.decode()
    assert response.status_code == 200


# --- roadmap shortcut --------------------------------------------------------


def _roadmap_links(content, gig):
    editor = reverse("roadmaps:editor", args=[gig.pk])
    return content.count(f'href="{editor}"'), content.count(f'href="{editor}#partage"')


def test_each_gig_links_to_its_roadmap_and_its_sharing(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=3))

    content = client.get(reverse("gigs:list")).content.decode()

    assert _roadmap_links(content, gig) == (1, 1)


def test_the_switch_says_whether_the_roadmap_is_shared(client):
    tenant = _login(client)
    shared = GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=3))
    RoadmapFactory(gig=shared, is_published=True, token="a-secret-token")
    GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=4))  # no roadmap yet
    stopped = GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=5))
    RoadmapFactory(gig=stopped, is_published=False)

    content = client.get(reverse("gigs:list")).content.decode()

    assert content.count("Non partagée") == 2
    assert content.count("Partagée") == 1


def test_the_secret_link_never_appears_in_the_list(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=3))
    RoadmapFactory(gig=gig, is_published=True, token="a-secret-token")

    content = client.get(reverse("gigs:list")).content.decode()

    assert "a-secret-token" not in content


def test_a_cancelled_gig_has_no_roadmap_shortcut(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=Gig.Status.CANCELLED)

    content = client.get(reverse("gigs:list")).content.decode()

    assert _roadmap_links(content, gig) == (0, 0)


def test_the_shortcut_only_shows_in_the_gig_list(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=3))

    content = client.get(reverse("home")).content.decode()

    assert "Non partagée" not in content
    assert _roadmap_links(content, gig)[1] == 0


def test_the_shortcut_is_kept_when_a_filter_swaps_the_list(client):
    tenant = _login(client)
    GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=3))

    content = client.get(reverse("gigs:list"), HTTP_HX_REQUEST="true").content.decode()

    assert "Non partagée" in content


def test_the_shortcut_of_another_tenant_is_never_shown(client):
    _login(client)
    other = GigFactory(date=TODAY + datetime.timedelta(days=3))
    RoadmapFactory(gig=other, is_published=True, token="other-secret")

    content = client.get(reverse("gigs:list")).content.decode()

    assert reverse("roadmaps:editor", args=[other.pk]) not in content
    assert "other-secret" not in content
