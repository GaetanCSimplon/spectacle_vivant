import datetime

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from ..factories import GigFactory

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
