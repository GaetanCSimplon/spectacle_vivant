"""The home page cards: active shows, upcoming dates by period, balance, alerts, shortcuts."""

import datetime
from pathlib import Path

import pytest
from django.urls import reverse

from apps.catalog.factories import ShowFactory
from apps.documents import services as doc_services
from apps.finance import dashboard, services
from apps.finance.factories import ExpenseFactory
from apps.finance.models import Payment
from apps.finance.tests.helpers import TENANT_FIELDS, issued_invoice, make_gig
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory, TenantFactory

pytestmark = pytest.mark.django_db

TODAY = datetime.date(2026, 10, 14)  # a Wednesday
HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def tenant(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    return membership.tenant


def _gig(tenant, days, **fields):
    return GigFactory(
        tenant=tenant, date=datetime.date.today() + datetime.timedelta(days=days), **fields
    )


# --- active shows ----------


def test_a_show_is_active_with_at_least_one_live_upcoming_gig():
    tenant = TenantFactory()
    busy = ShowFactory(tenant=tenant)
    for days in (3, 30):
        GigFactory(tenant=tenant, show=busy, date=TODAY + datetime.timedelta(days=days))
    only_past = ShowFactory(tenant=tenant)
    GigFactory(tenant=tenant, show=only_past, date=TODAY - datetime.timedelta(days=3))
    only_cancelled = ShowFactory(tenant=tenant)
    GigFactory(
        tenant=tenant,
        show=only_cancelled,
        status=Gig.Status.CANCELLED,
        date=TODAY + datetime.timedelta(days=3),
    )
    ShowFactory(tenant=tenant)  # no gig at all
    GigFactory(date=TODAY + datetime.timedelta(days=3))  # another tenant's show

    assert dashboard.active_shows_count(tenant, TODAY) == 1


# --- periods ----------


@pytest.mark.parametrize(
    ("today", "period", "expected"),
    [
        (datetime.date(2026, 10, 14), "semaine", datetime.date(2026, 10, 18)),
        (datetime.date(2026, 10, 18), "semaine", datetime.date(2026, 10, 18)),  # a Sunday
        (datetime.date(2026, 10, 14), "mois", datetime.date(2026, 10, 31)),
        (datetime.date(2028, 2, 10), "mois", datetime.date(2028, 2, 29)),
        (datetime.date(2026, 12, 31), "mois", datetime.date(2026, 12, 31)),
        (datetime.date(2026, 10, 14), "annee", datetime.date(2026, 12, 31)),
        (datetime.date(2026, 10, 14), "n'importe quoi", datetime.date(2026, 10, 31)),
    ],
)
def test_the_end_of_each_period(today, period, expected):
    assert dashboard.period_end(today, period) == expected


def test_next_gigs_stop_at_the_end_of_the_period():
    tenant = TenantFactory()
    inside = GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=2))
    GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=20))

    week = dashboard.next_gigs(tenant, TODAY, dashboard.period_end(TODAY, "semaine"))
    year = dashboard.next_gigs(tenant, TODAY, dashboard.period_end(TODAY, "annee"))

    assert week == [inside]
    assert len(year) == 2


def test_the_page_filters_the_upcoming_dates_by_period(client, tenant, monkeypatch):
    monkeypatch.setattr("apps.core.views.timezone.localdate", lambda: TODAY)
    GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=1), show__title="Demain")
    GigFactory(tenant=tenant, date=TODAY + datetime.timedelta(days=60), show__title="Decembre")

    week = client.get(reverse("home"), {"periode": "semaine"}).content.decode()
    month = client.get(reverse("home"), {"periode": "mois"}).content.decode()
    year = client.get(reverse("home"), {"periode": "annee"}).content.decode()

    assert "Demain" in week and "Decembre" not in week
    assert "Demain" in month and "Decembre" not in month
    assert "Demain" in year and "Decembre" in year


def test_an_unknown_period_falls_back_to_the_current_month(client, tenant):
    _gig(tenant, 0)
    response = client.get(reverse("home"), {"periode": "siecle"})
    assert response.context["period"] == "mois"


def test_changing_the_period_with_htmx_swaps_only_the_card(client, tenant):
    _gig(tenant, 0)

    response = client.get(reverse("home"), {"periode": "annee"}, **HTMX)
    content = response.content.decode()

    assert response.status_code == 200
    assert "<html" not in content and 'id="upcoming-card"' in content
    assert 'aria-current="true">Année' in content


def test_an_empty_period_says_so_and_the_link_goes_to_the_list(client, tenant):
    _gig(tenant, 400)  # a gig exists, but not this month
    content = client.get(reverse("home")).content.decode()
    assert (
        "Aucune date d'ici la fin du mois" in content
        or "Aucune date d&#x27;ici la fin du mois" in content
    )
    assert reverse("gigs:list") in content


# --- balance ----------


def _balance_page(client):
    return client.get(reverse("home")).content.decode()


def test_the_balance_is_a_surplus_a_deficit_or_balanced(client, tenant):
    gig = make_gig(tenant=tenant, price="1000.00", gig_fields={"date": datetime.date.today()})
    assert "Équilibre" in _balance_page(client)

    ExpenseFactory(gig=gig, amount="200.00")
    page = _balance_page(client)
    assert "Déficit" in page and "- 200" not in page

    services.record_payment(
        issued_invoice(gig), "1000.00", datetime.date.today(), Payment.Method.CASH
    )
    page = _balance_page(client)
    assert "Excédent" in page and "+ 800 €" in page.replace("\\xa0", " ")


