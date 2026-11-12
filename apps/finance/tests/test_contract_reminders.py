"""Contracts sent and not signed after a week: a reminder on the home page (DAT-07)."""

import datetime
from urllib.parse import parse_qs, unquote, urlparse

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.addressbook.factories import ContactFactory
from apps.documents.factories import ContractFactory
from apps.documents.models import Contract
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory, TenantFactory

from .. import dashboard

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()


def _sent(days_ago, tenant=None, status=Gig.Status.CONFIRMED, gig_days=30, **contract_fields):
    tenant = tenant or TenantFactory()
    gig = GigFactory(tenant=tenant, status=status, date=TODAY + datetime.timedelta(days=gig_days))
    sent_at = timezone.now() - datetime.timedelta(days=days_ago)
    return ContractFactory(tenant=tenant, gig=gig, sent_at=sent_at, **contract_fields)


def test_a_contract_sent_a_week_ago_and_not_signed_is_to_chase():
    contract = _sent(7)

    assert dashboard.contracts_to_chase(contract.tenant, TODAY) == [contract]


def test_a_contract_sent_less_than_a_week_ago_is_left_alone():
    contract = _sent(6)

    assert dashboard.contracts_to_chase(contract.tenant, TODAY) == []


def test_signed_contracts_cancelled_dates_and_past_dates_are_not_chased():
    tenant = TenantFactory()
    signed = _sent(20, tenant=tenant)
    Contract.objects.filter(pk=signed.pk).update(status=Contract.Status.SIGNED)
    _sent(20, tenant=tenant, status=Gig.Status.CANCELLED)
    _sent(20, tenant=tenant, gig_days=-3)
    never_sent = _sent(20, tenant=tenant)
    Contract.objects.filter(pk=never_sent.pk).update(sent_at=None)

    assert dashboard.contracts_to_chase(tenant, TODAY) == []


def test_the_oldest_contract_comes_first_and_an_option_counts():
    tenant = TenantFactory()
    recent = _sent(9, tenant=tenant)
    old = _sent(30, tenant=tenant, status=Gig.Status.OPTION)

    assert dashboard.contracts_to_chase(tenant, TODAY) == [old, recent]


def test_another_structures_contracts_are_never_chased():
    _sent(20)
    mine = TenantFactory()

    assert dashboard.contracts_to_chase(mine, TODAY) == []
    assert not [
        a for a in dashboard.alerts(mine, TODAY)["items"] if "pas encore signé" in a["text"]
    ]


def test_the_alert_says_how_long_and_offers_the_reminder_with_the_organiser_address():
    contract = _sent(9)
    ContactFactory(
        tenant=contract.tenant, promoter=contract.gig.promoter, name="Marie", email="m@x.org"
    )

    alert = next(
        a
        for a in dashboard.alerts(contract.tenant, TODAY)["items"]
        if "pas encore signé" in a["text"]
    )

    assert "envoyé il y a 9 jours" in alert["text"] and alert["level"] == "amber"
    parsed = urlparse(alert["action"]["mailto"])
    query = parse_qs(parsed.query)
    assert parsed.path == "m@x.org"
    assert "Relance contrat de cession" in query["subject"][0]
    body = unquote(query["body"][0])
    assert "Bonjour Marie," in body and "pas encore reçu le contrat signé" in body
    assert (TODAY - datetime.timedelta(days=9)).strftime("%d/%m/%Y") in body
    assert alert["url"] == reverse("documents:contract-history", args=[contract.gig_id])


def test_after_two_weeks_the_reminder_is_urgent():
    contract = _sent(15)

    alerts = dashboard.alerts(contract.tenant, TODAY)

    assert alerts["urgent"] == 1


def test_without_an_organiser_address_the_alert_stays_but_has_no_mail_button():
    contract = _sent(9)

    alert = next(
        a
        for a in dashboard.alerts(contract.tenant, TODAY)["items"]
        if "pas encore signé" in a["text"]
    )

    assert alert["action"]["mailto"] == ""


def test_three_or_more_contracts_become_one_line():
    tenant = TenantFactory()
    for days in (8, 9, 10):
        _sent(days, tenant=tenant)

    texts = [a["text"] for a in dashboard.alerts(tenant, TODAY)["items"]]

    assert [t for t in texts if "contrats envoyés" in t] == [
        "3 contrats envoyés depuis plus de 7 jours, pas signés"
    ]
    assert not [t for t in texts if "pas encore signé" in t]


def test_the_home_page_shows_the_reminder_button(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    contract = _sent(9, tenant=membership.tenant)
    ContactFactory(tenant=membership.tenant, promoter=contract.gig.promoter, email="m@x.org")

    page = client.get(reverse("home")).content.decode()

    assert "pas encore signé" in page and "Relancer" in page and "mailto:m@x.org" in page
