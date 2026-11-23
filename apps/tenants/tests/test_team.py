"""The team directory (F-06): people who work with the structure. Tracking only."""

import csv
import io
import zipfile

import pytest
from django.urls import reverse

from apps.core.tests.isolation_registry import mark_isolation_tested

from ..data_export import build_export_zip
from ..factories import MembershipFactory, PersonFactory, TenantFactory
from ..models import Person

mark_isolation_tested(Person)

pytestmark = pytest.mark.django_db

LIST = "tenants:person-list"


def _login(client, role="owner"):
    membership = MembershipFactory(role=role)
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {"last_name": "Durand", "first_name": "Léa", "role": "Chanteuse"}
    data.update(overrides)
    return data


# --- CRUD ----------------------------------------------------------------------------


def test_a_member_reads_the_team_but_cannot_change_it(client):
    tenant = _login(client, role="member")
    person = PersonFactory(tenant=tenant)

    assert client.get(reverse(LIST)).status_code == 200
    assert client.get(reverse("tenants:person-detail", args=[person.pk])).status_code == 200
    assert client.post(reverse("tenants:person-create"), _payload()).status_code == 403
    assert client.get(reverse("tenants:person-update", args=[person.pk])).status_code == 403
    assert client.post(reverse("tenants:person-delete", args=[person.pk])).status_code == 403
    assert Person.objects.filter(tenant=tenant).count() == 1


def test_only_names_are_required(client):
    tenant = _login(client)

    client.post(reverse("tenants:person-create"), {"last_name": "Seul", "first_name": "Un"})
    response = client.post(reverse("tenants:person-create"), {"last_name": "SansPrenom"})

    assert Person.objects.filter(tenant=tenant).count() == 1
    assert response.status_code == 200


@pytest.mark.parametrize("fee", ["-5", "abc"])
def test_an_invalid_fee_is_refused(client, fee):
    tenant = _login(client)

    response = client.post(reverse("tenants:person-create"), _payload(average_fee=fee))

    assert response.status_code == 200
    assert not Person.objects.filter(tenant=tenant).exists()


def test_a_person_can_be_edited_and_deleted(client):
    tenant = _login(client)
    person = PersonFactory(tenant=tenant, last_name="Ancien")

    client.post(reverse("tenants:person-update", args=[person.pk]), _payload())
    person.refresh_from_db()
    assert person.last_name == "Durand"

    page = client.get(reverse("tenants:person-delete", args=[person.pk]))
    assert page.status_code == 200
    client.post(reverse("tenants:person-delete", args=[person.pk]))
    assert not Person.objects.filter(pk=person.pk).exists()


def test_the_tenant_cannot_be_chosen_from_the_form(client):
    tenant = _login(client)
    other = TenantFactory()

    client.post(reverse("tenants:person-create"), _payload(tenant=other.pk))

    assert Person.objects.get().tenant == tenant


def test_list_and_search(client):
    tenant = _login(client)
    PersonFactory(tenant=tenant, first_name="Léa", last_name="Durand", role="Chanteuse")
    PersonFactory(tenant=tenant, first_name="Marc", last_name="Petit", status="Intermittent")

    everyone = client.get(reverse(LIST))
    assert [p.last_name for p in everyone.context["object_list"]] == ["Durand", "Petit"]
    by_role = client.get(reverse(LIST), {"q": "chanteuse"})
    assert [p.last_name for p in by_role.context["object_list"]] == ["Durand"]
    assert (
        "Aucune personne ne correspond" in client.get(reverse(LIST), {"q": "zzz"}).content.decode()
    )


def test_the_page_shows_the_two_tabs_and_the_fee_only_on_the_card(client):
    tenant = _login(client)
    person = PersonFactory(tenant=tenant, average_fee="300.00")

    listing = client.get(reverse(LIST)).content.decode()
    detail = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()

    assert "Fiche" in listing and "Équipe" in listing
    assert "300.00" not in listing
    assert "Cachet moyen" in detail


def test_the_form_proposes_the_structures_own_roles(client):
    tenant = _login(client)
    PersonFactory(tenant=tenant, role="Accordéoniste")
    PersonFactory(role="Rôle secret d'un autre")

    content = client.get(reverse("tenants:person-create")).content.decode()

    assert "Accordéoniste" in content and "Chanteur" in content
    assert "secret d" not in content


# --- login and isolation ---------------------------------------------------------------


def test_team_pages_need_a_login(client):
    person = PersonFactory()
    for name, args in (
        (LIST, []),
        ("tenants:person-create", []),
        ("tenants:person-detail", [person.pk]),
        ("tenants:person-update", [person.pk]),
        ("tenants:person-delete", [person.pk]),
    ):
        response = client.get(reverse(name, args=args))
        assert response.url.startswith(reverse("account_login")), name


def test_another_tenant_gets_404_and_sees_nobody(client):
    _login(client)
    other = PersonFactory(last_name="Cachée")

    for name in ("tenants:person-detail", "tenants:person-update", "tenants:person-delete"):
        assert client.get(reverse(name, args=[other.pk])).status_code == 404
    assert client.post(reverse("tenants:person-delete", args=[other.pk])).status_code == 404
    assert (
        client.post(reverse("tenants:person-update", args=[other.pk]), _payload()).status_code
        == 404
    )
    assert "Cachée" not in client.get(reverse(LIST)).content.decode()
    assert Person.objects.filter(pk=other.pk, last_name="Cachée").exists()


# --- export ----------------------------------------------------------------------------


def test_the_data_export_holds_only_the_teams_own_people():
    tenant = TenantFactory()
    PersonFactory(tenant=tenant, last_name="Durand", first_name="Léa", average_fee="250.00")
    PersonFactory(tenant=tenant, last_name="Sans", first_name="Cachet")
    PersonFactory(last_name="Etranger")

    archive = zipfile.ZipFile(build_export_zip(tenant))
    rows = list(
        csv.reader(io.StringIO(archive.read("equipe.csv").decode("utf-8-sig")), delimiter=";")
    )

    assert rows[0][:3] == ["Nom", "Prénom", "Fonction"]
    assert [r[0] for r in rows[1:]] == ["Durand", "Sans"]
    column = rows[0].index("Cachet moyen")
    assert rows[1][column] == "250,00" and rows[2][column] == ""
