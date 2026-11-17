import pytest
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.documents.factories import make_contract_ready
from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory, TenantFactory

from ..models import Contract, ContractSequence, ContractVersion
from ..services import generate_contract_pdf, next_contract_reference

mark_isolation_tested(ContractVersion)
mark_isolation_tested(ContractSequence)

pytestmark = pytest.mark.django_db

YEAR = timezone.localdate().year


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership


def test_first_generation_gives_a_reference_and_version_1():
    contract = generate_contract_pdf(GigFactory())

    assert contract.reference == f"C-{YEAR}-001"
    assert [v.number for v in contract.versions.all()] == [1]


def test_regenerating_adds_a_version_and_keeps_the_reference_and_old_files():
    gig = GigFactory()
    first = generate_contract_pdf(gig)
    first_file_name = first.latest_version.pdf_file.name

    contract = generate_contract_pdf(gig)

    assert contract.reference == first.reference
    assert [v.number for v in contract.versions.all()] == [2, 1]
    assert contract.versions.get(number=1).pdf_file.name == first_file_name


def test_references_follow_one_another_per_tenant():
    tenant = TenantFactory()

    refs = [generate_contract_pdf(GigFactory(tenant=tenant)).reference for _ in range(3)]

    assert refs == [f"C-{YEAR}-001", f"C-{YEAR}-002", f"C-{YEAR}-003"]


def test_each_tenant_has_its_own_numbering():
    generate_contract_pdf(GigFactory())

    other = generate_contract_pdf(GigFactory())

    assert other.reference == f"C-{YEAR}-001"


def test_numbering_restarts_each_year():
    tenant = TenantFactory()
    ContractSequence.objects.create(tenant=tenant, year=YEAR - 1, last_number=41)

    assert next_contract_reference(tenant) == f"C-{YEAR}-001"
    assert ContractSequence.objects.get(tenant=tenant, year=YEAR - 1).last_number == 41


def test_a_rolled_back_generation_leaves_no_gap():
    tenant = TenantFactory()
    gig = GigFactory(tenant=tenant)

    with pytest.raises(RuntimeError), transaction.atomic():
        next_contract_reference(tenant)
        raise RuntimeError

    assert generate_contract_pdf(gig).reference == f"C-{YEAR}-001"


def test_version_records_who_generated_it():
    membership = MembershipFactory()
    gig = GigFactory(tenant=membership.tenant)

    contract = generate_contract_pdf(gig, user=membership.user)

    assert contract.latest_version.created_by == membership.user


def test_signed_contract_gets_no_new_version():
    gig = GigFactory()
    contract = generate_contract_pdf(gig)
    contract.status = Contract.Status.SIGNED
    contract.save()

    generate_contract_pdf(gig)

    assert contract.versions.count() == 1


def test_history_page_lists_the_versions(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)
    contract = generate_contract_pdf(gig)
    generate_contract_pdf(gig)

    response = client.get(reverse("documents:contract-history", args=[gig.pk]))

    content = response.content.decode()
    assert response.status_code == 200
    assert contract.reference in content
    assert "Version 1" in content
    assert "Version 2" in content
    assert "Générer une nouvelle version" in content


def test_history_page_without_contract_offers_to_generate(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)

    response = client.get(reverse("documents:contract-history", args=[gig.pk]))

    assert "Générer le contrat" in response.content.decode()
    assert not Contract.objects.filter(gig=gig).exists()


def test_history_page_of_a_signed_contract_has_no_generate_button(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)
    contract = generate_contract_pdf(gig)
    contract.status = Contract.Status.SIGNED
    contract.save()

    response = client.get(reverse("documents:contract-history", args=[gig.pk]))

    assert "Générer" not in response.content.decode()


def test_generate_view_creates_a_version_and_redirects(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)
    make_contract_ready(gig)

    response = client.post(reverse("documents:contract-generate", args=[gig.pk]))

    assert response.status_code == 302
    assert response.url == reverse("documents:contract-history", args=[gig.pk])
    version = ContractVersion.objects.get(contract__gig=gig)
    assert version.created_by == membership.user


def test_generate_view_refuses_get(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)

    response = client.get(reverse("documents:contract-generate", args=[gig.pk]))

    assert response.status_code == 405
    assert not Contract.objects.filter(gig=gig).exists()


def test_generate_view_on_a_cancelled_gig_creates_nothing(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant, status="cancelled")

    response = client.post(reverse("documents:contract-generate", args=[gig.pk]))

    assert response.status_code == 302
    assert not Contract.objects.filter(gig=gig).exists()


def test_download_serves_the_latest_or_a_given_version(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)
    generate_contract_pdf(gig)
    contract = generate_contract_pdf(gig)

    latest = client.get(reverse("documents:contract-download", args=[gig.pk]))
    first = client.get(reverse("documents:contract-version-download", args=[gig.pk, 1]))

    assert f"{contract.reference}-v2.pdf" in latest["Content-Disposition"]
    assert f"{contract.reference}-v1.pdf" in first["Content-Disposition"]
    assert b"".join(first.streaming_content).startswith(b"%PDF-")


def test_download_without_any_version_redirects_to_the_history(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)

    response = client.get(reverse("documents:contract-download", args=[gig.pk]))

    assert response.status_code == 302
    assert response.url == reverse("documents:contract-history", args=[gig.pk])


def test_unknown_version_returns_404(client):
    membership = _login(client)
    gig = GigFactory(tenant=membership.tenant)
    generate_contract_pdf(gig)

    response = client.get(reverse("documents:contract-version-download", args=[gig.pk, 9]))

    assert response.status_code == 404


def test_other_tenants_contract_pages_return_404(client):
    _login(client)
    other_gig = GigFactory()
    generate_contract_pdf(other_gig)

    for name, args, method in [
        ("contract-history", [other_gig.pk], client.get),
        ("contract-download", [other_gig.pk], client.get),
        ("contract-version-download", [other_gig.pk, 1], client.get),
        ("contract-generate", [other_gig.pk], client.post),
    ]:
        assert method(reverse(f"documents:{name}", args=args)).status_code == 404

    assert other_gig.contract.versions.count() == 1


def test_versions_and_sequences_do_not_mix_between_tenants():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    contract_a = generate_contract_pdf(GigFactory(tenant=tenant_a))
    generate_contract_pdf(GigFactory(tenant=tenant_b))

    assert list(ContractVersion.objects.filter(tenant=tenant_a)) == list(contract_a.versions.all())
    assert ContractSequence.objects.filter(tenant=tenant_a).count() == 1
    assert ContractSequence.objects.get(tenant=tenant_a).tenant == tenant_a


def test_history_requires_login(client):
    gig = GigFactory()

    response = client.get(reverse("documents:contract-history", args=[gig.pk]))

    assert response.status_code == 302
