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
    assert "Votre action n'a pas pu être enregistrée" in response.content.decode()


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


def _csrf_refused(client=None, **extra):
    client = client or Client(enforce_csrf_checks=True)
    return client.post(reverse("account_login"), {"login": "a@b.fr", "password": "x"}, **extra)


def test_csrf_failure_page_does_not_claim_the_form_expired():
    content = _csrf_refused().content.decode()

    assert "a expiré" not in content
    assert "Rien n'a été enregistré" in content
    # Every usual cause is listed, not only the time.
    assert "restée ouverte trop longtemps" in content
    assert "dans un autre onglet" in content
    assert "bloque les cookies" in content


def test_csrf_failure_page_gives_the_technical_reason_in_a_fold():
    content = _csrf_refused(HTTP_ORIGIN="null").content.decode()

    assert "Détail technique" in content
    assert "Origin checking failed" in content


def test_csrf_failure_page_is_not_a_login_trap_for_a_visitor_without_account():
    content = _csrf_refused().content.decode()

    assert "Retour à l'accueil" not in content  # the home page would ask for a login


def test_csrf_failure_page_offers_the_home_page_to_a_logged_in_user(logged_in):
    membership = MembershipFactory()
    client = Client(enforce_csrf_checks=True)
    client.force_login(membership.user)

    response = client.post(reverse("tenants:settings"), {"name": "x"})

    assert response.status_code == 403
    assert "Retour à l'accueil" in response.content.decode()


def test_the_403_page_does_not_blame_the_user_for_something_else(logged_in):
    member = MembershipFactory(role="member")
    logged_in.force_login(member.user)

    response = logged_in.get(reverse("tenants:delete"))

    content = response.content.decode()
    assert response.status_code == 403
    assert "réservée au propriétaire de la structure" in content
    assert "Retour à l'accueil" in content
