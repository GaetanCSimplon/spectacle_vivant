"""Recette n°1, navigation and wording: NAV-01 to NAV-04, DAT-02, CTR-04."""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.documents import invoicing
from apps.documents.models import Quote
from apps.finance import dashboard
from apps.finance.tests.helpers import TENANT_FIELDS, make_gig
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory, TenantFactory

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()


def _login(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    return membership.tenant


def _html(client, url, **params):
    return client.get(url, params).content.decode()


# --- NAV-01 / NAV-02: icons, permanent access to the structure page ---------------------------


def test_every_signed_in_page_links_to_the_structure_page_twice(client):
    _login(client)

    for url in (reverse("home"), reverse("gigs:list"), reverse("catalog:show-list")):
        content = _html(client, url)
        # the top bar (small screens) and the left column (desktop)
        assert content.count(f'href="{reverse("tenants:settings")}"') >= 2


def test_the_burger_menu_has_an_icon_before_each_entry(client):
    _login(client)

    content = _html(client, reverse("home"))
    menu = content.split("lg:hidden", 1)[1].split("</details>", 1)[0]
    nav = menu.split("<nav", 1)[1]

    assert nav.count("<svg") >= 6  # one icon per entry, plus none of them read aloud
    assert 'aria-hidden="true"' in nav


def test_a_visitor_sees_no_structure_link(client):
    content = _html(client, reverse("account_login"))

    assert reverse("tenants:settings") not in content


# --- NAV-03: breadcrumb on the pages of a date ----------------------------------------------


def _pages(gig):
    quote = invoicing.create_quote(gig)
    invoice = invoicing.create_invoice(gig, "full")
    return [
        reverse("documents:billing", args=[gig.pk]),
        reverse("documents:document-detail", args=[gig.pk, "devis", quote.pk]),
        reverse("documents:document-detail", args=[gig.pk, "factures", invoice.pk]),
        reverse("documents:document-issue", args=[gig.pk, "factures", invoice.pk]),
        reverse("gigs:price", args=[gig.pk]),
        reverse("gigs:terms", args=[gig.pk]),
        reverse("gigs:checklist", args=[gig.pk]),
    ]


def test_the_pages_of_a_date_show_a_breadcrumb_back_to_the_date(client):
    tenant = _login(client)
    gig = make_gig(tenant=tenant, gig_fields={"event_name": "Festival des Arènes"})

    for url in _pages(gig):
        content = _html(client, url)
        assert "Fil d&#x27;Ariane" in content or "Fil d'Ariane" in content, url
        assert f'href="{reverse("gigs:detail", args=[gig.pk])}"' in content, url
        assert "Festival des Arènes" in content, url


def test_the_breadcrumb_does_not_open_the_date_of_another_structure(client):
    _login(client)
    foreign = make_gig(tenant=TenantFactory(**TENANT_FIELDS))

    assert client.get(reverse("documents:billing", args=[foreign.pk])).status_code == 404
    assert client.get(reverse("gigs:price", args=[foreign.pk])).status_code == 404


# --- CTR-04: after issuing a quote, back to the date -----------------------------------------


def test_issuing_a_quote_leads_back_to_the_date_with_its_number(client):
    tenant = _login(client)
    gig = make_gig(tenant=tenant)
    quote = invoicing.create_quote(gig)

    response = client.post(
        reverse("documents:document-issue", args=[gig.pk, "devis", quote.pk]), follow=True
    )

    quote.refresh_from_db()
    assert quote.status == Quote.Status.ISSUED
    assert response.redirect_chain[-1][0] == reverse("gigs:detail", args=[gig.pk])
    assert quote.number in response.content.decode()


def test_issuing_an_invoice_still_shows_the_invoice(client):
    tenant = _login(client)
    gig = make_gig(tenant=tenant)
    invoice = invoicing.create_invoice(gig, "full")

    response = client.post(
        reverse("documents:document-issue", args=[gig.pk, "factures", invoice.pk])
    )

    assert response.url == reverse(
        "documents:document-detail", args=[gig.pk, "factures", invoice.pk]
    )


# --- DAT-02: the title of a date card ---------------------------------------------------------


def test_a_date_is_named_after_its_event_else_its_show(client):
    tenant = _login(client)
    plain = GigFactory(tenant=tenant, event_name="")
    festival = GigFactory(tenant=tenant, event_name="Les Nuits de Fourvière")

    assert plain.display_title == plain.show.title
    assert festival.display_title == "Les Nuits de Fourvière"


def test_the_card_shows_the_event_as_title_and_the_show_under_it(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, event_name="Les Nuits de Fourvière")

    content = _html(client, reverse("gigs:list"))

    assert "Les Nuits de Fourvière" in content
    assert gig.show.title in content


# --- NAV-04: year filter of the home page -----------------------------------------------------


def test_the_home_year_filter_offers_the_coming_years_and_all_years(client):
    tenant = _login(client)
    GigFactory(tenant=tenant, date=datetime.date(TODAY.year - 3, 6, 1))

    choices = dashboard.year_choices(tenant, TODAY)

    assert {TODAY.year, TODAY.year + 1, TODAY.year + 2, TODAY.year - 3} <= set(choices)
    content = _html(client, reverse("home"))
    assert 'value="toutes"' in content
    assert f'value="{TODAY.year + 2}"' in content


def test_the_home_balance_follows_the_chosen_year(client):
    tenant = _login(client)
    next_year = TODAY.year + 1
    make_gig(
        tenant=tenant,
        price="3000.00",
        gig_fields={"status": Gig.Status.CONFIRMED, "date": datetime.date(next_year, 3, 15)},
    )

    assert dashboard.year_overview(tenant, next_year)["planned"] == 3000
    assert dashboard.year_overview(tenant, TODAY.year)["planned"] == 0
    assert dashboard.year_overview(tenant, None)["planned"] == 3000
    this_year = client.get(reverse("home")).context
    asked = client.get(reverse("home"), {"annee": str(next_year)}).context
    everything = client.get(reverse("home"), {"annee": "toutes"}).context
    assert this_year["overview"]["planned"] == 0
    assert asked["overview"]["planned"] == 3000 and asked["year"] == next_year
    assert everything["all_years"] and everything["overview"]["planned"] == 3000


@pytest.mark.parametrize("value", ["1850", "abc", "", "2099", "-1"])
def test_an_unknown_year_falls_back_to_this_year(client, value):
    _login(client)

    context = client.get(reverse("home"), {"annee": value}).context

    assert context["year"] == TODAY.year
    assert not context["all_years"]


def test_the_home_year_never_counts_the_dates_of_another_structure(client):
    tenant = _login(client)
    other = TenantFactory(**TENANT_FIELDS)
    make_gig(
        tenant=other,
        price="9000.00",
        gig_fields={"status": Gig.Status.CONFIRMED, "date": datetime.date(TODAY.year, 12, 1)},
    )

    assert dashboard.year_overview(tenant, None)["planned"] == 0
    assert dashboard.year_choices(tenant, TODAY) == [TODAY.year + n for n in range(3)]
