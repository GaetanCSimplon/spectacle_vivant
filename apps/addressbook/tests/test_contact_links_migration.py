"""The migrations that turn the single organiser/venue of a contact into many-to-many links.

Every contact must keep exactly the organiser or venue it had; nothing is lost, in either
direction.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)

BEFORE = [("addressbook", "0012_venue_map_point")]
LINKED = [("addressbook", "0015_remove_contact_single_links")]


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.fixture
def old_world():
    apps = _migrate(BEFORE)
    yield apps
    # Whatever happened, leave the schema at the latest migration for the other tests.
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def _data(apps):
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(name="Compagnie")
    Promoter = apps.get_model("addressbook", "Promoter")
    Venue = apps.get_model("addressbook", "Venue")
    Contact = apps.get_model("addressbook", "Contact")
    promoter = Promoter.objects.create(tenant_id=tenant.pk, name="Festival")
    venue = Venue.objects.create(tenant_id=tenant.pk, name="Salle")
    for name, parent in (
        ("De l'organisateur", {"promoter": promoter}),
        ("Du lieu", {"venue": venue}),
    ):
        Contact.objects.create(tenant_id=tenant.pk, name=name, **parent)
    return promoter.pk, venue.pk


def test_every_contact_keeps_its_organiser_or_its_venue(old_world):
    promoter_pk, venue_pk = _data(old_world)

    new = _migrate(LINKED)
    Contact = new.get_model("addressbook", "Contact")

    of_promoter = Contact.objects.get(name="De l'organisateur")
    of_venue = Contact.objects.get(name="Du lieu")
    assert [p.pk for p in of_promoter.promoters.all()] == [promoter_pk]
    assert not of_promoter.venues.exists()
    assert [v.pk for v in of_venue.venues.all()] == [venue_pk]
    assert not of_venue.promoters.exists()
    assert not hasattr(Contact, "promoter") and not hasattr(Contact, "venue")


def test_the_reverse_gives_each_contact_its_first_link_back(old_world):
    promoter_pk, venue_pk = _data(old_world)
    linked = _migrate(LINKED)
    # The historical models of that migration: the live Promoter has columns added since.
    Promoter = linked.get_model("addressbook", "Promoter")
    LiveContact = linked.get_model("addressbook", "Contact")

    two = LiveContact.objects.get(name="De l'organisateur")
    two.promoters.add(Promoter.objects.create(tenant_id=two.tenant_id, name="Second organisateur"))

    old = _migrate(BEFORE)
    Contact = old.get_model("addressbook", "Contact")

    assert Contact.objects.get(name="De l'organisateur").promoter_id == promoter_pk
    assert Contact.objects.get(name="Du lieu").venue_id == venue_pk
    assert Contact.objects.count() == 2


def test_the_reverse_stops_with_a_clear_message_if_a_contact_works_for_nobody(old_world):
    _data(old_world)
    _migrate(LINKED)
    from apps.addressbook.models import Contact as LiveContact

    LiveContact.objects.create(tenant=LiveContact.objects.first().tenant, name="Libre")

    with pytest.raises(RuntimeError, match="sans rattachement"):
        _migrate(BEFORE)
    # nothing was lost: the contact is still there
    assert LiveContact.objects.filter(name="Libre").exists()
