import datetime
import io
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Membership
from apps.addressbook.models import Contact, Promoter, Venue
from apps.catalog.models import Show
from apps.documents import invoicing
from apps.documents import services as doc_services
from apps.documents.models import Contract, ContractVersion, Invoice
from apps.finance import services as finance_services
from apps.finance.factories import ExpenseFactory
from apps.finance.models import Expense, Payment
from apps.finance.tests.helpers import make_gig
from apps.gigs.models import Gig
from apps.roadmaps.factories import RoadmapFactory

from .. import services
from ..factories import MembershipFactory
from ..models import Tenant

pytestmark = pytest.mark.django_db

User = get_user_model()
PASSWORD = "un-mot-de-passe-solide"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _owner(client, **tenant_fields):
    membership = MembershipFactory(role="owner", tenant__name="Compagnie A", **tenant_fields)
    client.force_login(membership.user)
    return membership


def _files(root):
    return sorted(p for p in Path(root).rglob("*") if p.is_file())


def _full_tenant():
    """A tenant with every kind of data and file: signed contract, invoices, credit note..."""
    gig = make_gig(gig_fields={"status": Gig.Status.CONFIRMED})
    tenant = gig.tenant
    doc_services.generate_contract_pdf(gig)
    doc_services.mark_contract_signed(gig)
    paid = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT))
    finance_services.record_payment(paid, "10.00", datetime.date.today(), Payment.Method.CASH)
    note = invoicing.create_credit_note(paid)
    invoicing.issue_invoice(note)
    invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.BALANCE))
    quote = invoicing.create_quote(gig)
    invoicing.issue_quote(quote)
    gig.show.rider_file.save("rider.pdf", ContentFile(b"rider"))
    expense = ExpenseFactory(gig=gig)
    expense.receipt_file.save("ticket.pdf", ContentFile(b"ticket"))
    RoadmapFactory(gig=gig)
    MembershipFactory(tenant=tenant, role="owner")
    return tenant


# --- request, cancel ---------------------------------------------------------------


