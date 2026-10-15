"""The price of a date can change until it is locked, and every change is kept."""

from decimal import Decimal

import pytest

from apps.accounts.factories import UserFactory
from apps.documents import invoicing
from apps.documents.models import Invoice
from apps.documents.services import generate_contract_pdf, mark_contract_signed
from apps.finance.tests.helpers import issued_invoice, make_gig
from apps.tenants.factories import MembershipFactory

from .. import services
from ..factories import GigFactory
from ..models import Gig, PriceChange

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def test_change_price_updates_the_gig_and_writes_the_history():
    gig = make_gig(price="1000.00")
    user = UserFactory()

    change = services.change_price(gig, "1200,50", user, note="  négocié par téléphone ")

    gig.refresh_from_db()
    assert gig.price == Decimal("1200.50")
    assert (change.old_price, change.new_price) == (Decimal("1000.00"), Decimal("1200.50"))
    assert change.changed_by == user
    assert change.tenant == gig.tenant
    assert change.note == "négocié par téléphone"
    assert list(gig.price_changes.all()) == [change]


def test_history_is_listed_newest_first():
    gig = make_gig(price="1000.00")

    services.change_price(gig, "1100", None)
    services.change_price(gig, "1050", None)

    assert [c.new_price for c in gig.price_changes.all()] == [
        Decimal("1050.00"),
        Decimal("1100.00"),
    ]


def test_same_price_writes_nothing():
    gig = make_gig(price="1000.00")

    assert services.change_price(gig, "1000.00", None) is None
    assert not PriceChange.objects.exists()


@pytest.mark.parametrize("value", ["", "abc", "0", "-5", "10.999", "1000000", "nan", "inf"])
def test_invalid_price_is_refused(value):
    gig = make_gig(price="1000.00")

    with pytest.raises(services.CannotChangePrice):
        services.change_price(gig, value, None)

    gig.refresh_from_db()
    assert gig.price == Decimal("1000.00")
    assert not PriceChange.objects.exists()


def test_cancelled_gig_price_is_locked():
    gig = make_gig(gig_fields={"status": Gig.Status.CANCELLED})

    with pytest.raises(services.CannotChangePrice, match="annulée"):
        services.change_price(gig, "900", None)


def test_signed_contract_locks_the_price():
    gig = make_gig(gig_fields={"status": Gig.Status.CONFIRMED})
    generate_contract_pdf(gig)
    mark_contract_signed(gig)
    gig.refresh_from_db()

    with pytest.raises(services.CannotChangePrice, match="contrat"):
        services.change_price(gig, "900", None)


def test_issued_invoice_locks_the_price():
    gig = make_gig()
    issued_invoice(gig)

    with pytest.raises(services.CannotChangePrice, match="facture"):
        services.change_price(gig, "900", None)


def test_draft_invoice_does_not_lock_the_price():
    gig = make_gig()
    invoicing.create_invoice(gig, Invoice.Kind.FULL)

    assert services.change_price(gig, "900", None) is not None


def test_price_blockers_is_empty_for_a_free_gig():
    assert services.price_blockers(make_gig()) == []


def test_creating_a_gig_from_the_wizard_writes_the_first_price():
    membership = MembershipFactory()
    tenant = membership.tenant
    seed = GigFactory(tenant=tenant)

    gig = services.create_gig_from_wizard_data(
        tenant,
        {
            "show_id": seed.show.pk,
            "promoter_id": seed.promoter.pk,
            "venue_id": seed.venue.pk,
            "date": seed.date,
            "price": Decimal("750.00"),
        },
        user=membership.user,
    )

    [first] = gig.price_changes.all()
    assert (first.old_price, first.new_price) == (None, Decimal("750.00"))
    assert first.changed_by == membership.user


def test_deleting_the_user_keeps_the_history():
    gig = make_gig()
    user = UserFactory()
    change = services.change_price(gig, "900", user)

    user.delete()

    change.refresh_from_db()
    assert change.changed_by is None
