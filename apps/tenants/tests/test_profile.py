from decimal import Decimal

import pytest
from django.urls import reverse

from apps.tenants.models import Tenant

from ..factories import MembershipFactory, TenantFactory

pytestmark = pytest.mark.django_db

URL = reverse("tenants:profile")


def _login(client, role="owner", **tenant_fields):
    membership = MembershipFactory(role=role, tenant__name="Compagnie A", **tenant_fields)
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {
        "name": "Compagnie du Soleil",
        "legal_form": "Association loi 1901",
        "siret": "12345678900012",
        "address": "1 rue des Arts\n69001 Lyon",
        "vat_regime": "franchise",
        "vat_rate": "",
        "vat_number": "",
        "iban": "",
        "licence_number": "L-2",
        "representative_name": "Julie Martin",
        "representative_role": "Présidente",
        "jurisdiction_city": "Montpellier",
    }
    data.update(overrides)
    return data


def test_profile_requires_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_profile_shows_the_form_to_the_owner(client):
    _login(client)

    response = client.get(URL)

    content = response.content.decode()
    assert response.status_code == 200
    assert 'name="jurisdiction_city"' in content
    assert "Compagnie A" in content
    assert "Enregistrer" in content
    assert "Seul le propriétaire" not in content


def test_owner_can_update_the_tenant(client):
    tenant = _login(client)

    response = client.post(URL, _payload())

    assert response.status_code == 302
    assert response.url == URL
    tenant.refresh_from_db()
    assert tenant.name == "Compagnie du Soleil"
    assert tenant.siret == "12345678900012"
    assert tenant.vat_regime == "franchise"
    assert tenant.jurisdiction_city == "Montpellier"


def test_name_is_required(client):
    tenant = _login(client)

    response = client.post(URL, _payload(name=""))

    assert response.status_code == 200
    tenant.refresh_from_db()
    assert tenant.name == "Compagnie A"


def test_unknown_choice_values_are_rejected(client):
    tenant = _login(client)

    response = client.post(URL, _payload(vat_regime="inconnu"))

    assert response.status_code == 200
    tenant.refresh_from_db()
    assert tenant.vat_regime != "inconnu"
    assert tenant.name == "Compagnie A"


def test_owner_can_set_a_vat_rate(client):
    tenant = _login(client)

    response = client.post(URL, _payload(vat_regime="taxable", vat_rate="2.10"))

    assert response.status_code == 302
    tenant.refresh_from_db()
    assert tenant.vat_rate == Decimal("2.10")


def test_an_invalid_vat_rate_is_rejected(client):
    tenant = _login(client)

    response = client.post(URL, _payload(vat_regime="taxable", vat_rate="123.456"))

    assert response.status_code == 200
    tenant.refresh_from_db()
    assert tenant.vat_rate is None


def test_too_long_siret_is_rejected(client):
    tenant = _login(client)

    response = client.post(URL, _payload(siret="1" * 15))

    assert response.status_code == 200
    tenant.refresh_from_db()
    assert tenant.siret == ""


def test_a_member_sees_the_page_read_only(client):
    _login(client, role="member")

    response = client.get(URL)

    content = response.content.decode()
    assert response.status_code == 200
    assert "Seul le propriétaire" in content
    assert "disabled" in content
    assert "Enregistrer" not in content


def test_a_member_cannot_update_the_tenant(client):
    tenant = _login(client, role="member")

    response = client.post(URL, _payload())

    assert response.status_code == 403
    tenant.refresh_from_db()
    assert tenant.name == "Compagnie A"
    assert tenant.jurisdiction_city == ""


def test_user_without_tenant_is_redirected_to_onboarding_on_get(client):
    membership = MembershipFactory()
    membership.delete()
    client.force_login(membership.user)

    response = client.get(URL)

    assert response.status_code == 302
    assert response.url == reverse("tenants-onboarding")


def test_user_without_tenant_gets_404_on_post(client):
    membership = MembershipFactory()
    membership.delete()
    client.force_login(membership.user)

    assert client.post(URL, _payload()).status_code == 404


def test_profile_only_shows_and_edits_the_current_tenant(client):
    tenant = _login(client)
    other = TenantFactory(name="Compagnie B secrète")

    get_response = client.get(URL)
    client.post(URL, _payload())

    assert "Compagnie B secrète" not in get_response.content.decode()
    other.refresh_from_db()
    assert other.name == "Compagnie B secrète"
    assert other.jurisdiction_city == ""
    tenant.refresh_from_db()
    assert tenant.name == "Compagnie du Soleil"


def test_a_tenant_id_posted_in_the_form_is_ignored(client):
    tenant = _login(client)
    other = TenantFactory(name="Compagnie B")

    client.post(URL, _payload(id=other.pk, pk=other.pk))

    other.refresh_from_db()
    assert other.name == "Compagnie B"
    assert Tenant.objects.get(pk=tenant.pk).name == "Compagnie du Soleil"


def test_owner_can_set_vat_number_and_iban_which_are_cleaned_up(client):
    tenant = _login(client)

    response = client.post(
        URL, _payload(vat_number=" fr 12 345678901 ", iban="fr14 2004 1010 0505 0001 3m02 606")
    )

    assert response.status_code == 302
    tenant.refresh_from_db()
    assert tenant.vat_number == "FR12345678901"
    assert tenant.iban == "FR1420041010050500013M02606"


def test_iban_is_optional(client):
    tenant = _login(client)

    response = client.post(URL, _payload(iban=""))

    assert response.status_code == 302
    tenant.refresh_from_db()
    assert tenant.iban == ""


@pytest.mark.parametrize(
    "iban",
    [
        "FR1420041010050500013M02607",  # wrong key
        "FR14",  # too short
        "1420041010050500013M02606",  # no country
        "FR14 2004 1010 0505 0001 3M02 606 !",
    ],
)
def test_a_wrong_iban_is_rejected(client, iban):
    tenant = _login(client)

    response = client.post(URL, _payload(iban=iban))

    assert response.status_code == 200
    tenant.refresh_from_db()
    assert tenant.iban == ""


def test_vat_number_and_iban_are_not_leaked_to_another_tenant(client):
    _login(client)
    other = TenantFactory(vat_number="FR999", iban="FR1420041010050500013M02606")

    content = client.get(URL).content.decode()

    assert other.vat_number not in content
    assert other.iban not in content


def test_code_ape_is_normalized_and_saved(client):
    tenant = _login(client)

    client.post(URL, _payload(code_ape="90.01 z"))

    tenant.refresh_from_db()
    assert tenant.code_ape == "9001Z"


def test_code_ape_is_optional(client):
    tenant = _login(client, tenant__code_ape="9001Z")

    response = client.post(URL, _payload(code_ape=""))

    assert response.status_code == 302
    tenant.refresh_from_db()
    assert tenant.code_ape == ""


@pytest.mark.parametrize("bad", ["9001", "ABCDE", "90012Z", "9001ZZ"])
def test_invalid_code_ape_is_rejected(client, bad):
    tenant = _login(client)

    response = client.post(URL, _payload(code_ape=bad))

    assert response.status_code == 200
    assert "4 chiffres et 1 lettre" in response.content.decode()
    tenant.refresh_from_db()
    assert tenant.code_ape == ""


def test_code_ape_field_comes_right_after_siret(client):
    _login(client)
    names = list(client.get(URL).context["form"].fields)
    assert names.index("code_ape") == names.index("siret") + 1
