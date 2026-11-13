import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


def test_the_page_requires_a_login(client):
    response = client.get(reverse("radar:radar"))

    assert response.status_code == 302


def test_the_page_lists_the_findings_with_a_way_to_correct(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant, price="0.00")

    content = client.get(reverse("radar:radar")).content.decode()

    assert "Ce qui coince" in content
    assert "Important" in content  # the structure has no SIRET
    assert "le prix de cession n&#x27;est pas renseigné" in content
    assert reverse("gigs:price", args=[gig.pk]) in content
    assert "Pourquoi cette alerte ?" in content


def test_another_structure_sees_none_of_it(client):
    mine = MembershipFactory()
    GigFactory(tenant=mine.tenant, price="0.00", promoter__name="Mairie secrète")
    other = MembershipFactory()
    client.force_login(other.user)

    content = client.get(reverse("radar:radar")).content.decode()

    assert "Mairie secrète" not in content


def test_the_navigation_links_to_radar(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    content = client.get(reverse("home")).content.decode()

    assert reverse("radar:radar") in content
