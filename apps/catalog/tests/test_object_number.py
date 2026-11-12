"""The object number of a show (SPE-02): format 22-3-P-513447-57, typed with or without dashes."""

import pytest
from django.urls import reverse

from apps.catalog.factories import ShowFactory
from apps.catalog.validators import normalize_object_number
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "typed, stored",
    [
        ("223P51344757", "22-3-P-513447-57"),
        ("22-3-P-513447-57", "22-3-P-513447-57"),
        ("22 3 p 513447 57", "22-3-P-513447-57"),
        ("  22.3.P.513447.57 ", "22-3-P-513447-57"),
    ],
)
def test_the_number_is_written_the_same_way_whatever_the_typing(typed, stored):
    assert normalize_object_number(typed) == stored


def test_something_else_is_left_as_typed_by_the_normalizer():
    assert normalize_object_number("OBJ-2") == "OBJ-2"
    assert normalize_object_number("") == ""


def _payload(**overrides):
    data = {
        "title": "Nuits d'été",
        "group_name": "Les Nocturnes",
        "duration_minutes": "75",
        "default_price": "800.00",
        "sacem_object_number": "",
    }
    data.update(overrides)
    return data


def test_the_form_stores_the_normalized_number_and_shows_the_hint(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    page = client.get(reverse("catalog:show-create")).content.decode()
    client.post(reverse("catalog:show-create"), _payload(sacem_object_number="223p51344757"))

    assert "22-3-P-513447-57" in page  # the hint
    from apps.catalog.models import Show

    assert Show.objects.get(tenant=membership.tenant).sacem_object_number == "22-3-P-513447-57"


def test_a_wrong_shape_is_refused_with_an_example(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    response = client.post(reverse("catalog:show-create"), _payload(sacem_object_number="12345"))

    assert (
        response.status_code == 200 and "ressemble à 22-3-P-513447-57" in response.content.decode()
    )


def test_an_old_free_text_value_does_not_block_saving_the_show(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    show = ShowFactory(tenant=membership.tenant, sacem_object_number="OBJ-ancien")

    unchanged = client.post(
        reverse("catalog:show-update", args=[show.pk]),
        _payload(title="Autre titre", sacem_object_number="OBJ-ancien"),
    )
    changed = client.post(
        reverse("catalog:show-update", args=[show.pk]),
        _payload(sacem_object_number="OBJ-nouveau"),
    )

    assert unchanged.status_code == 302
    assert changed.status_code == 200  # a new value must follow the format


def test_the_number_may_stay_empty(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    response = client.post(reverse("catalog:show-create"), _payload())

    assert response.status_code == 302
