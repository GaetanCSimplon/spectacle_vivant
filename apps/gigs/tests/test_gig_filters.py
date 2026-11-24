import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.catalog.factories import ShowFactory
from apps.tenants.factories import MembershipFactory, TenantFactory

from .. import services
from ..factories import GigFactory
from ..models import Gig

pytestmark = pytest.mark.django_db

S = Gig.Status
HTMX = {"HTTP_HX_REQUEST": "true"}


def _today():
    return timezone.localdate()


def _days(n):
    return _today() + datetime.timedelta(days=n)


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _list(client, **params):
    return client.get(reverse("gigs:list"), params)


def _ids(response, key):
    return list(response.context[key])


# --- filters -------------------------------------------------------------


def test_filter_by_status(client):
    tenant = _login(client)
    option = GigFactory(tenant=tenant, status=S.OPTION)
    GigFactory(tenant=tenant, status=S.CONFIRMED)

    response = _list(client, status="option")

    assert list(response.context["object_list"]) == [option]


def test_filter_by_month(client):
    tenant = _login(client)
    target = GigFactory(tenant=tenant, date=datetime.date(2031, 10, 15))
    GigFactory(tenant=tenant, date=datetime.date(2031, 11, 1))
    GigFactory(tenant=tenant, date=datetime.date(2032, 10, 15))  # same month, other year

    response = _list(client, month="2031-10")

    assert list(response.context["object_list"]) == [target]


def test_filter_by_month_includes_the_first_and_last_day(client):
    tenant = _login(client)
    first = GigFactory(tenant=tenant, date=datetime.date(2031, 10, 1))
    last = GigFactory(tenant=tenant, date=datetime.date(2031, 10, 31))
    GigFactory(tenant=tenant, date=datetime.date(2031, 9, 30))

    response = _list(client, month="2031-10")

    assert set(response.context["object_list"]) == {first, last}


def test_filter_by_show(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)
    wanted = GigFactory(tenant=tenant, show=show)
    GigFactory(tenant=tenant)

    response = _list(client, show=show.pk)

    assert list(response.context["object_list"]) == [wanted]


def test_filters_combine(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)
    wanted = GigFactory(
        tenant=tenant, show=show, status=S.CONFIRMED, date=datetime.date(2031, 6, 5)
    )
    GigFactory(tenant=tenant, show=show, status=S.OPTION, date=datetime.date(2031, 6, 5))
    GigFactory(tenant=tenant, show=show, status=S.CONFIRMED, date=datetime.date(2031, 7, 5))
    GigFactory(tenant=tenant, status=S.CONFIRMED, date=datetime.date(2031, 6, 5))

    response = _list(client, status="confirmed", month="2031-06", show=show.pk)

    assert list(response.context["object_list"]) == [wanted]


def test_empty_filter_values_mean_no_filter(client):
    tenant = _login(client)
    GigFactory(tenant=tenant)
    GigFactory(tenant=tenant)

    response = _list(client, status="", month="", show="")

    assert len(response.context["object_list"]) == 2


@pytest.mark.parametrize(
    "params",
    [{"status": "nimportequoi"}, {"month": "octobre"}, {"month": "2031-13"}, {"show": "abc"}],
)
def test_invalid_filter_values_are_ignored_not_an_error(client, params):
    tenant = _login(client)
    GigFactory(tenant=tenant)

    response = _list(client, **params)

    assert response.status_code == 200
    assert len(response.context["object_list"]) == 1


def test_one_invalid_filter_does_not_cancel_the_valid_ones(client):
    tenant = _login(client)
    option = GigFactory(tenant=tenant, status=S.OPTION)
    GigFactory(tenant=tenant, status=S.CONFIRMED)

    response = _list(client, status="option", month="pas-un-mois")

    assert list(response.context["object_list"]) == [option]


def test_no_match_says_so_but_is_not_the_empty_state(client):
    tenant = _login(client)
    GigFactory(tenant=tenant, status=S.OPTION)

    content = _list(client, status="signed").content.decode()

    assert "Aucune date ne correspond" in content
    assert "pas encore de date" not in content


def test_no_gig_at_all_shows_the_empty_state_without_filters(client):
    _login(client)

    content = _list(client).content.decode()

    assert "pas encore de date" in content
    assert 'name="status"' not in content


# --- isolation -----------------------------------------------------------


def test_filter_never_returns_another_tenants_gigs(client):
    _login(client)
    other = GigFactory(status=S.OPTION)

    assert list(_list(client, status="option").context["object_list"]) == []
    assert list(_list(client, month=other.date.strftime("%Y-%m")).context["object_list"]) == []


def test_another_tenants_show_id_is_ignored_and_leaks_nothing(client):
    tenant = _login(client)
    mine = GigFactory(tenant=tenant)
    other = GigFactory()

    response = _list(client, show=other.show.pk)

    # Invalid choice for this tenant => ignored, so only *my* gigs are listed.
    assert list(response.context["object_list"]) == [mine]
    assert other.show.title not in response.content.decode()