def test_delete_page_requires_login(client):
    response = client.get(reverse("tenants:delete"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_a_member_cannot_ask_for_the_deletion(client):
    membership = MembershipFactory(role="member")
    client.force_login(membership.user)

    assert client.get(reverse("tenants:delete")).status_code == 403
    response = client.post(
        reverse("tenants:delete"), {"name": membership.tenant.name, "password": PASSWORD}
    )

    assert response.status_code == 403
    membership.tenant.refresh_from_db()
    assert membership.tenant.deletion_requested_at is None


def test_the_owner_asks_for_the_deletion_with_name_and_password(client):
    tenant = _owner(client).tenant

    response = client.post(reverse("tenants:delete"), {"name": "Compagnie A", "password": PASSWORD})

    assert response.status_code == 302
    tenant.refresh_from_db()
    assert tenant.deletion_requested_at is not None
    assert Tenant.objects.filter(pk=tenant.pk).exists()  # nothing is deleted yet


@pytest.mark.parametrize(
    "data, message",
    [
        ({"name": "Autre nom", "password": PASSWORD}, "nom exact"),
        ({"name": "Compagnie A", "password": "faux"}, "Mot de passe incorrect"),
        ({"name": "", "password": ""}, "obligatoire"),
    ],
)
def test_wrong_confirmation_is_refused(client, data, message):
    tenant = _owner(client).tenant

    response = client.post(reverse("tenants:delete"), data)

    assert response.status_code == 200
    assert message in response.content.decode()
    tenant.refresh_from_db()
    assert tenant.deletion_requested_at is None


def test_the_banner_shows_the_purge_day_and_the_deletion_can_be_cancelled(client):
    tenant = _owner(client).tenant
    services.request_deletion(tenant)
    expected = services.deletion_date(tenant).strftime("%d/%m/%Y")

    page = client.get(reverse("tenants:profile")).content.decode()
    assert f"Suppression de votre structure prévue le {expected}" in page

    response = client.post(reverse("tenants:cancel-deletion"))

    assert response.status_code == 302
    tenant.refresh_from_db()
    assert tenant.deletion_requested_at is None
    assert "Suppression de votre structure" not in client.get(reverse("home")).content.decode()


def test_a_member_cannot_cancel_the_deletion(client):
    membership = MembershipFactory(role="member")
    services.request_deletion(membership.tenant)
    client.force_login(membership.user)

    assert client.post(reverse("tenants:cancel-deletion")).status_code == 403


def test_asking_twice_keeps_the_first_date():
    tenant = MembershipFactory().tenant
    services.request_deletion(tenant)
    first = tenant.deletion_requested_at

    services.request_deletion(tenant)

    assert tenant.deletion_requested_at == first


# --- leaving -----------------------------------------------------------------------


def test_a_member_can_leave_and_the_owner_keeps_the_tenant(client):
    owner = MembershipFactory(role="owner")
    member = MembershipFactory(tenant=owner.tenant, role="member")
    client.force_login(member.user)

    assert client.get(reverse("tenants:leave")).status_code == 200
    response = client.post(reverse("tenants:leave"))

    assert response.status_code == 302
    assert not Membership.objects.filter(pk=member.pk).exists()
    assert Membership.objects.filter(pk=owner.pk).exists()
    assert User.objects.filter(pk=member.user.pk).exists()


def test_the_last_owner_cannot_leave(client):
    owner = _owner(client)

    client.post(reverse("tenants:leave"))

    assert Membership.objects.filter(pk=owner.pk).exists()


def test_an_owner_can_leave_when_another_owner_remains():
    first = MembershipFactory(role="owner")
    MembershipFactory(tenant=first.tenant, role="owner")

    services.leave_tenant(first.user, first.tenant)

    assert not Membership.objects.filter(pk=first.pk).exists()


# --- purge -------------------------------------------------------------------------


def test_purge_leaves_no_row_and_no_file(settings):
    tenant = _full_tenant()
    assert _files(settings.MEDIA_ROOT)  # the dataset really created files

    services.purge_tenant(tenant)

    for model in (Gig, Show, Promoter, Venue, Contact, Contract, ContractVersion, Invoice):
        assert not model.objects.exists(), model
    assert not Payment.objects.exists()
    assert not Expense.objects.exists()
    assert not Tenant.objects.exists()
    assert not Membership.objects.exists()
    assert not User.objects.exists()
    assert _files(settings.MEDIA_ROOT) == []


def test_purge_does_not_touch_another_tenant(settings):
    doomed = _full_tenant()
    other = make_gig(gig_fields={"status": Gig.Status.CONFIRMED})
    doc_services.generate_contract_pdf(other)
    issued = invoicing.issue_invoice(invoicing.create_invoice(other, Invoice.Kind.FULL))
    expense = ExpenseFactory(gig=other)
    expense.receipt_file.save("ticket.pdf", ContentFile(b"keep"))
    other_user = MembershipFactory(tenant=other.tenant).user
    # A user in both tenants keeps their account and the other tenant.
    shared = MembershipFactory(tenant=doomed)
    Membership.objects.create(user=shared.user, tenant=other.tenant)
    kept_files = {p.name for p in _files(settings.MEDIA_ROOT) if "keep" in p.read_text("latin1")}

    services.purge_tenant(doomed)

    assert Tenant.objects.filter(pk=other.tenant.pk).exists()
    assert Gig.objects.filter(pk=other.pk).exists()
    assert Invoice.objects.filter(pk=issued.pk).exists()
    assert Contract.objects.filter(tenant=other.tenant).exists()
    assert User.objects.filter(pk=other_user.pk).exists()
    assert User.objects.filter(pk=shared.user.pk).exists()
    assert Tenant.objects.count() == 1
    remaining = _files(settings.MEDIA_ROOT)
    assert {p.name for p in remaining if "keep" in p.read_text("latin1")} == kept_files
    assert len(remaining) == 3  # contract version, invoice PDF, receipt


def test_purge_keeps_staff_accounts():
    membership = MembershipFactory()
    membership.user.is_staff = True
    membership.user.save()

    services.purge_tenant(membership.tenant)

    assert User.objects.filter(pk=membership.user.pk).exists()


def test_purge_is_atomic_and_keeps_the_files(settings, monkeypatch):
    tenant = _full_tenant()
    pk = tenant.pk
    before = _files(settings.MEDIA_ROOT)

    def boom(*args, **kwargs):
        raise RuntimeError("database failure")

    monkeypatch.setattr(User.objects.__class__, "filter", boom, raising=False)
    with pytest.raises(RuntimeError):
        services.purge_tenant(tenant)

    assert Tenant.objects.filter(pk=pk).exists()
    assert Gig.objects.exists()
    assert _files(settings.MEDIA_ROOT) == before


# --- grace period and command -------------------------------------------------------


def test_only_tenants_past_the_grace_period_are_purged():
    recent = MembershipFactory().tenant
    old = MembershipFactory().tenant
    untouched = MembershipFactory().tenant
    Tenant.objects.filter(pk=recent.pk).update(
        deletion_requested_at=timezone.now() - datetime.timedelta(days=29)
    )
    Tenant.objects.filter(pk=old.pk).update(
        deletion_requested_at=timezone.now() - datetime.timedelta(days=31)
    )

    assert services.purge_due_tenants() == 1

    assert Tenant.objects.filter(pk=recent.pk).exists()
    assert Tenant.objects.filter(pk=untouched.pk).exists()
    assert not Tenant.objects.filter(pk=old.pk).exists()


def test_the_command_purges_and_prints_only_a_count():
    old = MembershipFactory(tenant__name="Nom Secret").tenant
    Tenant.objects.filter(pk=old.pk).update(
        deletion_requested_at=timezone.now() - datetime.timedelta(days=40)
    )
    out = io.StringIO()

    call_command("purge_deleted_tenants", stdout=out)
    call_command("purge_deleted_tenants", stdout=out)  # idempotent

    assert "1 tenant(s) purged." in out.getvalue()
    assert "0 tenant(s) purged." in out.getvalue()
    assert "Secret" not in out.getvalue()
    assert not Tenant.objects.filter(pk=old.pk).exists()


# --- isolation -----------------------------------------------------------------------


def test_asking_for_deletion_only_affects_the_current_tenant(client):
    other = MembershipFactory(tenant__name="Compagnie B").tenant
    mine = _owner(client).tenant

    client.post(reverse("tenants:delete"), {"name": "Compagnie A", "password": PASSWORD})

    mine.refresh_from_db()
    other.refresh_from_db()
    assert mine.deletion_requested_at is not None
    assert other.deletion_requested_at is None
