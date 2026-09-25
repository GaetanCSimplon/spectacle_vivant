from decimal import Decimal

import pytest

from ..factories import GigFactory

pytestmark = pytest.mark.django_db


def test_new_gig_fields_have_sensible_defaults():
    gig = GigFactory()
    gig.refresh_from_db()

    assert gig.is_free is False
    assert gig.ticket_price == Decimal("0.00")
    assert gig.invitations_count == 0
    assert gig.signing_place == ""


def test_free_gig_forces_ticket_price_to_zero():
    gig = GigFactory(is_free=True, ticket_price=Decimal("15.00"))
    gig.refresh_from_db()

    assert gig.ticket_price == Decimal("0.00")


def test_paid_gig_keeps_its_ticket_price():
    gig = GigFactory(is_free=False, ticket_price=Decimal("15.00"))
    gig.refresh_from_db()

    assert gig.ticket_price == Decimal("15.00")


def test_switching_a_gig_to_free_resets_the_ticket_price():
    gig = GigFactory(ticket_price=Decimal("15.00"))

    gig.is_free = True
    gig.save()
    gig.refresh_from_db()

    assert gig.ticket_price == Decimal("0.00")


def test_switching_back_to_paid_does_not_restore_the_old_price():
    gig = GigFactory(is_free=True, ticket_price=Decimal("15.00"))

    gig.is_free = False
    gig.save()
    gig.refresh_from_db()

    assert gig.ticket_price == Decimal("0.00")


def test_free_gig_resets_ticket_price_even_with_update_fields():
    gig = GigFactory(ticket_price=Decimal("15.00"))

    gig.is_free = True
    gig.save(update_fields=["is_free"])
    gig.refresh_from_db()

    assert gig.ticket_price == Decimal("0.00")
