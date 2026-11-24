"""The figures at the head of "Mes dates" (DAT-06): the money of the dates shown."""

import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.finance import bord, services
from apps.finance.tests.helpers import TENANT_FIELDS, issued_invoice, make_gig
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory, TenantFactory

pytestmark = pytest.mark.django_db
D = Decimal
TODAY = datetime.date.today()


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _gig(tenant, price, status=Gig.Status.CONFIRMED, days=10):
    return make_gig(
        tenant=tenant,
        price=price,
        gig_fields={"status": status, "date": TODAY + datetime.timedelta(days=days)},
    )


def _login(client):
    membership = MembershipFactory(tenant=TenantFactory(**TENANT_FIELDS))
    client.force_login(membership.user)
    return membership.tenant


def test_the_figures_sum_the_dates_shown(client):
    tenant = _login(client)
    confirmed = _gig(tenant, "1000.00")
    _gig(tenant, "2000.00", status=Gig.Status.SIGNED)
    _gig(tenant, "500.00", status=Gig.Status.OPTION)
    _gig(tenant, "900.00", status=Gig.Status.CANCELLED)
    invoice = issued_invoice(confirmed)
    services.record_payment(invoice, "250.00", TODAY, "transfer")

    figures = client.get(reverse("gigs:list")).context["figures"]

    assert figures["planned"] == D("3000.00")  # options and cancelled dates are not counted
    assert figures["signed"] == D("2000.00")
    assert figures["invoiced"] == D("1000.00")
    assert figures["received"] == D("250.00")


def test_the_figures_follow_the_filters_of_the_list(client):
    tenant = _login(client)
    kept = _gig(tenant, "1000.00")
    _gig(tenant, "700.00")

    figures = client.get(reverse("gigs:list"), {"show": kept.show.pk}).context["figures"]

    assert figures["planned"] == D("1000.00")


def test_the_figures_are_the_same_as_the_bord_for_the_same_dates(client):
    tenant = _login(client)
    gig = _gig(tenant, "1500.00")
    services.record_payment(issued_invoice(gig), "300.00", TODAY, "transfer")
    filters = bord.Filters(
        start=TODAY - datetime.timedelta(days=30), end=TODAY + datetime.timedelta(days=30)
    )

    figures = client.get(reverse("gigs:list")).context["figures"]
    revenue = bord.revenue(tenant, filters)

    for key in ("planned", "signed", "invoiced", "received"):
        assert figures[key] == revenue[key]


def test_the_page_shows_the_strip_and_the_link_to_the_bord(client):
    tenant = _login(client)
    _gig(tenant, "1500.00")

    page = client.get(reverse("gigs:list")).content.decode()

    assert "Ce que rapportent ces dates" in page and "1\xa0500 €" in page
    assert reverse("tenants:profile") in page


def test_no_strip_when_no_date_is_shown(client):
    _login(client)

    assert "Ce que rapportent ces dates" not in client.get(reverse("gigs:list")).content.decode()


def test_another_structures_dates_never_count(client):
    tenant = _login(client)
    _gig(tenant, "100.00")
    other = MembershipFactory().tenant
    _gig(other, "99999.00")

    assert client.get(reverse("gigs:list")).context["figures"]["planned"] == D("100.00")


def test_remaining_figures_use_the_same_formula_as_the_balance_of_a_date():
    from apps.finance.factories import ExpenseFactory

    tenant = TenantFactory()
    gig = _gig(tenant, "1000.00")
    ExpenseFactory(gig=gig, amount="120.50")

    figures = bord.figures_for_gigs(tenant, Gig.objects.filter(pk=gig.pk))
    balance = services.gig_balance(gig)

    assert figures["remaining_planned"] == balance.remaining_planned == D("879.50")
    assert figures["remaining_real"] == balance.result == D("-120.50")


def test_remaining_figures_of_another_tenant_are_not_counted():
    from apps.finance.factories import ExpenseFactory

    tenant, other = TenantFactory(), TenantFactory()
    ExpenseFactory(gig=_gig(other, "500.00"), amount="80.00")
    mine = _gig(tenant, "1000.00")

    figures = bord.figures_for_gigs(tenant, Gig.objects.filter(pk=mine.pk))

    assert figures["remaining_planned"] == D("1000.00")


@pytest.mark.parametrize("url", ["home", "tenants:profile", "gigs:list"])
def test_the_two_remaining_labels_sit_side_by_side_on_each_summary(client, url):
    tenant = _login(client)
    _gig(tenant, "1000.00")

    page = client.get(reverse(url)).content.decode()

    assert "Reste prévu" in page
    assert "Reste réel" in page
    assert "Solde de l'année" not in page
    assert "Ce qu'il reste après ces frais" not in page
