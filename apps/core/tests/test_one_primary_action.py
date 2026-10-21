"""One main (coral) action per screen, and red for what destroys (charter, docs/cadrage/13)."""

import re

import pytest
from django.urls import reverse

from apps.documents import invoicing
from apps.documents.models import Invoice
from apps.finance.tests.helpers import TENANT_FIELDS, make_gig
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db

PRIMARY = re.compile(r'class="[^"]*\bbtn-primary\b')


def _primary_count(html):
    return len(PRIMARY.findall(html))


@pytest.fixture
def membership(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    return membership


EMPTY_PAGES = [
    "home",
    "gigs:list",
    "gigs:calendar",
    "catalog:show-list",
    "addressbook:promoter-list",
    "addressbook:venue-list",
    "addressbook:contact-list",
    "tenants:person-list",
    "tenants:profile",
    "tenants:settings",
    "tenants:data-export",
    "export",
]


@pytest.mark.parametrize("name", EMPTY_PAGES)
def test_a_new_structure_sees_one_main_action_per_screen(client, membership, name):
    html = client.get(reverse(name)).content.decode()

    assert _primary_count(html) <= 1, f"{name}: {_primary_count(html)} coral buttons"


@pytest.mark.parametrize("status", [Gig.Status.OPTION, Gig.Status.CONFIRMED, Gig.Status.SIGNED])
def test_every_gig_page_has_at_most_one_main_action(client, membership, status):
    gig = make_gig(tenant=membership.tenant, gig_fields={"status": status})
    invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT)

    for name, args in (
        ("gigs:detail", [gig.pk]),
        ("gigs:price", [gig.pk]),
        ("gigs:terms", [gig.pk]),
        ("gigs:list", []),
        ("finance:page", [gig.pk]),
        ("documents:billing", [gig.pk]),
        ("documents:contract-history", [gig.pk]),
        ("documents:contract-complete", [gig.pk]),
        ("roadmaps:editor", [gig.pk]),
    ):
        html = client.get(reverse(name, args=args)).content.decode()
        assert _primary_count(html) <= 1, f"{name} ({status}): {_primary_count(html)}"


def test_the_billing_page_puts_the_deposit_first_and_the_balance_second(client, membership):
    gig = make_gig(tenant=membership.tenant)

    html = client.get(reverse("documents:billing", args=[gig.pk])).content.decode()

    deposit = html.split("Facture d'acompte")[0].rsplit("<button", 1)[1]
    balance = html.split("Facture de solde")[0].rsplit("<button", 1)[1]
    assert "btn-primary" in deposit and "btn-secondary" in balance


@pytest.mark.parametrize(
    ("name", "label"),
    [
        ("addressbook:promoter-delete", "Supprimer"),
        ("addressbook:venue-delete", "Supprimer"),
        ("catalog:show-delete", "Supprimer"),
        ("tenants:person-delete", "Supprimer"),
    ],
)
def test_the_confirmation_of_a_deletion_is_red_not_coral(client, membership, name, label):
    from apps.addressbook.factories import PromoterFactory, VenueFactory
    from apps.catalog.factories import ShowFactory
    from apps.tenants.factories import PersonFactory

    tenant = membership.tenant
    obj = {
        "addressbook:promoter-delete": lambda: PromoterFactory(tenant=tenant),
        "addressbook:venue-delete": lambda: VenueFactory(tenant=tenant),
        "catalog:show-delete": lambda: ShowFactory(tenant=tenant),
        "tenants:person-delete": lambda: PersonFactory(tenant=tenant),
    }[name]()

    html = client.get(reverse(name, args=[obj.pk])).content.decode()

    assert "btn-danger" in html and "btn-primary" not in html


def test_cancelling_and_deleting_a_gig_are_red(client, membership):
    gig = make_gig(tenant=membership.tenant)

    cancel = client.get(reverse("gigs:cancel", args=[gig.pk])).content.decode()
    delete = client.get(reverse("gigs:delete", args=[gig.pk])).content.decode()

    assert "btn-danger" in cancel and "btn-primary" not in cancel
    assert "btn-danger" in delete and "btn-primary" not in delete


def test_leaving_and_deleting_the_structure_are_red(client, membership):
    member = MembershipFactory(role="member", tenant=membership.tenant)
    client.force_login(member.user)
    leave = client.get(reverse("tenants:leave")).content.decode()
    client.force_login(membership.user)
    delete = client.get(reverse("tenants:delete")).content.decode()

    for html in (leave, delete):
        assert "btn-danger" in html and "bg-red-700" not in html


def test_the_onboarding_button_is_the_main_action(client, django_user_model):
    client.force_login(django_user_model.objects.create_user(email="neuf@example.org"))

    html = client.get(reverse("tenants-onboarding")).content.decode()

    assert _primary_count(html) == 1 and "bg-blue-600" not in html


def test_the_danger_button_text_is_readable():
    from pathlib import Path

    from apps.core.tests.test_brand_contrast import SCALES, contrast

    css = (Path(__file__).resolve().parents[3] / "css/source.css").read_text()
    assert ".btn-danger" in css and "bg-red-700 text-white" in css
    assert contrast("#ffffff", SCALES["red-700"]) >= 4.5
    assert contrast("#ffffff", SCALES["red-800"]) >= 4.5
