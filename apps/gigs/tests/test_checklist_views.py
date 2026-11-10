"""The checklist modal: open, tick, reset (F-83)."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory, TenantFactory

from .. import checklist
from ..factories import GigFactory
from ..models import Gig, GigChecklist

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def membership(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership


@pytest.fixture
def gig(membership):
    return GigFactory(tenant=membership.tenant)


def _url(name, gig):
    return reverse(f"gigs:{name}", args=[gig.pk])


def _tick(client, gig, key, on=True, **extra):
    data = {"item": key, **({"value": "true"} if on else {})}
    return client.post(_url("checklist-item", gig), data, **extra)


def _checked(content):
    """How many boxes of the HTML are ticked (the JS of the page also says "checked")."""
    return content.count('value="true" checked')


def _done(gig):
    return {
        item["key"]
        for section in checklist.checklist_sections(gig)
        for item in section["items"]
        if item["done"]
    }


@pytest.mark.parametrize("name", ["checklist", "checklist-item", "checklist-reset"])
def test_every_route_requires_login(client, name):
    other = GigFactory()

    response = (
        client.post(_url(name, other)) if name != "checklist" else client.get(_url(name, other))
    )

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_the_modal_shows_the_title_the_sections_and_sixteen_boxes(client, gig):
    response = client.get(_url("checklist", gig), **HTMX)

    content = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in content and "<dialog" in content
    assert "Checklist contractualisation" in content
    assert "Cochez les éléments réalisés pour cette date." in content
    for title in (
        "Avant confirmation de la date",
        "Contrat",
        "Documents techniques",
        "Facturation",
        "Intervenants / intermittents",
        "Clôture",
    ):
        assert title in content
    assert content.count('type="checkbox"') == 16
    assert _checked(content) == 0
    assert "Fermer" in content and "Réinitialiser" in content


def test_the_sections_keep_the_order_of_the_spec(client, gig):
    content = client.get(_url("checklist", gig), **HTMX).content.decode()

    positions = [
        content.index(title)
        for title in (
            "Avant confirmation de la date",
            "Contrat</h3>",
            "Documents techniques",
            "Facturation",
            "Intervenants / intermittents",
            "Clôture",
        )
    ]
    assert positions == sorted(positions)


def test_opening_the_checklist_creates_nothing(client, gig):
    client.get(_url("checklist", gig), **HTMX)
    client.get(_url("checklist", gig))

    assert not GigChecklist.objects.exists()


def test_the_page_without_javascript(client, gig):
    response = client.get(_url("checklist", gig))

    content = response.content.decode()
    assert response.status_code == 200 and "<html" in content
    assert gig.show.title in content
    assert content.count('type="checkbox"') == 16
    assert "Retour à la date" in content


def test_there_is_no_to_do_line_and_no_progress(client, gig):
    _tick(client, gig, "quote_sent")

    content = client.get(_url("checklist", gig), **HTMX).content.decode().lower()

    for forbidden in ("à faire", "en cours", "progress", "avancement"):
        assert forbidden not in content


def test_ticking_saves_at_once_and_answers_with_the_saved_box(client, gig):
    response = _tick(client, gig, "quote_sent", **HTMX)

    content = response.content.decode()
    assert response.status_code == 200
    assert _done(gig) == {"quote_sent"}
    assert 'id="checklist-quote_sent"' in content and _checked(content) == 1
    assert 'id="checklist-updated"' in content and 'hx-swap-oob="true"' in content
    assert "Dernière modification" in content


def test_a_tick_is_still_there_after_closing_and_reopening(client, gig):
    _tick(client, gig, "contract_signed", **HTMX)

    content = client.get(_url("checklist", gig), **HTMX).content.decode()

    row = content.split('id="checklist-contract_signed"')[1].split("</li>")[0]
    assert _checked(row) == 1
    assert _checked(content) == 1


def test_unticking(client, gig):
    _tick(client, gig, "rider_sent")

    response = _tick(client, gig, "rider_sent", on=False, **HTMX)

    assert _done(gig) == set()
    assert _checked(response.content.decode()) == 0


def test_ticking_one_box_never_changes_another(client, gig):
    for key in ("quote_sent", "deposit_received", "closed"):
        _tick(client, gig, key, **HTMX)

    _tick(client, gig, "deposit_received", on=False, **HTMX)

    assert _done(gig) == {"quote_sent", "closed"}


def test_an_unknown_box_is_a_400_and_writes_nothing(client, gig):
    for item in ("nope", "", "devis_envoye"):
        response = client.post(_url("checklist-item", gig), {"item": item, "value": "true"}, **HTMX)
        assert response.status_code == 400

    assert not GigChecklist.objects.exists()


def test_the_tick_without_javascript_goes_back_to_the_page(client, gig):
    response = _tick(client, gig, "quote_sent")

    assert response.status_code == 302
    assert response.url == _url("checklist", gig)
    assert _done(gig) == {"quote_sent"}


def test_the_tick_view_is_post_only(client, gig):
    assert client.get(_url("checklist-item", gig)).status_code == 405
    assert client.get(_url("checklist-reset", gig)).status_code == 405


def test_reset_unticks_everything(client, gig):
    for key in ("quote_sent", "closed"):
        _tick(client, gig, key)

    response = client.post(_url("checklist-reset", gig), **HTMX)

    assert response.status_code == 200
    assert _done(gig) == set()
    assert _checked(response.content.decode()) == 0


def test_reset_without_javascript_goes_back_to_the_page(client, gig):
    _tick(client, gig, "quote_sent")

    response = client.post(_url("checklist-reset", gig))

    assert response.status_code == 302 and response.url == _url("checklist", gig)
    assert _done(gig) == set()


def test_reset_asks_for_a_confirmation_and_a_failed_save_has_its_message(client, gig):
    content = client.get(_url("checklist", gig), **HTMX).content.decode()

    assert "Réinitialiser toutes les cases ?" in content
    assert "Modification non enregistrée. Réessayez." in content


def test_a_checklist_belongs_to_its_own_date(client, membership, gig):
    other = GigFactory(tenant=membership.tenant)
    _tick(client, gig, "quote_sent")

    assert _done(other) == set()
    content = client.get(_url("checklist", other), **HTMX).content.decode()
    assert _checked(content) == 0


def test_any_member_can_tick(client, membership, gig):
    member = MembershipFactory(role="member", tenant=membership.tenant)
    client.force_login(member.user)

    assert _tick(client, gig, "quote_sent", **HTMX).status_code == 200
    assert _done(gig) == {"quote_sent"}


def test_ticking_changes_nothing_else_on_the_date(client, gig):
    for key in checklist.ITEM_KEYS:
        _tick(client, gig, key)

    gig.refresh_from_db()
    assert gig.status == Gig.Status.OPTION and not gig.price_changes.exists()


def test_another_tenants_date_is_a_404_everywhere(client, membership):
    foreign = GigFactory(tenant=TenantFactory())

    assert client.get(_url("checklist", foreign)).status_code == 404
    assert client.get(_url("checklist", foreign), **HTMX).status_code == 404
    assert _tick(client, foreign, "quote_sent", **HTMX).status_code == 404
    assert client.post(_url("checklist-reset", foreign), **HTMX).status_code == 404
    assert not GigChecklist.objects.exists()


def test_the_buttons_are_on_the_date_and_on_the_contract_page(client, gig):
    for url in (
        reverse("gigs:detail", args=[gig.pk]),
        reverse("documents:contract-history", args=[gig.pk]),
    ):
        content = client.get(url).content.decode()

        assert "Checklist contractualisation" in content
        assert f'hx-get="{_url("checklist", gig)}"' in content
        assert 'id="checklist-modal"' in content


def test_headings_follow_the_page_title_without_skipping_a_level(client, gig):
    """Audit axe-core 2026-11-10: the page (h1) has h2 sections; the modal (h2) has h3."""
    page = client.get(_url("checklist", gig)).content.decode()
    modal = client.get(_url("checklist", gig), **HTMX).content.decode()

    assert "<h1" in page and '<h2 id="checklist-section-1"' in page and "<h3" not in page
    assert '<h3 id="checklist-section-1"' in modal
