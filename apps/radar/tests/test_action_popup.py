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
    gig = GigFactory(tenant=tenant, status=Gig.Status.CONFIRMED, promoter__siret="12345678901234")
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


def test_each_engaging_action_has_its_own_alerts():
    membership = MembershipFactory(
        tenant__siret="12345678901234", tenant__city="Pau", tenant__licence_exempt=True
    )
    gig = _confirmed_gig(membership.tenant)

    invoice = [f.code for f in rules.for_action("invoice_issue", gig)]
    share = [f.code for f in rules.for_action("roadmap_share", gig)]

    assert invoice == ["RAD-02"]
    # Far from the concert, the missing times still count at the moment of sharing.
    assert share == ["RAD-26", "RAD-20"] or sorted(share) == ["RAD-20", "RAD-26"]


def test_sharing_the_roadmap_shows_the_alerts_and_still_shares(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = _confirmed_gig(membership.tenant)
    url = reverse("roadmaps:share", args=[gig.pk, "activer"])

    page = client.get(url).content.decode()
    editor = client.get(reverse("roadmaps:editor", args=[gig.pk])).content.decode()
    response = client.post(url)

    assert "Radar : avant de continuer" in page and "Continuer quand même" in page
    assert f'href="{url}"' in editor  # a link to the page, not a one-click form
    assert response.status_code == 302
    gig.roadmap.refresh_from_db()
    assert gig.roadmap.is_published


def test_stopping_the_share_by_get_just_goes_back_to_the_editor(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = _confirmed_gig(membership.tenant)

    response = client.get(reverse("roadmaps:share", args=[gig.pk, "arreter"]))

    assert response.status_code == 302


# --- the same pop-ups as Radar's modal (htmx) -------------------------------------------------

HTMX = {"HTTP_HX_REQUEST": "true"}


def test_the_history_links_open_radar_s_modal_through_htmx(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = _generated(membership.tenant)

    content = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()

    for name, args in (("contract-sent", [gig.pk, "envoye"]), ("contract-sign", [gig.pk])):
        assert f'hx-get="{reverse(f"documents:{name}", args=args)}"' in content
    assert content.count('hx-target="#radar-modal"') >= 2


def test_the_send_modal_is_a_dialog_with_the_alerts_and_posts_anyway(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = _generated(membership.tenant)
    url = reverse("documents:contract-sent", args=[gig.pk, "envoye"])

    modal = client.get(url, **HTMX).content.decode()

    assert "<dialog" in modal and "<html" not in modal
    assert "Radar : avant de continuer" in modal and "Continuer quand même" in modal
    assert client.post(url).status_code == 302
    gig.contract.refresh_from_db()
    assert gig.contract.sent_at is not None


def test_the_sign_modal_is_a_dialog_with_the_form_and_the_alerts(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = _generated(membership.tenant)

    modal = client.get(reverse("documents:contract-sign", args=[gig.pk]), **HTMX)
    content = modal.content.decode()

    assert "<dialog" in content and "<html" not in content
    assert "Radar : avant de continuer" in content and 'enctype="multipart/form-data"' in content


def test_a_refusal_in_the_modal_redirects_the_whole_page(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = _confirmed_gig(membership.tenant)  # no contract generated yet

    response = client.get(reverse("documents:contract-sign", args=[gig.pk]), **HTMX)

    assert response.status_code == 200
    assert response["HX-Redirect"] == reverse("documents:contract-history", args=[gig.pk])


def test_another_structure_gets_a_404_in_both_modals(client):
    gig = _generated(MembershipFactory().tenant)
    client.force_login(MembershipFactory().user)

    assert (
        client.get(reverse("documents:contract-sent", args=[gig.pk, "envoye"]), **HTMX).status_code
        == 404
    )
    assert client.get(reverse("documents:contract-sign", args=[gig.pk]), **HTMX).status_code == 404


def test_the_share_modal_is_a_dialog_and_the_editor_link_opens_it(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = _confirmed_gig(membership.tenant)
    url = reverse("roadmaps:share", args=[gig.pk, "activer"])

    modal = client.get(url, **HTMX).content.decode()
    editor = client.get(reverse("roadmaps:editor", args=[gig.pk])).content.decode()

    assert "<dialog" in modal and "<html" not in modal
    assert "Radar : avant de continuer" in modal and "Continuer quand même" in modal
    assert f'hx-get="{url}"' in editor and 'hx-target="#radar-modal"' in editor


def test_another_structure_gets_a_404_in_the_share_modal(client):
    gig = _confirmed_gig(MembershipFactory().tenant)
    client.force_login(MembershipFactory().user)

    response = client.get(reverse("roadmaps:share", args=[gig.pk, "activer"]), **HTMX)

    assert response.status_code == 404
