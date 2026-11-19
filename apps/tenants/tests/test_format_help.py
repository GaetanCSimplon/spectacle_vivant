import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.tenants.validators import normalize_iban, validate_iban

from ..factories import MembershipFactory

pytestmark = pytest.mark.django_db

IBAN = "FR1420041010050500013M02606"


@pytest.mark.parametrize(
    "value",
    [
        IBAN,
        "FR14 2004 1010 0505 0001 3M02 606",
        "fr14-2004-1010-0505-0001-3m02-606",
        "FR14.2004." + IBAN[8:],
    ],
)
def test_iban_accepts_spaces_dashes_and_dots(value):
    validate_iban(value)
    assert normalize_iban(value) == IBAN


def test_iban_with_a_wrong_key_is_a_typing_mistake():
    with pytest.raises(ValidationError, match="erreur de saisie"):
        validate_iban("FR1520041010050500013M02606")


def test_iban_with_a_wrong_length_says_how_many_characters():
    with pytest.raises(ValidationError, match="vous en avez saisi 3"):
        validate_iban("FR7")


def test_each_formatted_field_has_a_help_button(client):
    client.force_login(MembershipFactory(role="owner").user)

    content = client.get(reverse("tenants:settings")).content.decode()

    for name in ("siret", "code_ape", "postal_code", "vat_number", "iban", "bic"):
        assert f'id="help-id_{name}"' in content
