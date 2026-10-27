"""Social data of a team member: artist / technician boxes (public), birth date and social
security number (owner only, for the person in charge of the accounts and the paperwork)."""

import datetime

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from ..data_export import build_export_zip
from ..factories import MembershipFactory, PersonFactory
from ..validators import (
    format_social_security_number,
    normalize_social_security_number,
    validate_social_security_number,
)
from .test_team_private import _csv

pytestmark = pytest.mark.django_db

NIR = "185057800608491"
NIR_SPACED = "1 85 05 78 006 084 91"


def _corsican_number():
    """A Corsican number whose key is right (2A counts as 19)."""
    base = "185052A006084"
    key = 97 - int(base.replace("2A", "19")) % 97
    return f"{base}{key:02d}"


def _login(client, role):
    membership = MembershipFactory(role=role)
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {"last_name": "Durand", "first_name": "Léa"}
    data.update(overrides)
    return data


# --- the number ----------------------------------------------------------------------------


def test_a_right_number_is_accepted_with_or_without_spaces():
    validate_social_security_number(NIR)
    validate_social_security_number(NIR_SPACED)
    validate_social_security_number(_corsican_number())


@pytest.mark.parametrize("value", ["185057800608492", "1850578006084", "A85057800608491", "x"])
def test_a_wrong_number_is_refused(value):
    with pytest.raises(ValidationError):
        validate_social_security_number(value)


def test_the_number_is_stored_without_spaces_and_shown_as_on_the_card():
    assert normalize_social_security_number(" 1 85 05 78 006 084 91 ") == NIR
    assert format_social_security_number(NIR) == NIR_SPACED


# --- the owner -----------------------------------------------------------------------------


def test_the_owner_saves_the_boxes_the_birth_date_and_the_number(client):
    tenant = _login(client, "owner")

    response = client.post(
        reverse("tenants:person-create"),
        _payload(
            is_artist="on",
            is_technician="on",
            birth_date="1985-05-17",
            social_security_number=NIR_SPACED,
        ),
    )

    assert response.status_code == 302
    person = tenant.person_set.get()
    assert person.is_artist and person.is_technician
    assert person.birth_date == datetime.date(1985, 5, 17)
    assert person.social_security_number == NIR


def test_the_boxes_default_to_unchecked_and_the_private_fields_are_optional(client):
    tenant = _login(client, "owner")

    client.post(reverse("tenants:person-create"), _payload())

    person = tenant.person_set.get()
    assert (person.is_artist, person.is_technician) == (False, False)
    assert person.birth_date is None and person.social_security_number == ""


def test_a_wrong_number_or_a_future_birth_date_is_refused(client):
    tenant = _login(client, "owner")

    wrong = client.post(
        reverse("tenants:person-create"), _payload(social_security_number="185057800608492")
    )
    future = client.post(
        reverse("tenants:person-create"),
        _payload(birth_date=(datetime.date.today() + datetime.timedelta(days=1)).isoformat()),
    )

    assert wrong.status_code == 200 and "erreur de saisie" in wrong.content.decode()
    assert future.status_code == 200 and "plausible" in future.content.decode()
    assert not tenant.person_set.exists()


def test_the_card_shows_the_age_the_number_and_the_boxes(client):
    tenant = _login(client, "owner")
    person = PersonFactory(
        tenant=tenant,
        is_artist=True,
        birth_date=datetime.date(1985, 5, 17),
        social_security_number=NIR,
    )

    page = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()

    assert "17/05/1985" in page and NIR_SPACED in page and "Artiste" in page
    assert "Technicien" not in page


def test_the_age_is_counted_in_full_years():
    person = PersonFactory(birth_date=datetime.date(1985, 5, 17))

    assert person.age(datetime.date(2026, 5, 16)) == 40
    assert person.age(datetime.date(2026, 5, 17)) == 41
    assert PersonFactory().age() is None


def test_the_owner_export_has_the_new_columns(client):
    tenant = _login(client, "owner")
    PersonFactory(
        tenant=tenant,
        is_technician=True,
        birth_date=datetime.date(1985, 5, 17),
        social_security_number=NIR,
    )

    table = _csv(build_export_zip(tenant, include_private=True), "equipe.csv")

    row = dict(zip(table[0], table[1], strict=True))
    assert row["Technicien"] == "oui" and row["Artiste"] == ""
    assert row["Date de naissance"] == "17/05/1985"
    assert row["N° de sécurité sociale"] == NIR_SPACED


# --- a simple member ----------------------------------------------------------------------


def test_a_member_sees_the_boxes_but_neither_the_birth_date_nor_the_number(client):
    tenant = _login(client, "member")
    person = PersonFactory(
        tenant=tenant,
        is_artist=True,
        birth_date=datetime.date(1985, 5, 17),
        social_security_number=NIR,
    )

    card = client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()
    form = client.get(reverse("tenants:person-update", args=[person.pk])).content.decode()
    listing = client.get(reverse("tenants:person-list")).content.decode()

    assert "Artiste" in card and 'name="is_artist"' in form
    for page in (card, form, listing):
        assert NIR not in page and NIR_SPACED not in page and "17/05/1985" not in page
    assert 'name="social_security_number"' not in form and 'name="birth_date"' not in form


def test_a_member_cannot_overwrite_them_by_posting_them(client):
    tenant = _login(client, "member")
    person = PersonFactory(tenant=tenant, social_security_number=NIR)

    client.post(
        reverse("tenants:person-update", args=[person.pk]),
        _payload(social_security_number="", birth_date="2000-01-01"),
    )

    person.refresh_from_db()
    assert person.social_security_number == NIR and person.birth_date is None


def test_the_member_export_leaves_them_out(client):
    tenant = _login(client, "member")
    PersonFactory(tenant=tenant, social_security_number=NIR, birth_date=datetime.date(1985, 5, 17))

    table = _csv(build_export_zip(tenant, include_private=False), "equipe.csv")

    assert "N° de sécurité sociale" not in table[0] and "Date de naissance" not in table[0]
    assert NIR not in str(table) and NIR_SPACED not in str(table)


def test_another_structure_never_reaches_a_card(client):
    _login(client, "owner")
    foreign = PersonFactory(social_security_number=NIR)

    assert client.get(reverse("tenants:person-detail", args=[foreign.pk])).status_code == 404


# --- the form -----------------------------------------------------------------------------


def test_the_two_boxes_sit_side_by_side_and_the_number_has_its_full_label(client):
    _login(client, "owner")

    page = client.get(reverse("tenants:person-create")).content.decode()
    row = page.split('role="group"')[1].split("</div>")[0]

    assert 'name="is_artist"' in row and 'name="is_technician"' in row
    assert "N° de sécurité sociale" in page and "n° de sécurité sociale :" not in page
