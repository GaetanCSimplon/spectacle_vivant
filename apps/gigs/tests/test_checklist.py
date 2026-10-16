"""The contracting checklist: boxes done or not done, nothing more (F-83)."""

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.factories import UserFactory
from apps.tenants.factories import TenantFactory

from .. import checklist
from ..factories import GigFactory
from ..models import Gig, GigChecklist

pytestmark = pytest.mark.django_db


def _done(gig):
    return {
        item["key"]
        for section in checklist.checklist_sections(gig)
        for item in section["items"]
        if item["done"]
    }


def test_the_sections_follow_the_spec():
    titles = [str(title) for title, _items in checklist.SECTIONS]

    assert titles == [
        "Avant confirmation de la date",
        "Contrat",
        "Documents techniques",
        "Facturation",
        "Intervenants / intermittents",
        "Clôture",
    ]
    assert [len(items) for _title, items in checklist.SECTIONS] == [2, 2, 3, 4, 3, 2]
    assert len(checklist.ITEM_KEYS) == 16


def test_the_labels_are_the_ones_of_the_spec():
    labels = [str(label) for _title, items in checklist.SECTIONS for _key, label in items]

    assert labels == [
        "Devis envoyé",
        "Devis accepté / accord du lieu",
        "Contrat envoyé",
        "Contrat signé / retourné",
        "Fiche technique envoyée",
        "Rider envoyé",
        "Feuille de route envoyée",
        "Acompte envoyé",
        "Acompte reçu",
        "Facture de solde envoyée",
        "Solde reçu",
        "Contrats intermittents envoyés / signés",
        "DPAE envoyée",
        "Accusé DPAE reçu",
        "Tous les documents archivés",
        "Date clôturée",
    ]


def test_a_new_gig_has_every_box_unticked_and_no_row():
    gig = GigFactory()

    sections = checklist.checklist_sections(gig)

    assert _done(gig) == set()
    assert sum(len(section["items"]) for section in sections) == 16
    assert not GigChecklist.objects.exists()
    assert checklist.last_update(gig) is None


def test_ticking_a_box_is_kept_and_leaves_the_others_alone():
    gig = GigFactory()
    user = UserFactory()

    checklist.set_item(gig, "quote_sent", True, user)
    checklist.set_item(gig, "deposit_received", True, user)

    assert _done(gig) == {"quote_sent", "deposit_received"}
    row = GigChecklist.objects.get(gig=gig)
    assert row.tenant == gig.tenant and row.updated_by == user
    assert checklist.last_update(gig) is not None


def test_unticking_a_box():
    gig = GigFactory()
    checklist.set_item(gig, "rider_sent", True, None)
    checklist.set_item(gig, "closed", True, None)

    checklist.set_item(gig, "rider_sent", False, None)

    assert _done(gig) == {"closed"}


def test_ticking_a_box_does_not_depend_on_the_order_or_on_the_other_boxes():
    gig = GigFactory()

    checklist.set_item(gig, "closed", True, None)  # the last box first, nothing before it

    assert _done(gig) == {"closed"}


def test_an_unchanged_box_does_not_touch_the_audit_trail():
    gig = GigFactory()
    first, second = UserFactory(), UserFactory()
    checklist.set_item(gig, "quote_sent", True, first)
    before = GigChecklist.objects.get(gig=gig)

    checklist.set_item(gig, "quote_sent", True, second)

    after = GigChecklist.objects.get(gig=gig)
    assert after.updated_by == first
    assert after.updated_at == before.updated_at


def test_the_last_author_is_kept():
    gig = GigFactory()
    first, second = UserFactory(), UserFactory()

    checklist.set_item(gig, "quote_sent", True, first)
    checklist.set_item(gig, "quote_accepted", True, second)

    assert GigChecklist.objects.get(gig=gig).updated_by == second


@pytest.mark.parametrize("key", ["nope", "", "QUOTE_SENT", "devis_envoye"])
def test_an_unknown_box_is_refused(key):
    gig = GigFactory()

    with pytest.raises(checklist.InvalidChecklistItem):
        checklist.set_item(gig, key, True, None)

    assert not GigChecklist.objects.exists()


@pytest.mark.parametrize("value", [1, 0, "true", "", None, "false"])
def test_a_value_that_is_not_a_plain_boolean_is_refused(value):
    gig = GigFactory()

    with pytest.raises(checklist.InvalidChecklistItem):
        checklist.set_item(gig, "quote_sent", value, None)

    assert not GigChecklist.objects.exists()


def test_reset_unticks_everything_and_records_who():
    gig = GigFactory()
    user = UserFactory()
    for key in checklist.ITEM_KEYS:
        checklist.set_item(gig, key, True, None)
    assert len(_done(gig)) == 16

    checklist.reset(gig, user)

    assert _done(gig) == set()
    assert GigChecklist.objects.get(gig=gig).updated_by == user


def test_reset_on_a_gig_without_checklist_creates_nothing():
    gig = GigFactory()

    assert checklist.reset(gig, UserFactory()) is None
    assert not GigChecklist.objects.exists()


def test_a_checklist_belongs_to_one_gig_only():
    gig = GigFactory()
    other = GigFactory(tenant=gig.tenant)
    checklist.set_item(gig, "quote_sent", True, None)

    assert _done(other) == set()
    with pytest.raises(IntegrityError), transaction.atomic():
        GigChecklist.objects.create(gig=gig, tenant=gig.tenant)


def test_deleting_the_gig_deletes_its_checklist():
    gig = GigFactory()
    checklist.set_item(gig, "quote_sent", True, None)

    Gig.objects.filter(pk=gig.pk).delete()

    assert not GigChecklist.objects.exists()


def test_deleting_the_user_keeps_the_checklist():
    gig = GigFactory()
    user = UserFactory()
    checklist.set_item(gig, "quote_sent", True, user)

    user.delete()

    row = GigChecklist.objects.get(gig=gig)
    assert row.updated_by is None and row.items == {"quote_sent": True}


def test_nothing_else_happens_when_a_box_is_ticked():
    """No status change, no price change, no document: the checklist is only a memo."""
    gig = GigFactory(status=Gig.Status.OPTION)

    for key in checklist.ITEM_KEYS:
        checklist.set_item(gig, key, True, None)

    gig.refresh_from_db()
    assert gig.status == Gig.Status.OPTION
    assert not gig.price_changes.exists()


def test_two_tenants_never_share_a_checklist():
    gig_a = GigFactory(tenant=TenantFactory())
    gig_b = GigFactory(tenant=TenantFactory())
    checklist.set_item(gig_a, "quote_sent", True, None)

    assert _done(gig_b) == set()
    assert list(GigChecklist.objects.filter(tenant=gig_b.tenant)) == []
    # A gig seen under the wrong tenant finds no checklist and writes into none of the others.
    gig_b.tenant = gig_a.tenant
    assert _done(gig_b) == set()
