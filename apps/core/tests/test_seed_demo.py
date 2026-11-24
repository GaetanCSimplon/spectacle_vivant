"""The demo data command: fictional, in its own structure, refused outside development."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import Membership, User
from apps.addressbook.models import Contact, Promoter, Venue
from apps.catalog.models import Show
from apps.documents.models import Contract, Invoice
from apps.finance.models import Expense, ExpenseClaim, Payment
from apps.gigs.models import Gig
from apps.roadmaps.models import PlaceContact, Roadmap
from apps.tenants.factories import TenantFactory
from apps.tenants.models import Person, Tenant

pytestmark = [pytest.mark.django_db, pytest.mark.slow]

DEMO = "Compagnie des Nuits d'Été"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _seed(*extra):
    call_command("seed_demo", "--force", "--no-map", *extra)


@pytest.fixture(scope="module")
def _unused():
    return None


def test_it_is_refused_when_debug_is_off(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError, match="development only"):
        call_command("seed_demo", "--no-map")

    assert not Tenant.objects.filter(name=DEMO).exists()


def test_it_creates_a_full_demo_in_its_own_structure():
    mine = TenantFactory(name="Ma structure")

    _seed()

    demo = Tenant.objects.get(name=DEMO)
    assert Gig.objects.filter(tenant=demo).count() == 15
    assert {s for s in Gig.objects.filter(tenant=demo).values_list("status", flat=True)} == {
        "signed",
        "confirmed",
        "option",
        "cancelled",
    }
    assert Show.objects.filter(tenant=demo).count() == 3
    assert Person.objects.filter(tenant=demo).count() == 6
    assert Promoter.objects.filter(tenant=demo).count() == 6
    assert Venue.objects.filter(tenant=demo).count() == 6
    assert Contact.objects.filter(tenant=demo).count() == 16
    assert Contact.objects.filter(tenant=demo, promoters=None, venues=None).count() == 2
    assert Contact.objects.filter(tenant=demo, promoters__isnull=False).distinct().count() >= 7
    assert Venue.objects.filter(tenant=demo, promoters__isnull=False).distinct().count() == 3
    assert Contract.objects.filter(tenant=demo, status="signed").count() == 7
    assert Invoice.objects.filter(tenant=demo).count() == 12
    assert (
        Payment.objects.filter(tenant=demo).exists()
        and Expense.objects.filter(tenant=demo).exists()
    )
    assert Expense.objects.filter(
        tenant=demo, person__isnull=False, reimbursed_on__isnull=True
    ).exists()
    assert ExpenseClaim.objects.filter(tenant=demo, status="pending").count() == 2
    assert Roadmap.objects.filter(tenant=demo, is_published=True).count() == 1
    assert PlaceContact.objects.filter(tenant=demo).count() == 6
    assert Membership.objects.filter(tenant=demo).count() == 2
    # nothing of the user's own data was touched
    assert (
        Tenant.objects.filter(pk=mine.pk).exists() and Gig.objects.filter(tenant=mine).count() == 0
    )


def test_the_owner_can_log_in_and_sees_the_demo(client):
    _seed()

    assert client.login(email="demo@example.org", password="demo-bordpro-2026")
    page = client.get("/bord/").content.decode()

    assert "Compagnie des Nuits d&#x27;Été" in page or DEMO in page


def test_a_second_run_is_refused_and_reset_recreates_it():
    _seed()

    with pytest.raises(CommandError, match="already exists"):
        _seed()
    _seed("--reset")

    assert Tenant.objects.filter(name=DEMO).count() == 1
    assert Gig.objects.filter(tenant__name=DEMO).count() == 15


def test_remove_deletes_the_demo_and_its_users():
    other = TenantFactory(name="Autre")
    _seed()

    _seed("--remove")

    assert not Tenant.objects.filter(name=DEMO).exists()
    assert not User.objects.filter(email__in=["demo@example.org", "gestion@example.org"]).exists()
    assert Tenant.objects.filter(pk=other.pk).exists()