def test_show_filter_only_offers_the_tenants_own_shows(client):
    tenant = _login(client)
    GigFactory(tenant=tenant, show__title="Mon spectacle")
    ShowFactory(title="Spectacle secret de B")

    content = _list(client).content.decode()

    assert "Mon spectacle" in content
    assert "Spectacle secret de B" not in content


# --- sections ------------------------------------------------------------


def test_cancelled_gigs_have_their_own_section_and_leave_upcoming(client):
    tenant = _login(client)
    live = GigFactory(tenant=tenant, date=_days(10))
    cancelled = GigFactory(tenant=tenant, date=_days(5), status=S.CANCELLED)
    past_cancelled = GigFactory(tenant=tenant, date=_days(-5), status=S.CANCELLED)

    response = _list(client)

    assert _ids(response, "upcoming_gigs") == [live]
    assert _ids(response, "past_gigs") == []
    assert _ids(response, "cancelled_gigs") == [cancelled, past_cancelled]
    assert "Annulées" in response.content.decode()


def test_no_cancelled_section_without_cancelled_gigs(client):
    tenant = _login(client)
    GigFactory(tenant=tenant)

    assert "Annulées" not in _list(client).content.decode()


def test_status_filter_can_show_only_cancelled_gigs(client):
    tenant = _login(client)
    GigFactory(tenant=tenant)
    cancelled = GigFactory(tenant=tenant, status=S.CANCELLED)

    response = _list(client, status="cancelled")

    assert _ids(response, "upcoming_gigs") == []
    assert _ids(response, "cancelled_gigs") == [cancelled]


# --- yearly count --------------------------------------------------------


def test_count_gigs_for_year_excludes_cancelled_other_years_and_other_tenants():
    tenant = TenantFactory()
    GigFactory(tenant=tenant, date=datetime.date(2031, 3, 1))
    GigFactory(tenant=tenant, date=datetime.date(2031, 12, 31), status=S.SIGNED)
    GigFactory(tenant=tenant, date=datetime.date(2031, 5, 1), status=S.CANCELLED)
    GigFactory(tenant=tenant, date=datetime.date(2030, 12, 31))
    GigFactory(tenant=tenant, date=datetime.date(2032, 1, 1))
    GigFactory(date=datetime.date(2031, 6, 1))  # another tenant

    assert services.count_gigs_for_year(tenant, 2031) == 2


def test_count_is_zero_without_gigs():
    assert services.count_gigs_for_year(TenantFactory(), 2031) == 0


def test_list_shows_the_displayed_count_with_the_right_plural(client):
    tenant = _login(client)
    year = _today().year
    GigFactory(tenant=tenant, date=datetime.date(year, 12, 31))

    assert "1 date affichée" in _list(client).content.decode()

    GigFactory(tenant=tenant, date=datetime.date(year, 1, 1))
    assert "2 dates affichées" in _list(client).content.decode()


def test_count_follows_the_active_filters(client):
    tenant = _login(client)
    year = _today().year
    GigFactory(tenant=tenant, date=datetime.date(year, 6, 1), status=S.OPTION)
    GigFactory(tenant=tenant, date=datetime.date(year, 7, 1), status=S.CONFIRMED)

    content = _list(client, status="option").content.decode()

    assert "1 date affichée" in content


# --- HTMX ----------------------------------------------------------------


def test_htmx_request_gets_only_the_results_fragment(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=S.OPTION)

    fragment = client.get(reverse("gigs:list"), {"status": "option"}, **HTMX).content.decode()

    assert "<html" not in fragment
    assert gig.show.title in fragment
    assert 'name="status"' not in fragment  # the form itself is not swapped


def test_normal_request_gets_the_full_page(client):
    _login(client)

    assert "<html" in _list(client).content.decode()


@pytest.mark.parametrize("header", ["HTTP_HX_BOOSTED", "HTTP_HX_HISTORY_RESTORE_REQUEST"])
def test_boosted_navigation_and_history_restore_get_the_full_page(client, header):
    tenant = _login(client)
    GigFactory(tenant=tenant)

    content = client.get(reverse("gigs:list"), **HTMX, **{header: "true"}).content.decode()

    assert "<html" in content


def test_filter_form_is_wired_for_live_filtering_and_url_history(client):
    tenant = _login(client)
    GigFactory(tenant=tenant)

    content = _list(client).content.decode()

    assert 'hx-target="#results"' in content
    assert 'hx-push-url="true"' in content
    assert 'hx-trigger="change"' in content


def test_filter_values_are_kept_in_the_form_after_a_full_page_load(client):
    tenant = _login(client)
    GigFactory(tenant=tenant, status=S.OPTION)

    content = _list(client, status="option", month="2031-10").content.decode()

    assert 'value="2031-10"' in content
    assert '<option value="option" selected>' in content


def test_filters_require_login(client):
    response = client.get(reverse("gigs:list"), {"status": "option"})

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))
