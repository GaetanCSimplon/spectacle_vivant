import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory, TenantFactory

from ..factories import ShowFactory
from ..models import Show

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {
        "title": "Nuits d'été",
        "group_name": "Les Nocturnes",
        "performers": "",
        "duration_minutes": "75",
        "default_price": "800.00",
        "crew_size": "",
        "tech_sheet_text": "",
        "epk_url": "",
        "sacem_number": "",
        "sacem_object_number": "",
    }
    data.update(overrides)
    return data


def _pdf(name="fiche.pdf", content=b"%PDF-1.4 test"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def test_show_list_requires_login(client):
    response = client.get(reverse("catalog:show-list"))

    assert response.status_code == 302


def test_show_list_only_shows_the_current_tenants_shows(client):
    tenant = _login(client)
    ShowFactory(tenant=tenant, title="Le mien")
    ShowFactory(title="Un autre")

    content = client.get(reverse("catalog:show-list")).content.decode()

    assert "Le mien" in content
    assert "Un autre" not in content


def test_show_search_by_title_or_group(client):
    tenant = _login(client)
    ShowFactory(tenant=tenant, title="Nuits d'été", group_name="Les Nocturnes")
    ShowFactory(tenant=tenant, title="Aube", group_name="Trio Matin")
    url = reverse("catalog:show-list")

    by_title = client.get(url, {"q": "nuits"}).content.decode()
    by_group = client.get(url, {"q": "matin"}).content.decode()
    fragment = client.get(url, {"q": "nuits"}, **HTMX).content.decode()

    assert "Nuits" in by_title and "Aube" not in by_title
    assert "Aube" in by_group and "Nuits" not in by_group
    assert "<html" not in fragment


def test_show_search_never_returns_another_tenants_show(client):
    _login(client)
    ShowFactory(title="Nuits d'été")

    content = client.get(reverse("catalog:show-list"), {"q": "nuits"}).content.decode()

    assert "Nuits" not in content


def test_create_a_show(client):
    tenant = _login(client)

    response = client.post(
        reverse("catalog:show-create"),
        _payload(crew_size="4", epk_url="https://exemple.fr/epk", tech_sheet_text="2 micros"),
    )

    show = Show.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("catalog:show-detail", args=[show.pk])
    assert show.tenant == tenant
    assert (show.crew_size, show.epk_url, show.tech_sheet_text) == (
        4,
        "https://exemple.fr/epk",
        "2 micros",
    )


@pytest.mark.parametrize("field", ["title", "duration_minutes", "default_price"])
def test_required_fields_to_create_a_show(client, field):
    _login(client)

    response = client.post(reverse("catalog:show-create"), _payload(**{field: ""}))

    assert response.status_code == 200
    assert not Show.objects.exists()


def test_epk_must_be_a_valid_url(client):
    _login(client)

    response = client.post(reverse("catalog:show-create"), _payload(epk_url="pas un lien"))

    assert response.status_code == 200
    assert not Show.objects.exists()


def test_tech_sheet_file_must_be_a_pdf(client):
    _login(client)

    response = client.post(
        reverse("catalog:show-create"),
        {**_payload(), "tech_sheet_file": SimpleUploadedFile("fiche.exe", b"MZ")},
    )

    assert response.status_code == 200
    assert not Show.objects.exists()


def test_form_ignores_a_tenant_sent_by_the_client(client):
    tenant = _login(client)
    other = TenantFactory()

    client.post(reverse("catalog:show-create"), _payload(tenant=other.pk))

    assert Show.objects.get().tenant == tenant


def test_show_detail_shows_its_gigs(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)
    gig = GigFactory(tenant=tenant, show=show)

    content = client.get(reverse("catalog:show-detail", args=[show.pk])).content.decode()

    assert show.title in content
    assert gig.promoter.name in content


def test_show_detail_of_another_tenant_returns_404(client):
    _login(client)
    other = ShowFactory()

    response = client.get(reverse("catalog:show-detail", args=[other.pk]))

    assert response.status_code == 404


def test_update_a_show(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant, title="Ancien titre")

    response = client.post(
        reverse("catalog:show-update", args=[show.pk]), _payload(title="Nouveau titre")
    )

    assert response.status_code == 302
    show.refresh_from_db()
    assert show.title == "Nouveau titre"


def test_cannot_update_another_tenants_show(client):
    _login(client)
    other = ShowFactory(title="Ancien titre")

    response = client.post(
        reverse("catalog:show-update", args=[other.pk]), _payload(title="Nouveau titre")
    )

    assert response.status_code == 404
    other.refresh_from_db()
    assert other.title == "Ancien titre"


def test_delete_a_show_without_gigs(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)

    response = client.post(reverse("catalog:show-delete", args=[show.pk]))

    assert response.status_code == 302
    assert not Show.objects.exists()


def test_cannot_delete_a_show_used_by_a_gig(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)
    GigFactory(tenant=tenant, show=show)

    response = client.post(reverse("catalog:show-delete", args=[show.pk]))

    assert response.status_code == 302
    assert Show.objects.filter(pk=show.pk).exists()


def test_cannot_delete_another_tenants_show(client):
    _login(client)
    other = ShowFactory()

    response = client.post(reverse("catalog:show-delete", args=[other.pk]))

    assert response.status_code == 404
    assert Show.objects.filter(pk=other.pk).exists()


def test_upload_then_download_the_tech_sheet(client):
    tenant = _login(client)
    response = client.post(
        reverse("catalog:show-create"), {**_payload(), "tech_sheet_file": _pdf()}
    )
    show = Show.objects.get()
    assert response.status_code == 302 and show.tenant == tenant

    download = client.get(reverse("catalog:show-file", args=[show.pk, "fiche-technique"]))

    assert download.status_code == 200
    assert b"".join(download.streaming_content) == b"%PDF-1.4 test"
    assert download["Content-Disposition"].startswith("attachment")


def test_download_the_rider(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant, rider_file=SimpleUploadedFile("rider.txt", b"2 loges"))

    download = client.get(reverse("catalog:show-file", args=[show.pk, "rider"]))

    assert b"".join(download.streaming_content) == b"2 loges"


def test_download_without_a_file_or_with_unknown_kind_returns_404(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)

    assert client.get(reverse("catalog:show-file", args=[show.pk, "rider"])).status_code == 404
    assert client.get(reverse("catalog:show-file", args=[show.pk, "autre"])).status_code == 404


def test_cannot_download_another_tenants_file(client):
    _login(client)
    other = ShowFactory(rider_file=SimpleUploadedFile("rider.txt", b"secret"))

    response = client.get(reverse("catalog:show-file", args=[other.pk, "rider"]))

    assert response.status_code == 404


def test_download_requires_login(client):
    show = ShowFactory(rider_file=SimpleUploadedFile("rider.txt", b"secret"))

    response = client.get(reverse("catalog:show-file", args=[show.pk, "rider"]))

    assert response.status_code == 302
