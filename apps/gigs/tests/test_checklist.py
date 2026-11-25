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


def test_ticking_a_box_is_kept_and_leaves_the_others_alone():
    gig = GigFactory()
    user = UserFactory()

    checklist.set_item(gig, "rider_sent", True, user)
    checklist.set_item(gig, "dpae_sent", True, user)

    assert _done(gig) == {"rider_sent", "dpae_sent"}
    row = GigChecklist.objects.get(gig=gig)
    assert row.tenant == gig.tenant and row.updated_by == user


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
    checklist.set_item(gig, "rider_sent", True, first)
    before = GigChecklist.objects.get(gig=gig)

    checklist.set_item(gig, "rider_sent", True, second)

    after = GigChecklist.objects.get(gig=gig)
    assert after.updated_by == first
    assert after.updated_at == before.updated_at


def test_the_last_author_is_kept():
    gig = GigFactory()
    first, second = UserFactory(), UserFactory()

    checklist.set_item(gig, "rider_sent", True, first)
    checklist.set_item(gig, "tech_sheet_sent", True, second)

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
        checklist.set_item(gig, "rider_sent", value, None)

    assert not GigChecklist.objects.exists()


def test_a_checklist_belongs_to_one_gig_only():
    gig = GigFactory()
    other = GigFactory(tenant=gig.tenant)
    checklist.set_item(gig, "rider_sent", True, None)

    assert _done(other) == set()
    with pytest.raises(IntegrityError), transaction.atomic():
        GigChecklist.objects.create(gig=gig, tenant=gig.tenant)


def test_deleting_the_gig_deletes_its_checklist():
    gig = GigFactory()
    checklist.set_item(gig, "rider_sent", True, None)

    Gig.objects.filter(pk=gig.pk).delete()

    assert not GigChecklist.objects.exists()


def test_deleting_the_user_keeps_the_checklist():
    gig = GigFactory()
    user = UserFactory()
    checklist.set_item(gig, "rider_sent", True, user)

    user.delete()

    row = GigChecklist.objects.get(gig=gig)
    assert row.updated_by is None and row.items == {"rider_sent": True}


def test_nothing_else_happens_when_a_box_is_ticked():
    """No status change, no price change, no document: the checklist is only a memo."""
    gig = GigFactory(status=Gig.Status.OPTION)

    for key in checklist.ITEM_KEYS - checklist.AUTOMATIC_KEYS:
        checklist.set_item(gig, key, True, None)

    gig.refresh_from_db()
    assert gig.status == Gig.Status.OPTION
    assert not gig.price_changes.exists()


def test_two_tenants_never_share_a_checklist():
    gig_a = GigFactory(tenant=TenantFactory())
    gig_b = GigFactory(tenant=TenantFactory())
    checklist.set_item(gig_a, "rider_sent", True, None)

    assert _done(gig_b) == set()
    assert list(GigChecklist.objects.filter(tenant=gig_b.tenant)) == []
    # A gig seen under the wrong tenant finds no checklist and writes into none of the others.
    gig_b.tenant = gig_a.tenant
    assert _done(gig_b) == set()


# --- automatic boxes (the app knows) ---


def _invoice(gig, kind, status):
    from apps.documents.models import Invoice

    return Invoice.objects.create(gig=gig, tenant=gig.tenant, kind=kind, status=status)


def test_an_empty_gig_has_no_automatic_box_done():
    assert _done(GigFactory()) == set()


def test_a_signed_invoiced_and_paid_gig_ticks_its_boxes():
    from django.utils import timezone

    from apps.documents.models import Contract, Invoice, Quote
    from apps.roadmaps.models import Roadmap

    gig = GigFactory()
    scope = {"gig": gig, "tenant": gig.tenant}
    Contract.objects.create(
        **scope, status=Contract.Status.SIGNED, sent_at=timezone.now(), signed_at=timezone.now()
    )
    Quote.objects.create(**scope, status=Quote.Status.ISSUED, accepted_on=timezone.localdate())
    Roadmap.objects.create(**scope, is_published=True)
    _invoice(gig, Invoice.Kind.DEPOSIT, Invoice.Status.PAID)
    _invoice(gig, Invoice.Kind.BALANCE, Invoice.Status.PAID)

    assert _done(gig) == checklist.AUTOMATIC_KEYS


def test_a_draft_quote_or_unsent_contract_ticks_nothing():
    from apps.documents.models import Contract, Quote

    gig = GigFactory()
    Quote.objects.create(gig=gig, tenant=gig.tenant)
    Contract.objects.create(gig=gig, tenant=gig.tenant)

    assert _done(gig) == set()


def test_an_issued_unpaid_invoice_is_sent_not_received():
    from apps.documents.models import Invoice

    gig = GigFactory()
    _invoice(gig, Invoice.Kind.FULL, Invoice.Status.ISSUED)

    assert _done(gig) == {"balance_invoice_sent"}


def test_a_cancelled_invoice_and_a_draft_tick_nothing():
    from apps.documents.models import Invoice

    gig = GigFactory()
    _invoice(gig, Invoice.Kind.DEPOSIT, Invoice.Status.CANCELLED)
    _invoice(gig, Invoice.Kind.BALANCE, Invoice.Status.DRAFT)

    assert _done(gig) == set()


def test_an_automatic_box_cannot_be_ticked_by_hand():
    with pytest.raises(checklist.InvalidChecklistItem):
        checklist.set_item(GigFactory(), "contract_signed", True, None)


def test_an_old_manual_tick_on_an_automatic_box_is_ignored():
    gig = GigFactory()
    GigChecklist.objects.create(gig=gig, tenant=gig.tenant, items={"contract_signed": True})

    assert _done(gig) == set()


def test_a_manual_box_stays_ticked_next_to_automatic_ones():
    from apps.documents.models import Invoice

    gig = GigFactory()
    _invoice(gig, Invoice.Kind.DEPOSIT, Invoice.Status.ISSUED)
    checklist.set_item(gig, "dpae_sent", True, None)

    assert _done(gig) == {"deposit_invoice_sent", "dpae_sent"}


def test_documents_of_another_tenant_tick_nothing():
    from apps.documents.models import Invoice

    gig, other = GigFactory(), TenantFactory()
    Invoice.objects.create(
        gig=gig, tenant=other, kind=Invoice.Kind.DEPOSIT, status=Invoice.Status.PAID
    )

    assert _done(gig) == set()
