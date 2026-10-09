"""Deleting a gig: only when it carries no legal or financial trace."""

import pytest
from django.urls import reverse

from apps.documents import invoicing
from apps.documents.models import Contract, ContractVersion, Invoice
from apps.documents.services import generate_contract_pdf, mark_contract_signed
from apps.finance.factories import ExpenseFactory
from apps.finance.tests.helpers import TENANT_FIELDS, issued_invoice, make_gig
from apps.roadmaps.models import Roadmap
from apps.tenants.factories import MembershipFactory

from .. import services
from ..factories import GigFactory
from ..models import Gig

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _login(client):
    membership = MembershipFactory(
        tenant__name=TENANT_FIELDS["name"],
        tenant__address=TENANT_FIELDS["address"],
        tenant__siret=TENANT_FIELDS["siret"],
        tenant__vat_regime=TENANT_FIELDS["vat_regime"],
        tenant__iban=TENANT_FIELDS["iban"],
    )
    client.force_login(membership.user)
    return membership.tenant


def _url(gig):
    return reverse("gigs:delete", args=[gig.pk])


def test_a_blank_gig_is_deleted_with_its_drafts_contract_and_roadmap(client):
    tenant = _login(client)
    gig = make_gig(tenant=tenant)
    invoicing.create_invoice(gig, Invoice.Kind.FULL)
    generate_contract_pdf(gig)
    Roadmap.objects.create(gig=gig, tenant=tenant)
    stored = [v.pdf_file.path for v in ContractVersion.objects.filter(contract__gig=gig)]
    assert stored

    response = client.post(_url(gig))

    assert response.status_code == 302
    assert response.url == reverse("gigs:list")
    assert not Gig.objects.filter(pk=gig.pk).exists()
    assert not Invoice.objects.filter(tenant=tenant).exists()
    assert not Contract.objects.filter(tenant=tenant).exists()
    assert not Roadmap.objects.filter(tenant=tenant).exists()
    import os

    assert not any(os.path.exists(p) for p in stored)


def test_confirmation_page_of_a_blank_gig_offers_deletion(client):
    gig = make_gig(tenant=_login(client))
    content = client.get(_url(gig)).content.decode()
    assert "Supprimer définitivement" in content


def test_an_issued_invoice_blocks_deletion(client):
    gig = make_gig(tenant=_login(client))
    issued_invoice(gig)

    assert "Supprimer définitivement" not in client.get(_url(gig)).content.decode()
    response = client.post(_url(gig))

    assert response.url == reverse("gigs:detail", args=[gig.pk])
    assert Gig.objects.filter(pk=gig.pk).exists()
    assert Invoice.objects.filter(gig=gig).exists()


def test_a_signed_contract_blocks_deletion(client):
    gig = make_gig(tenant=_login(client), gig_fields={"status": Gig.Status.CONFIRMED})
    generate_contract_pdf(gig)
    mark_contract_signed(gig)

    client.post(_url(gig))

    assert Gig.objects.filter(pk=gig.pk).exists()
    assert Contract.objects.filter(gig=gig).exists()


def test_an_expense_blocks_deletion(client):
    gig = make_gig(tenant=_login(client))
    ExpenseFactory(gig=gig)

    client.post(_url(gig))

    assert Gig.objects.filter(pk=gig.pk).exists()


def test_service_reports_the_reasons():
    gig = make_gig()
    assert services.deletion_blockers(gig) == []
    ExpenseFactory(gig=gig)
    assert len(services.deletion_blockers(gig)) == 1
    with pytest.raises(services.CannotDelete):
        services.delete_blank_gig(gig)


def test_deletion_needs_login(client):
    gig = GigFactory()
    response = client.post(_url(gig))
    assert response.url.startswith(reverse("account_login"))
    assert Gig.objects.filter(pk=gig.pk).exists()


def test_another_tenant_gets_404_and_nothing_is_deleted(client):
    _login(client)
    other = GigFactory()

    assert client.get(_url(other)).status_code == 404
    assert client.post(_url(other)).status_code == 404
    assert Gig.objects.filter(pk=other.pk).exists()


def test_deletion_is_post_only_for_the_action(client):
    gig = make_gig(tenant=_login(client))
    client.get(_url(gig))
    assert Gig.objects.filter(pk=gig.pk).exists()
