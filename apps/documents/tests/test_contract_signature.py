import importlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import Resolver404, clear_url_caches, resolve, reverse

from apps.gigs import services as gig_services
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

from ..models import Contract
from ..services import (
    ContractSigningError,
    attach_signed_pdf,
    generate_contract_pdf,
    mark_contract_signed,
)

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4 fake signed contract"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _pdf(name="scan.pdf", content=PDF):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def _confirmed_gig_with_contract(tenant=None):
    gig = GigFactory(status=Gig.Status.CONFIRMED, **({"tenant": tenant} if tenant else {}))
    generate_contract_pdf(gig)
    return gig


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


# --- service ---------------------------------------------------------------


def test_marking_signed_freezes_the_latest_version_and_signs_the_gig():
    gig = _confirmed_gig_with_contract()
    latest = generate_contract_pdf(gig).latest_version

    contract = mark_contract_signed(gig)

    gig.refresh_from_db()
    assert contract.status == Contract.Status.SIGNED
    assert contract.signed_version == latest
    assert contract.signed_at is not None
    assert gig.status == Gig.Status.SIGNED


def test_marking_signed_can_store_the_signed_pdf():
    gig = _confirmed_gig_with_contract()

    contract = mark_contract_signed(gig, _pdf())

    assert contract.signed_pdf.read() == PDF


def test_signed_pdf_is_stored_in_an_unguessable_folder_without_the_uploaded_name():
    gig = _confirmed_gig_with_contract()

    contract = mark_contract_signed(gig, _pdf("mon-nom-perso.pdf"))

    folder, name = contract.signed_pdf.name.rsplit("/", 1)
    assert name == "contrat-signe.pdf"
    assert len(folder.split("/")[-1]) == 32


def test_generated_versions_are_stored_in_unguessable_folders():
    contract = generate_contract_pdf(GigFactory())

    parts = contract.latest_version.pdf_file.name.split("/")
    assert parts[0] == "contracts"
    assert len(parts[1]) == 32


def test_signed_contract_cannot_be_signed_again_nor_regenerated():
    gig = _confirmed_gig_with_contract()
    contract = mark_contract_signed(gig)

    with pytest.raises(ContractSigningError):
        mark_contract_signed(gig)
    generate_contract_pdf(gig)

    assert contract.versions.count() == 1
    contract.refresh_from_db()
    assert contract.signed_version == contract.latest_version


@pytest.mark.parametrize("status", [Gig.Status.OPTION, Gig.Status.CANCELLED])
def test_only_a_confirmed_gig_can_be_signed(status):
    gig = _confirmed_gig_with_contract()
    Gig.objects.filter(pk=gig.pk).update(status=status)
    gig.refresh_from_db()

    with pytest.raises(ContractSigningError):
        mark_contract_signed(gig)

    contract = Contract.objects.get(gig=gig)
    assert contract.status == Contract.Status.DRAFT
    assert contract.signed_version is None


def test_cannot_sign_without_a_generated_contract():
    gig = GigFactory(status=Gig.Status.CONFIRMED)

    with pytest.raises(ContractSigningError):
        mark_contract_signed(gig)

    gig.refresh_from_db()
    assert gig.status == Gig.Status.CONFIRMED


def test_the_signed_version_cannot_be_deleted():
    from django.db.models import ProtectedError

    gig = _confirmed_gig_with_contract()
    contract = mark_contract_signed(gig)

    with pytest.raises(ProtectedError):
        contract.signed_version.delete()


def test_signed_pdf_can_be_added_once_afterwards():
    gig = _confirmed_gig_with_contract()
    mark_contract_signed(gig)

    contract = attach_signed_pdf(gig, _pdf())

    assert contract.signed_pdf.read() == PDF
    with pytest.raises(ContractSigningError):
        attach_signed_pdf(gig, _pdf())


def test_signed_pdf_cannot_be_added_to_an_unsigned_contract():
    gig = _confirmed_gig_with_contract()

    with pytest.raises(ContractSigningError):
        attach_signed_pdf(gig, _pdf())


# --- reactivation (A1) -----------------------------------------------------


def test_reactivating_a_gig_with_a_signed_contract_puts_it_back_to_signed():
    gig = _confirmed_gig_with_contract()
    mark_contract_signed(gig)
    gig_services.change_status(gig, Gig.Status.CANCELLED)

    gig_services.reactivate_gig(gig)

    gig.refresh_from_db()
    assert gig.status == Gig.Status.SIGNED


def test_reactivating_a_gig_with_an_unsigned_contract_still_goes_to_option():
    gig = _confirmed_gig_with_contract()
    gig_services.change_status(gig, Gig.Status.CANCELLED)

    gig_services.reactivate_gig(gig)

    gig.refresh_from_db()
    assert gig.status == Gig.Status.OPTION


# --- views -----------------------------------------------------------------


def test_sign_page_asks_for_confirmation_and_shows_the_version(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)

    response = client.get(reverse("documents:contract-sign", args=[gig.pk]))

    content = response.content.decode()
    assert response.status_code == 200
    assert "version 1" in content
    assert "signé en dehors de l'application" in content


def test_sign_page_without_a_contract_redirects_to_the_history(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=Gig.Status.CONFIRMED)

    response = client.get(reverse("documents:contract-sign", args=[gig.pk]))

    assert response.status_code == 302