# --- alerts ----------


def _alerts(tenant, today=None):
    return dashboard.alerts(tenant, today or datetime.date.today())


def test_no_alert_says_nothing_to_report(client, tenant):
    _gig(tenant, 100)  # a quiet future gig, option without expiry
    assert _alerts(tenant)["items"] == []
    assert "Rien à signaler" in _balance_page(client)


def test_options_about_to_expire_or_expired_are_alerts():
    today = datetime.date.today()
    tenant = TenantFactory()
    GigFactory(
        tenant=tenant,
        status=Gig.Status.OPTION,
        date=today + datetime.timedelta(days=60),
        option_expires_on=today + datetime.timedelta(days=5),
    )
    GigFactory(
        tenant=tenant,
        status=Gig.Status.OPTION,
        date=today + datetime.timedelta(days=61),
        option_expires_on=today - datetime.timedelta(days=2),
    )
    GigFactory(
        tenant=tenant,
        status=Gig.Status.OPTION,
        date=today + datetime.timedelta(days=62),
        option_expires_on=today + datetime.timedelta(days=30),
    )  # far: no alert

    items = _alerts(tenant)["items"]

    assert [a["level"] for a in items] == ["red", "amber"]  # expired first, then 5 days left
    assert "expirée depuis 2 jour(s)" in items[0]["text"]
    assert "expire dans 5 jour(s)" in items[1]["text"]


def test_an_overdue_invoice_is_a_red_alert_and_the_others_follow():
    today = datetime.date.today()
    gig = make_gig(
        gig_fields={"status": Gig.Status.CONFIRMED, "date": today + datetime.timedelta(days=40)}
    )
    invoice = issued_invoice(gig)
    from apps.documents.models import Invoice

    Invoice.objects.filter(pk=invoice.pk).update(due_date=today - datetime.timedelta(days=4))

    items = _alerts(gig.tenant)["items"]

    assert items[0]["level"] == "red"
    assert f"Facture {invoice.number} en retard de 4 jour(s)" == items[0]["text"]
    assert items[0]["url"] == reverse("finance:page", args=[gig.pk])
    assert any("contrat à générer" in a["text"] for a in items[1:])


def test_a_contract_still_unsigned_close_to_the_date_is_an_alert():
    today = datetime.date.today()
    close = make_gig(
        gig_fields={"status": Gig.Status.CONFIRMED, "date": today + datetime.timedelta(days=10)}
    )
    doc_services.generate_contract_pdf(close)
    later = make_gig(
        tenant=close.tenant,
        gig_fields={"status": Gig.Status.CONFIRMED, "date": today + datetime.timedelta(days=40)},
    )
    doc_services.generate_contract_pdf(later)

    texts = [a["text"] for a in _alerts(close.tenant)["items"]]

    assert any("contrat à faire signer (dans 10 jour(s))" in t for t in texts)
    assert not any("dans 40" in t for t in texts)


def test_expenses_without_a_receipt_are_an_alert_per_date():
    gig = make_gig(gig_fields={"date": datetime.date.today() + datetime.timedelta(days=5)})
    ExpenseFactory(gig=gig)
    ExpenseFactory(gig=gig)

    texts = [a["text"] for a in _alerts(gig.tenant)["items"]]

    assert any("2 dépense(s) sans justificatif" in t for t in texts)


def test_alerts_are_capped_and_the_rest_is_counted():
    today = datetime.date.today()
    tenant = TenantFactory()
    for n in range(11):
        GigFactory(
            tenant=tenant,
            status=Gig.Status.OPTION,
            date=today + datetime.timedelta(days=50 + n),
            option_expires_on=today + datetime.timedelta(days=1),
        )

    result = _alerts(tenant)

    assert len(result["items"]) == dashboard.ALERT_LIMIT
    assert result["hidden"] == 3


def test_alerts_never_include_another_tenants_data(client, tenant):
    today = datetime.date.today()
    _gig(tenant, 100)  # a quiet gig of this tenant, so the dashboard is shown
    GigFactory(
        status=Gig.Status.OPTION,
        date=today + datetime.timedelta(days=9),
        option_expires_on=today + datetime.timedelta(days=1),
    )
    other = make_gig(
        gig_fields={"status": Gig.Status.CONFIRMED, "date": today + datetime.timedelta(days=9)}
    )
    ExpenseFactory(gig=other)

    assert _alerts(tenant)["items"] == []
    assert "Rien à signaler" in _balance_page(client)


# --- shortcuts ----------


def test_the_home_page_has_the_three_shortcuts(client, tenant):
    content = client.get(reverse("home")).content.decode()
    for url in (
        reverse("gigs:wizard-show"),
        reverse("catalog:show-create"),
        reverse("addressbook:contact-create"),
    ):
        assert f'href="{url}"' in content


# --- identity ----------


def test_the_self_hosted_fonts_are_shipped_and_referenced():
    root = Path(__file__).resolve().parents[3]
    css = (root / "css/source.css").read_text()
    for name in (
        "archivo-latin.woff2",
        "instrument-sans-latin.woff2",
        "ibm-plex-mono-400-latin.woff2",
        "ibm-plex-mono-500-latin.woff2",
    ):
        assert (root / "static/fonts" / name).stat().st_size > 10_000
        assert name in css
    assert "sora-latin.woff2" not in css
    assert "fonts.googleapis.com" not in (root / "templates/base.html").read_text()
    assert "fonts.googleapis.com" not in css
