"""The boxes of the date page: tick and untick (F-83)."""

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


@pytest.mark.parametrize("name", ["checklist", "checklist-item"])
def test_every_route_requires_login(client, name):
    other = GigFactory()

    response = (
        client.post(_url(name, other)) if name != "checklist" else client.get(_url(name, other))
    )

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_opening_the_date_page_creates_nothing(client, gig):
    client.get(_url("detail", gig))

    assert not GigChecklist.objects.exists()


def test_ticking_saves_at_once_and_answers_with_the_saved_box(client, gig):
    response = _tick(client, gig, "rider_sent", **HTMX)

    content = response.content.decode()
    assert response.status_code == 200
    assert _done(gig) == {"rider_sent"}
    assert 'id="checklist-rider_sent"' in content and _checked(content) == 1


def test_a_tick_is_still_there_after_closing_and_reopening(client, gig):
    _tick(client, gig, "dpae_receipt_received", **HTMX)

    content = client.get(_url("detail", gig)).content.decode()

    row = content.split('id="checklist-dpae_receipt_received"')[1].split("</li>")[0]
    assert _checked(row) == 1
    assert _checked(content) == 1


def test_unticking(client, gig):
    _tick(client, gig, "rider_sent")

    response = _tick(client, gig, "rider_sent", on=False, **HTMX)

    assert _done(gig) == set()
    assert _checked(response.content.decode()) == 0


def test_ticking_one_box_never_changes_another(client, gig):
    for key in ("rider_sent", "dpae_sent", "closed"):
        _tick(client, gig, key, **HTMX)

    _tick(client, gig, "dpae_sent", on=False, **HTMX)

    assert _done(gig) == {"rider_sent", "closed"}


def test_an_unknown_box_is_a_400_and_writes_nothing(client, gig):
    for item in ("nope", "", "devis_envoye"):
        response = client.post(_url("checklist-item", gig), {"item": item, "value": "true"}, **HTMX)
        assert response.status_code == 400

    assert not GigChecklist.objects.exists()


def test_the_tick_without_javascript_goes_back_to_the_date_page(client, gig):
    response = _tick(client, gig, "rider_sent")

    assert response.status_code == 302
    assert response.url == _url("detail", gig) + "#checklist-rider_sent"
    assert _done(gig) == {"rider_sent"}


def test_the_tick_view_is_post_only(client, gig):
    assert client.get(_url("checklist-item", gig)).status_code == 405


def test_a_checklist_belongs_to_its_own_date(client, membership, gig):
    other = GigFactory(tenant=membership.tenant)
    _tick(client, gig, "rider_sent")

    assert _done(other) == set()
    content = client.get(_url("detail", other)).content.decode()
    assert _checked(content) == 0


def test_any_member_can_tick(client, membership, gig):
    member = MembershipFactory(role="member", tenant=membership.tenant)
    client.force_login(member.user)

    assert _tick(client, gig, "rider_sent", **HTMX).status_code == 200
    assert _done(gig) == {"rider_sent"}


def test_ticking_changes_nothing_else_on_the_date(client, gig):
    for key in checklist.ITEM_KEYS:
        _tick(client, gig, key)

    gig.refresh_from_db()
    assert gig.status == Gig.Status.OPTION and not gig.price_changes.exists()


def test_another_tenants_date_is_a_404_everywhere(client, membership):
    foreign = GigFactory(tenant=TenantFactory())

    assert client.get(_url("checklist", foreign)).status_code == 404
    assert client.get(_url("checklist", foreign), **HTMX).status_code == 404
    assert _tick(client, foreign, "rider_sent", **HTMX).status_code == 404
    assert not GigChecklist.objects.exists()


def test_the_former_checklist_address_leads_to_the_date_page(client, gig):
    response = client.get(_url("checklist", gig))

    assert response.status_code == 302 and response.url == _url("detail", gig)


def test_the_floating_button_is_gone_from_the_date_and_the_contract_page(client, gig):
    for url in (_url("detail", gig), reverse("documents:contract-history", args=[gig.pk])):
        content = client.get(url).content.decode()

        assert "checklist-button" not in content and "checklist-modal" not in content
