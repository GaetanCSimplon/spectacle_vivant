"""A cancelled gig must not look like money still expected (issued invoices stay, by law)."""

import pytest
from django.urls import reverse

from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

from .helpers import TENANT_FIELDS, issued_invoice, make_gig

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _setup(client, cancelled=True):
    membership = MembershipFactory(
        tenant__name=TENANT_FIELDS["name"],
        tenant__address=TENANT_FIELDS["address"],
        tenant__siret=TENANT_FIELDS["siret"],
        tenant__vat_regime=TENANT_FIELDS["vat_regime"],
        tenant__iban=TENANT_FIELDS["iban"],
    )
    client.force_login(membership.user)
    gig = make_gig(tenant=membership.tenant)
    invoice = issued_invoice(gig)
    if cancelled:
        gig.status = Gig.Status.CANCELLED
        gig.save()
    return gig, invoice


def test_cancel_page_warns_about_issued_invoices(client):
    gig, invoice = _setup(client, cancelled=False)
    content = client.get(reverse("gigs:cancel", args=[gig.pk])).content.decode()
    assert invoice.number in content
    assert "avoir" in content


def test_cancel_page_has_no_warning_without_invoice(client):
    gig, _ = _setup(client, cancelled=False)
    other = make_gig(tenant=gig.tenant)
    content = client.get(reverse("gigs:cancel", args=[other.pk])).content.decode()
    assert "factures émises restent" not in content


def test_cancelled_gig_shows_its_price_as_struck_out(client):
    gig, _ = _setup(client)
    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()
    assert "date annulée" in content


def test_cancelled_gig_warns_on_billing_and_finance_pages(client):
    gig, _ = _setup(client)
    assert (
        "Cette date est annulée"
        in client.get(reverse("documents:billing", args=[gig.pk])).content.decode()
    )
    assert (
        "Cette date est annulée"
        in client.get(reverse("finance:page", args=[gig.pk])).content.decode()
    )


def test_home_flags_unpaid_invoices_of_a_cancelled_gig(client):
    _setup(client)
    content = client.get(reverse("home")).content.decode()
    assert "Date annulée" in content


def test_home_does_not_flag_a_live_gig(client):
    _setup(client, cancelled=False)
    assert "Date annulée" not in client.get(reverse("home")).content.decode()
