"""The data migration that carries the old single-value qualification over to the new lists."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)

BEFORE = [("addressbook", "0009_promoter_qualification_lists")]
AFTER = [("addressbook", "0010_convert_qualification")]


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


def _promoter(apps, tenant, name, **fields):
    return apps.get_model("addressbook", "Promoter").objects.create(
        tenant_id=tenant.pk, name=name, **fields
    )


def test_old_values_are_carried_over_and_nothing_is_lost(old_world):
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(name="Compagnie")
    mapped = _promoter(
        old_world, tenant, "Mapped", kind="municipality", event_type="festival", aesthetic="JAZZ"
    )
    accents = _promoter(
        old_world,
        tenant,
        "Accents",
        kind="venue",
        event_type="Évènement  Privé",
        aesthetic="Musique classique",
    )
    bar = _promoter(old_world, tenant, "Bar", kind="bar", event_type="Fête locale")
    other = _promoter(old_world, tenant, "Other", kind="other")
    lost = _promoter(
        old_world,
        tenant,
        "Lost",
        event_type="Marché de Noël",
        aesthetic="Électro",
        notes="Déjà là",
    )
    empty = _promoter(old_world, tenant, "Empty")

    new_world = _migrate(AFTER)

    Promoter = new_world.get_model("addressbook", "Promoter")
    get = lambda p: Promoter.objects.get(pk=p.pk)  # noqa: E731
    assert (get(mapped).kinds, get(mapped).event_types, get(mapped).aesthetics) == (
        ["municipality"],
        ["festival"],
        ["jazz"],
    )
    assert (get(accents).kinds, get(accents).event_types, get(accents).aesthetics) == (
        ["venue"],
        ["private_event"],
        ["classical"],
    )
    assert (get(bar).kinds, get(bar).event_types) == (["venue"], ["municipal_event"])
    assert get(other).kinds == ["other"]
    # What matches nothing is kept in the notes, after what was already there.
    assert get(lost).event_types == [] and get(lost).aesthetics == []
    assert get(lost).notes == "Déjà là\nType d'évènement : Marché de Noël\nEsthétique : Électro"
    assert (get(empty).kinds, get(empty).notes) == ([], "")


def test_a_promoter_without_old_values_is_left_untouched(old_world):
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(name="Compagnie")
    plain = _promoter(old_world, tenant, "Plain", notes="Rien à changer")

    new_world = _migrate(AFTER)

    promoter = new_world.get_model("addressbook", "Promoter").objects.get(pk=plain.pk)
    assert promoter.notes == "Rien à changer" and promoter.kinds == []
