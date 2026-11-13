import pytest
from django.urls import reverse

from apps.documents.services import generate_contract_pdf
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.radar import rules
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _confirmed_gig(tenant):
    gig = GigFactory(tenant=tenant, status=Gig.Status.CONFIRMED)
    gig.refresh_from_db()
    return gig


def test_an_action_only_lists_the_alerts_that_bear_on_it():
    membership = MembershipFactory()
    gig = _confirmed_gig(membership.tenant)  # also has RAD-26 (venue without place)

    codes = [f.code for f in rules.for_action("contract_send", gig)]

    assert codes == ["RAD-01", "RAD-10"]  # not RAD-26, not RAD-02


def test_the_send_page_shows_the_alerts_and_lets_the_user_go_on(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = _confirmed_gig(membership.tenant)

    content = client.get(
        reverse("documents:contract-sent", args=[gig.pk, "envoye"])
    ).content.decode()

    assert "Radar : avant de continuer" in content
    assert "Continuer quand même" in content
    assert reverse("documents:contract-complete", args=[gig.pk]) in content


def test_the_send_page_asks_a_plain_confirmation_without_alerts(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant, status=Gig.Status.OPTION)
    membership.tenant.siret = "12345678901234"
    membership.tenant.address = "1 rue"
    membership.tenant.save()

    content = client.get(
        reverse("documents:contract-sent", args=[gig.pk, "envoye"])
    ).content.decode()

    assert "Radar : avant de continuer" not in content
    assert "Confirmer : le contrat est envoyé" in content


def _generated(tenant):
    gig = _confirmed_gig(tenant)
    generate_contract_pdf(gig)
    return gig


def test_the_history_links_to_the_page_while_radar_has_something_to_say(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = _generated(membership.tenant)
    send_url = reverse("documents:contract-sent", args=[gig.pk, "envoye"])

    content = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()

    assert f'href="{send_url}"' in content  # a link to the page, not a one-click form
    assert f'action="{send_url}"' not in content


def test_signing_shows_the_alerts_and_still_signs(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = _generated(membership.tenant)
    url = reverse("documents:contract-sign", args=[gig.pk])

    page = client.get(url).content.decode()
    response = client.post(url)

    assert "Radar : avant de continuer" in page and "Continuer quand même" in page
    assert response.status_code == 302  # nothing blocks
    gig.refresh_from_db()
    assert gig.status == Gig.Status.SIGNED


def test_another_structure_gets_a_404_on_the_send_page(client):
    gig = _confirmed_gig(MembershipFactory().tenant)
    client.force_login(MembershipFactory().user)

    response = client.get(reverse("documents:contract-sent", args=[gig.pk, "envoye"]))

    assert response.status_code == 404
