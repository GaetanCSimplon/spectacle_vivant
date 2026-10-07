import pytest
from django.test import Client
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def logged_in(client):
    membership = MembershipFactory(role="member")
    client.force_login(membership.user)
    return client


def test_404_page_is_in_french_with_a_way_back(logged_in):
    response = logged_in.get("/une-page-qui-n-existe-pas/")

    content = response.content.decode()
    assert response.status_code == 404
    assert "Page introuvable" in content
    assert reverse("home") in content


def test_403_page_is_in_french(logged_in):
    response = logged_in.get(reverse("tenants:delete"))  # owner only

    assert response.status_code == 403
    assert "Accès refusé" in response.content.decode()


def test_csrf_failure_page_is_in_french():
    client = Client(enforce_csrf_checks=True)

    response = client.post(reverse("account_login"), {"login": "a@b.fr", "password": "x"})

    assert response.status_code == 403
    assert "Le formulaire a expiré" in response.content.decode()


def test_500_page_is_standalone_and_in_french(rf):
    from django.views.defaults import server_error

    response = server_error(rf.get("/"))

    content = response.content.decode()
    assert response.status_code == 500
    assert "Une erreur est survenue" in content
    assert "{%" not in content  # it renders without any template machinery or database


def test_skip_link_and_main_target_are_on_every_page(logged_in):
    content = logged_in.get(reverse("home")).content.decode()

    assert 'href="#contenu"' in content
    assert 'id="contenu"' in content


def test_the_share_link_field_has_a_label(logged_in):
    from apps.gigs.factories import GigFactory
    from apps.roadmaps import services
    from apps.roadmaps.factories import RoadmapFactory

    membership = MembershipFactory()
    logged_in.force_login(membership.user)
    roadmap = RoadmapFactory(gig=GigFactory(tenant=membership.tenant))
    services.publish(roadmap)

    response = logged_in.get(reverse("roadmaps:editor", args=[roadmap.gig_id]))

    assert 'aria-label="Adresse du lien de partage"' in response.content.decode()
