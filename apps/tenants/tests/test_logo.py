"""The logo of a structure on its quotes, invoices and contracts (STR-07, CTR-01)."""

import base64

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.documents import invoicing, services
from apps.finance.tests.helpers import TENANT_FIELDS, issued_invoice, make_gig
from apps.tenants import logo as logo_files
from apps.tenants.factories import MembershipFactory, TenantFactory

pytestmark = pytest.mark.django_db

# A 1x1 PNG (real, so the PDF engine can draw it) and the start of a JPEG.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 30


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _owner(client, **tenant_fields):
    membership = MembershipFactory(tenant=TenantFactory(**{**TENANT_FIELDS, **tenant_fields}))
    client.force_login(membership.user)
    return membership.tenant


def _profile(tenant, **overrides):
    data = {
        "name": tenant.name,
        "legal_form": tenant.legal_form,
        "siret": "73282932000074",  # a valid SIRET (the check key is controlled)
        "address": tenant.address,
        "postal_code": tenant.postal_code,
        "city": tenant.city,
        "vat_regime": tenant.vat_regime,
        "vat_rate": tenant.vat_rate or "",
    }
    return {**data, **overrides}


def _upload(client, tenant, content=PNG, name="logo.png", **extra):
    return client.post(
        reverse("tenants:settings"),
        _profile(tenant, logo=SimpleUploadedFile(name, content), **extra),
    )


# --- uploading ------------------------------------------------------------------------------------


def test_the_owner_uploads_a_png_and_it_is_stored_privately(client):
    tenant = _owner(client)

    response = _upload(client, tenant)

    tenant.refresh_from_db()
    assert response.status_code == 302 and tenant.logo
    assert tenant.logo.name.startswith("logos/") and tenant.logo.name.endswith("/logo.png")
    assert "logo.png" not in tenant.logo.name.split("/")[1]  # an unguessable folder


def test_a_jpeg_is_accepted_too(client):
    tenant = _owner(client)

    _upload(client, tenant, content=JPEG, name="mon logo.JPEG")

    tenant.refresh_from_db()
    assert tenant.logo.name.endswith("/logo.jpg")


@pytest.mark.parametrize(
    "content, name",
    [
        (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "logo.svg"),
        (b"<svg></svg>", "logo.png"),  # the name lies
        (b"GIF89a....", "logo.png"),
        (b"%PDF-1.4 fake", "logo.png"),
        (b"", "logo.png"),
    ],
)
def test_anything_but_a_png_or_a_jpeg_is_refused(client, content, name):
    tenant = _owner(client)

    response = _upload(client, tenant, content=content, name=name)

    tenant.refresh_from_db()
    assert response.status_code == 200 and not tenant.logo


def test_a_file_over_two_megabytes_is_refused(client, monkeypatch):
    tenant = _owner(client)
    monkeypatch.setattr(logo_files, "MAX_SIZE", 10)

    response = _upload(client, tenant)

    assert response.status_code == 200 and "trop lourd" in response.content.decode()


def test_a_member_who_is_not_the_owner_cannot_change_the_logo(client):
    membership = MembershipFactory(role="member", tenant=TenantFactory(**TENANT_FIELDS))
    client.force_login(membership.user)

    response = _upload(client, membership.tenant)

    membership.tenant.refresh_from_db()
    assert response.status_code == 403 and not membership.tenant.logo


def test_replacing_or_removing_the_logo_deletes_the_old_file(
    client, django_capture_on_commit_callbacks
):
    tenant = _owner(client)
    _upload(client, tenant)
    tenant.refresh_from_db()
    first = tenant.logo.name
    storage = tenant.logo.storage

    with django_capture_on_commit_callbacks(execute=True):
        _upload(client, tenant, content=JPEG, name="b.jpg")
    tenant.refresh_from_db()

    assert tenant.logo.name != first and not storage.exists(first)
    second = tenant.logo.name
    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("tenants:settings"), _profile(tenant, **{"logo-clear": "on"}))
    tenant.refresh_from_db()
    assert not tenant.logo and not storage.exists(second)


# --- on the documents -----------------------------------------------------------------------------


def _tenant_with_logo():
    tenant = TenantFactory(**TENANT_FIELDS)
    tenant.logo.save("logo.png", SimpleUploadedFile("logo.png", PNG), save=True)
    return tenant


def _draft_quote(tenant):
    gig = make_gig(tenant=tenant, price="1000.00")
    return invoicing.create_quote(gig)


def test_the_context_of_a_draft_uses_the_current_logo_as_a_data_address():
    tenant = _tenant_with_logo()

    context = invoicing.build_pdf_context(_draft_quote(tenant))

    assert context["logo_uri"].startswith("data:image/png;base64,")


def test_no_logo_no_image_and_nothing_breaks():
    tenant = TenantFactory(**TENANT_FIELDS)

    context = invoicing.build_pdf_context(_draft_quote(tenant))

    assert context["logo_uri"] == ""


def test_the_pdf_of_a_document_shows_the_logo_only_when_there_is_one():
    from django.template.loader import render_to_string

    with_logo = invoicing.build_pdf_context(_draft_quote(_tenant_with_logo()))
    without = invoicing.build_pdf_context(_draft_quote(TenantFactory(**TENANT_FIELDS)))

    assert "data:image/png;base64," in render_to_string("documents/billing_pdf.html", with_logo)
    assert "<img" not in render_to_string("documents/billing_pdf.html", without)


def test_an_issued_document_keeps_the_logo_it_was_issued_with():
    tenant = _tenant_with_logo()
    invoice = issued_invoice(make_gig(tenant=tenant, price="1000.00"))
    issued_with = invoice.issuer_snapshot["logo"]

    assert issued_with.startswith("document-logos/") and issued_with != tenant.logo.name
    tenant.logo.save("new.jpg", SimpleUploadedFile("new.jpg", JPEG), save=True)
    invoice.refresh_from_db()

    context = invoicing.build_pdf_context(invoice)
    assert context["logo_uri"].startswith("data:image/png;base64,")  # not the new JPEG


def test_an_issued_document_without_logo_has_none():
    invoice = issued_invoice(make_gig())

    assert invoice.issuer_snapshot["logo"] == ""
    assert invoicing.build_pdf_context(invoice)["logo_uri"] == ""


def test_a_missing_file_never_stops_a_document_from_printing():
    assert logo_files.data_uri("logos/gone/logo.png") == ""
    assert logo_files.snapshot_copy("logos/gone/logo.png") == ""


def test_the_contract_context_carries_the_logo():
    tenant = _tenant_with_logo()
    gig = make_gig(tenant=tenant, price="1000.00")

    context = services.build_contract_context(gig, None)

    assert context["logo_uri"].startswith("data:image/png")


def test_a_copy_is_kept_for_an_issued_document():
    tenant = _tenant_with_logo()
    copy = logo_files.snapshot_copy(tenant.logo.name)

    assert copy.startswith("document-logos/") and copy != tenant.logo.name
    assert logo_files.data_uri(copy).startswith("data:image/png")


def test_the_pdf_is_rendered_with_the_logo():
    tenant = _tenant_with_logo()
    gig = make_gig(tenant=tenant, price="1000.00")

    pdf, _annexes = services.render_contract_pdf(gig, None)

    assert pdf.startswith(b"%PDF")


def test_another_structures_logo_never_shows(client):
    _owner(client)
    other = _tenant_with_logo()

    page = client.get(reverse("tenants:settings")).content.decode()

    assert other.logo.name not in page
