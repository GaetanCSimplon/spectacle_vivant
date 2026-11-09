import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from .. import services
from ..factories import GigFactory
from ..models import Gig

pytestmark = pytest.mark.django_db

S = Gig.Status


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


# --- service -------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (S.OPTION, S.CONFIRMED),
        (S.OPTION, S.CANCELLED),
        (S.CONFIRMED, S.SIGNED),
        (S.CONFIRMED, S.CANCELLED),
        (S.SIGNED, S.CANCELLED),
    ],
)
def test_allowed_transitions(start, target):
    gig = GigFactory(status=start)

    services.change_status(gig, target)

    gig.refresh_from_db()
    assert gig.status == target


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (S.OPTION, S.OPTION),
        (S.OPTION, S.SIGNED),  # signing needs the contract step first
        (S.CONFIRMED, S.OPTION),
        (S.CONFIRMED, S.CONFIRMED),
        (S.SIGNED, S.OPTION),
        (S.SIGNED, S.CONFIRMED),
        (S.CANCELLED, S.OPTION),  # only reactivate_gig() may do this (RG-04)
        (S.CANCELLED, S.CONFIRMED),
        (S.CANCELLED, S.SIGNED),
    ],
)
def test_forbidden_transitions_change_nothing(start, target):
    gig = GigFactory(status=start)

    with pytest.raises(services.InvalidTransition):
        services.change_status(gig, target)

    gig.refresh_from_db()
    assert gig.status == start


def test_reactivating_a_cancelled_gig_puts_it_back_in_option():
    gig = GigFactory(status=S.CANCELLED)

    services.reactivate_gig(gig)

    gig.refresh_from_db()
    assert gig.status == S.OPTION


@pytest.mark.parametrize("status", [S.OPTION, S.CONFIRMED, S.SIGNED])
def test_only_a_cancelled_gig_can_be_reactivated(status):
    gig = GigFactory(status=status)

    with pytest.raises(services.InvalidTransition):
        services.reactivate_gig(gig)

    gig.refresh_from_db()
    assert gig.status == status


def test_a_stale_gig_object_cannot_apply_an_outdated_transition():
    gig = GigFactory(status=S.OPTION)
    stale = Gig.objects.get(pk=gig.pk)
    services.change_status(gig, S.CANCELLED)

    with pytest.raises(services.InvalidTransition):
        services.change_status(stale, S.CONFIRMED)

    gig.refresh_from_db()
    assert gig.status == S.CANCELLED


# --- detail page ---------------------------------------------------------


def test_detail_requires_login(client):
    gig = GigFactory()

    response = client.get(reverse("gigs:detail", args=[gig.pk]))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_detail_shows_the_gig(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, price="800.00")

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert gig.show.title in content
    assert gig.promoter.name in content
    assert gig.venue.name in content
    assert "Option" in content
    assert reverse("documents:contract-complete", args=[gig.pk]) in content


@pytest.mark.parametrize(
    ("status", "expected", "absent"),
    [
        (S.OPTION, "Confirmer la date", "Réactiver"),
        (S.CONFIRMED, "Générer le contrat", "Confirmer la date"),
        (S.SIGNED, "Prochaine action", "Confirmer la date"),
        (S.CANCELLED, "Réactiver la date", "Confirmer la date"),
    ],
)
def test_detail_suggests_the_next_action_for_each_status(client, status, expected, absent):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=status)

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert expected in content
    assert absent not in content


def test_detail_never_offers_to_sign_the_gig(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=S.CONFIRMED)

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert "Marquer" not in content
    assert reverse("gigs:confirm", args=[gig.pk]) not in content


def test_cancelled_gig_has_no_cancel_link(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=S.CANCELLED)

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert reverse("gigs:cancel", args=[gig.pk]) not in content


def test_gig_list_links_to_the_detail_page(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    content = client.get(reverse("gigs:list")).content.decode()

    assert reverse("gigs:detail", args=[gig.pk]) in content


# --- status buttons ------------------------------------------------------


def test_confirm_button_moves_an_option_to_confirmed(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = client.post(reverse("gigs:confirm", args=[gig.pk]))

    assert response.status_code == 302
    assert response.url == reverse("gigs:detail", args=[gig.pk])
    gig.refresh_from_db()
    assert gig.status == S.CONFIRMED


def test_confirm_on_a_cancelled_gig_shows_an_error_and_changes_nothing(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=S.CANCELLED)

    response = client.post(reverse("gigs:confirm", args=[gig.pk]), follow=True)

    gig.refresh_from_db()
    assert gig.status == S.CANCELLED
    assert "pas possible" in response.content.decode()


def test_status_buttons_do_not_answer_to_get(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    assert client.get(reverse("gigs:confirm", args=[gig.pk])).status_code == 405
    assert client.get(reverse("gigs:reactivate", args=[gig.pk])).status_code == 405
    gig.refresh_from_db()
    assert gig.status == S.OPTION


def test_cancel_asks_for_confirmation_then_cancels_and_keeps_the_gig(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=S.CONFIRMED)

    page = client.get(reverse("gigs:cancel", args=[gig.pk]))
    gig.refresh_from_db()
    assert page.status_code == 200 and gig.status == S.CONFIRMED  # GET changes nothing

    response = client.post(reverse("gigs:cancel", args=[gig.pk]))

    assert response.status_code == 302
    gig.refresh_from_db()
    assert gig.status == S.CANCELLED
    assert Gig.objects.filter(pk=gig.pk).exists()


def test_reactivate_puts_a_cancelled_gig_back_in_option(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=S.CANCELLED)

    client.post(reverse("gigs:reactivate", args=[gig.pk]))

    gig.refresh_from_db()
    assert gig.status == S.OPTION


def test_reactivate_on_a_live_gig_changes_nothing(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=S.CONFIRMED)

    client.post(reverse("gigs:reactivate", args=[gig.pk]))

    gig.refresh_from_db()
    assert gig.status == S.CONFIRMED


# --- isolation and access ------------------------------------------------


@pytest.mark.parametrize("url_name", ["detail", "cancel"])
def test_another_tenants_gig_pages_return_404(client, url_name):
    _login(client)
    other = GigFactory()

    assert client.get(reverse(f"gigs:{url_name}", args=[other.pk])).status_code == 404


@pytest.mark.parametrize("url_name", ["confirm", "cancel", "reactivate"])
def test_cannot_change_the_status_of_another_tenants_gig(client, url_name):
    _login(client)
    other = GigFactory(status=S.CANCELLED if url_name == "reactivate" else S.OPTION)
    before = other.status

    response = client.post(reverse(f"gigs:{url_name}", args=[other.pk]))

    assert response.status_code == 404
    other.refresh_from_db()
    assert other.status == before


@pytest.mark.parametrize("url_name", ["confirm", "cancel", "reactivate"])
def test_status_buttons_require_login(client, url_name):
    gig = GigFactory()

    response = client.post(reverse(f"gigs:{url_name}", args=[gig.pk]))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))
    gig.refresh_from_db()
    assert gig.status == S.OPTION
