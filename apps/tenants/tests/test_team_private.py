"""Address and GUSO number of a team member: owner only, and never on a roadmap."""

import csv
import io
import zipfile

import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.roadmaps import services as roadmap_services

from ..data_export import build_export_zip
from ..factories import MembershipFactory, PersonFactory

pytestmark = pytest.mark.django_db

SECRET_STREET = "12 rue Secrète"
SECRET_GUSO = "GUSO-987654"


def _login(client, role):
    membership = MembershipFactory(role=role)
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {"last_name": "Durand", "first_name": "Léa"}
    data.update(overrides)
    return data


def _private(**overrides):
    data = {
        "address": SECRET_STREET,
        "postal_code": "34 200",
        "city": "Sète",
        "guso_number": SECRET_GUSO,
    }
    data.update(overrides)
    return data


def _person(tenant):
    return PersonFactory(
        tenant=tenant,
        address=SECRET_STREET,
        postal_code="34200",
        city="Sète",
        department="34",
        guso_number=SECRET_GUSO,
    )


def _csv(zip_file, name):
    with zipfile.ZipFile(zip_file) as archive:
        content = archive.read(name).decode("utf-8-sig")
    return list(csv.reader(io.StringIO(content), delimiter=";"))


# --- the owner -------------------------------------------------------------------------


def test_the_owner_saves_the_address_and_the_guso_number(client):
    tenant = _login(client, "owner")

    response = client.post(reverse("tenants:person-create"), _payload(**_private()))

    assert response.status_code == 302
    person = tenant.person_set.get()
    assert (person.address, person.postal_code, person.city) == (SECRET_STREET, "34200", "Sète")
    assert person.department == "34"  # deduced from the postal code
    assert person.guso_number == SECRET_GUSO
    assert person.full_address == f"{SECRET_STREET}\n34200 Sète"


def test_the_owner_sees_them_on_the_card_and_in_the_form(client):
    tenant = _login(client, "owner")
    person = _person(tenant)

    card = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()
    form = client.get(reverse("tenants:person-update", args=[person.pk])).content.decode()

    assert SECRET_STREET in card and SECRET_GUSO in card
    assert 'name="guso_number"' in form and 'name="address"' in form


def test_a_bad_postal_code_is_refused(client):
    tenant = _login(client, "owner")

    response = client.post(reverse("tenants:person-create"), _payload(postal_code="ABCDE"))

    assert response.status_code == 200
    assert not tenant.person_set.exists()


def test_the_fields_are_optional(client):
    tenant = _login(client, "owner")

    client.post(reverse("tenants:person-create"), _payload())

    person = tenant.person_set.get()
    assert (person.address, person.guso_number) == ("", "")


def test_the_owner_export_has_the_private_columns(client):
    tenant = _login(client, "owner")
    _person(tenant)

    table = _csv(build_export_zip(tenant, include_private=True), "equipe.csv")

    row = dict(zip(table[0], table[1], strict=True))
    assert row["Adresse"] == SECRET_STREET and row["N° GUSO"] == SECRET_GUSO
    assert row["Code postal"] == "34200" and row["Ville"] == "Sète"


def test_the_owner_download_view_includes_them(client):
    tenant = _login(client, "owner")
    _person(tenant)

    response = client.post(reverse("tenants:data-export"))

    with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as archive:
        assert SECRET_GUSO in archive.read("equipe.csv").decode("utf-8-sig")


# --- a simple member -------------------------------------------------------------------


def test_a_member_does_not_see_them_on_the_card_or_in_the_form(client):
    tenant = _login(client, "member")
    person = _person(tenant)

    card = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()
    form = client.get(reverse("tenants:person-update", args=[person.pk])).content.decode()
    listing = client.get(reverse("tenants:person-list")).content.decode()

    for page in (card, form, listing):
        assert SECRET_STREET not in page and SECRET_GUSO not in page
    assert 'name="guso_number"' not in form and 'name="address"' not in form


def test_a_member_cannot_write_a_card_at_all(client):
    tenant = _login(client, "member")
    person = _person(tenant)

    created = client.post(reverse("tenants:person-create"), _payload(**_private()))
    edited = client.post(
        reverse("tenants:person-update", args=[person.pk]),
        _payload(role="Guitare", **_private(address="Pirate", guso_number="X")),
    )

    assert (created.status_code, edited.status_code) == (403, 403)
    person.refresh_from_db()
    assert (person.address, person.guso_number) == (SECRET_STREET, SECRET_GUSO)
    assert tenant.person_set.count() == 1


def test_a_member_export_has_no_private_columns(client):
    tenant = _login(client, "member")
    _person(tenant)

    response = client.post(reverse("tenants:data-export"))
    with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as archive:
        content = archive.read("equipe.csv").decode("utf-8-sig")

    assert SECRET_STREET not in content and SECRET_GUSO not in content
    assert "N° GUSO" not in content


def test_the_default_export_is_without_private_columns():
    person = _person(MembershipFactory().tenant)

    table = _csv(build_export_zip(person.tenant), "equipe.csv")

    assert "N° GUSO" not in table[0] and SECRET_GUSO not in str(table)


# --- never on a roadmap ----------------------------------------------------------------


def test_the_private_data_is_not_copied_to_the_roadmap_nor_shown_publicly(client):
    membership = MembershipFactory()
    person = _person(membership.tenant)
    gig = GigFactory(tenant=membership.tenant)
    member = roadmap_services.add_team_member(gig, person)
    roadmap = roadmap_services.get_or_create_roadmap(gig)
    roadmap_services.publish(roadmap)

    context = roadmap_services.public_context(roadmap)
    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()
    pdf = client.get(reverse("roadmap-public-pdf", args=[roadmap.token]))

    assert SECRET_STREET not in str(context) and SECRET_GUSO not in str(context)
    assert SECRET_STREET not in page and SECRET_GUSO not in page
    assert pdf.status_code == 200
    assert SECRET_GUSO.encode() not in pdf.content
    assert not hasattr(member, "guso_number")


def test_another_structure_cannot_change_the_card(client):
    _login(client, "owner")
    other = _person(MembershipFactory().tenant)

    response = client.post(
        reverse("tenants:person-update", args=[other.pk]), _payload(**_private(city="Hack"))
    )

    assert response.status_code == 404
    other.refresh_from_db()
    assert other.city == "Sète"
