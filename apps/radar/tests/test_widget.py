import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(client):
    membership = MembershipFactory(tenant__licence_exempt=True)
    client.force_login(membership.user)
    return membership


def test_every_connected_page_carries_the_radar_widget(client, owner):
    content = client.get(reverse("gigs:list")).content.decode()

    assert 'id="radar-button"' in content and 'id="radar-modal"' in content
    assert reverse("radar:button") in content
    assert "htmx:afterRequest" in content  # the notification follows every action


def test_the_widget_looks_at_the_date_being_shown(client, owner):
    gig = GigFactory(tenant=owner.tenant)

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert f"{reverse('radar:button')}?gig={gig.pk}" in content


def test_the_widget_is_absent_for_the_logged_out(client):
    assert "radar-button" not in client.get(reverse("home")).content.decode()


def test_the_button_writes_the_count_and_opens_the_modal(client, owner):
    response = client.get(reverse("radar:button"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Radar : 2 points à regarder" in content  # the structure has no SIRET, no IBAN
    assert "radar.svg" in content and reverse("radar:panel") in content


def test_the_button_follows_a_change(client, owner):
    before = client.get(reverse("radar:button")).content.decode()
    GigFactory(tenant=owner.tenant, price="0.00")

    after = client.get(reverse("radar:button")).content.decode()

    assert "Radar : 2 points à regarder" in before
    assert "Radar : 4 points à regarder" in after or "Radar : 5 points à regarder" in after


def test_the_panel_lists_the_findings_of_one_date_and_of_the_structure(client, owner):
    gig = GigFactory(tenant=owner.tenant, price="0.00")
    other = GigFactory(tenant=owner.tenant, price="0.00")

    content = client.get(reverse("radar:panel"), {"gig": gig.pk}).content.decode()

    assert reverse("gigs:price", args=[gig.pk]) in content
    assert reverse("gigs:price", args=[other.pk]) not in content
    assert "Pourquoi cette alerte ?" in content and "Corriger" in content


def test_the_panel_without_a_date_lists_everything(client, owner):
    gig = GigFactory(tenant=owner.tenant, price="0.00")

    content = client.get(reverse("radar:panel")).content.decode()

    assert reverse("gigs:price", args=[gig.pk]) in content


def test_another_tenants_date_is_a_404_and_nothing_leaks(client, owner):
    foreign = GigFactory(price="0.00")

    for name in ("radar:button", "radar:panel"):
        assert client.get(reverse(name), {"gig": foreign.pk}).status_code == 404
    assert (
        reverse("gigs:price", args=[foreign.pk])
        not in client.get(reverse("radar:panel")).content.decode()
    )


def test_the_fragments_need_a_login(client):
    for name in ("radar:button", "radar:panel"):
        assert client.get(reverse(name)).status_code == 302


def test_the_panel_is_a_native_dialog_opened_at_once_like_the_checklist(client, owner):
    content = client.get(reverse("radar:panel")).content.decode()

    assert "<dialog" in content and "showModal()" in content and "Fermer" in content


def test_the_checklist_button_has_an_id_so_that_radar_can_move_aside(client, owner):
    gig = GigFactory(tenant=owner.tenant)

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert 'id="checklist-button"' in content