def test_signing_through_the_view(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)

    response = client.post(
        reverse("documents:contract-sign", args=[gig.pk]), {"signed_pdf": _pdf()}
    )

    assert response.status_code == 302
    gig.refresh_from_db()
    contract = Contract.objects.get(gig=gig)
    assert gig.status == Gig.Status.SIGNED
    assert contract.status == Contract.Status.SIGNED
    assert contract.signed_pdf


def test_signing_without_a_pdf_works(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)

    client.post(reverse("documents:contract-sign", args=[gig.pk]))

    assert Contract.objects.get(gig=gig).status == Contract.Status.SIGNED


def test_signing_rejects_a_file_that_is_not_a_pdf(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)
    fake = _pdf("faux.pdf", b"<html>not a pdf</html>")

    response = client.post(reverse("documents:contract-sign", args=[gig.pk]), {"signed_pdf": fake})

    assert response.status_code == 200
    assert "doit être un PDF" in response.content.decode()
    assert Contract.objects.get(gig=gig).status == Contract.Status.DRAFT


def test_signing_rejects_a_file_over_10_mb(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)
    big = _pdf(content=b"%PDF-" + b"0" * (10 * 1024 * 1024))

    response = client.post(reverse("documents:contract-sign", args=[gig.pk]), {"signed_pdf": big})

    assert response.status_code == 200
    assert "trop lourd" in response.content.decode()
    assert Contract.objects.get(gig=gig).status == Contract.Status.DRAFT


def test_history_of_a_signed_contract_shows_the_signature_and_blocks_generation(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)
    mark_contract_signed(gig, _pdf())

    content = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()

    assert "Signé le" in content
    assert "Télécharger le PDF signé" in content
    assert "Générer" not in content
    assert "Marquer comme signé" not in content
    assert client.post(reverse("documents:contract-generate", args=[gig.pk])).status_code == 302
    assert Contract.objects.get(gig=gig).versions.count() == 1


def test_history_offers_to_sign_only_a_confirmed_gig_with_a_version(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)

    content = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()

    assert "Marquer comme signé" in content


def test_complete_form_is_blocked_once_signed(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)
    mark_contract_signed(gig)

    response = client.get(reverse("documents:contract-complete", args=[gig.pk]))

    assert response.status_code == 302


def test_signed_pdf_download_is_an_attachment(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)
    mark_contract_signed(gig, _pdf())

    response = client.get(reverse("documents:contract-signed-pdf", args=[gig.pk]))

    assert "attachment" in response["Content-Disposition"]
    assert b"".join(response.streaming_content) == PDF


def test_signed_pdf_download_without_a_scan_is_404(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)
    mark_contract_signed(gig)

    assert client.get(reverse("documents:contract-signed-pdf", args=[gig.pk])).status_code == 404


def test_signed_pdf_can_be_uploaded_later_through_the_view(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)
    mark_contract_signed(gig)

    client.post(reverse("documents:contract-signed-pdf", args=[gig.pk]), {"signed_pdf": _pdf()})

    assert Contract.objects.get(gig=gig).signed_pdf


def test_later_upload_cannot_replace_the_existing_scan(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)
    mark_contract_signed(gig, _pdf())
    first_name = Contract.objects.get(gig=gig).signed_pdf.name

    client.post(
        reverse("documents:contract-signed-pdf", args=[gig.pk]),
        {"signed_pdf": _pdf(content=PDF + b" other")},
    )

    assert Contract.objects.get(gig=gig).signed_pdf.name == first_name


def test_preview_of_a_cancelled_signed_contract_shows_the_frozen_version(client):
    tenant = _login(client)
    gig = _confirmed_gig_with_contract(tenant)
    mark_contract_signed(gig)
    gig_services.change_status(gig, Gig.Status.CANCELLED)

    response = client.get(reverse("documents:contract-download", args=[gig.pk]))

    assert response.status_code == 200


# --- access control --------------------------------------------------------


@pytest.mark.parametrize("name", ["contract-sign", "contract-signed-pdf"])
def test_signature_pages_require_login(client, name):
    gig = _confirmed_gig_with_contract()

    response = client.get(reverse(f"documents:{name}", args=[gig.pk]))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_other_tenants_cannot_sign_or_read_a_contract(client):
    _login(client)
    other_gig = _confirmed_gig_with_contract()
    mark_contract_signed(other_gig, _pdf())

    assert client.get(reverse("documents:contract-sign", args=[other_gig.pk])).status_code == 404
    assert client.post(reverse("documents:contract-sign", args=[other_gig.pk])).status_code == 404
    assert (
        client.get(reverse("documents:contract-signed-pdf", args=[other_gig.pk])).status_code == 404
    )
    assert (
        client.post(
            reverse("documents:contract-signed-pdf", args=[other_gig.pk]), {"signed_pdf": _pdf()}
        ).status_code
        == 404
    )


def test_other_tenants_cannot_sign_a_contract_of_another_tenant(client):
    _login(client)
    other_gig = _confirmed_gig_with_contract()

    client.post(reverse("documents:contract-sign", args=[other_gig.pk]))

    assert Contract.objects.get(gig=other_gig).status == Contract.Status.DRAFT


def test_media_files_are_not_served_by_url(settings):
    import config.urls

    settings.DEBUG = True
    try:
        importlib.reload(config.urls)
        clear_url_caches()
        with pytest.raises(Resolver404):
            resolve("/media/contracts/abc/contrat.pdf")
    finally:
        settings.DEBUG = False
        importlib.reload(config.urls)
        clear_url_caches()
