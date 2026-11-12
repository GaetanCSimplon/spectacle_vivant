"""The dates an organiser usually programmes, as ranges that come back every year (ORG-03)."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.addressbook import date_ranges
from apps.addressbook.factories import PromoterFactory
from apps.addressbook.models import Promoter
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "typed, stored",
    [
        ("10/07 au 25/07", {"start": "07-10", "end": "07-25"}),
        ("du 10/07 au 25/07", {"start": "07-10", "end": "07-25"}),
        ("1/7-9/7", {"start": "07-01", "end": "07-09"}),
        ("15.12 à 05.01", {"start": "12-15", "end": "01-05"}),  # across the new year
        ("29/02 au 02/03", {"start": "02-29", "end": "03-02"}),  # comes back each year
    ],
)
def test_a_range_is_read_whatever_the_separators(typed, stored):
    assert date_ranges.parse_range(typed) == stored


def test_an_empty_field_is_no_range():
    assert date_ranges.parse_range("  ") is None


@pytest.mark.parametrize(
    "typed", ["juillet", "10/07", "31/02 au 05/03", "10/13 au 12/13", "0/7 au 5/7"]
)
def test_a_wrong_range_is_refused(typed):
    with pytest.raises(ValidationError):
        date_ranges.parse_range(typed)


def test_a_range_is_written_for_the_field_and_for_a_page():
    stored = {"start": "07-10", "end": "07-25"}

    assert date_ranges.input_text(stored) == "10/07 au 25/07"
    assert date_ranges.label(stored) == "du 10 juillet au 25 juillet"


def _post(client, promoter=None, **ranges):
    data = {"name": "Festival du Lac", **ranges}
    if promoter is None:
        return client.post(reverse("addressbook:promoter-create"), data)
    return client.post(reverse("addressbook:promoter-update", args=[promoter.pk]), data)


def test_the_form_stores_up_to_three_ranges_and_the_page_shows_them(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    response = _post(
        client,
        usual_range_1="10/07 au 25/07",
        usual_range_2="15/12 au 05/01",
        usual_range_3="",
    )

    promoter = Promoter.objects.get(tenant=membership.tenant)
    assert promoter.usual_date_ranges == [
        {"start": "07-10", "end": "07-25"},
        {"start": "12-15", "end": "01-05"},
    ]
    page = client.get(response.url).content.decode()
    assert "du 10 juillet au 25 juillet" in page and "du 15 décembre au 5 janvier" in page


def test_the_form_shows_the_stored_ranges_and_keeps_them_on_save(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    promoter = PromoterFactory(
        tenant=membership.tenant, usual_date_ranges=[{"start": "07-10", "end": "07-25"}]
    )

    page = client.get(reverse("addressbook:promoter-update", args=[promoter.pk])).content.decode()
    _post(client, promoter, usual_range_1="10/07 au 25/07")

    assert 'value="10/07 au 25/07"' in page
    promoter.refresh_from_db()
    assert promoter.usual_date_ranges == [{"start": "07-10", "end": "07-25"}]


def test_clearing_the_fields_removes_the_ranges(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    promoter = PromoterFactory(
        tenant=membership.tenant, usual_date_ranges=[{"start": "07-10", "end": "07-25"}]
    )

    _post(client, promoter, usual_range_1="")

    promoter.refresh_from_db()
    assert promoter.usual_date_ranges == []


def test_an_impossible_date_is_refused_with_a_message_and_nothing_is_saved(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    response = _post(client, usual_range_1="31/02 au 05/03")

    assert response.status_code == 200
    assert "pas dans le calendrier" in response.content.decode()
    assert not Promoter.objects.filter(tenant=membership.tenant).exists()


def test_the_account_export_lists_the_ranges(client):
    from apps.tenants.data_export import promoters_rows

    membership = MembershipFactory()
    PromoterFactory(
        tenant=membership.tenant, usual_date_ranges=[{"start": "07-10", "end": "07-25"}]
    )

    header, rows = promoters_rows(membership.tenant)

    assert "Plages de dates habituelles" in header
    assert any("du 10 juillet au 25 juillet" in row for row in rows[0])


def test_another_structures_ranges_never_show(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    other = PromoterFactory(usual_date_ranges=[{"start": "08-01", "end": "08-09"}])

    assert client.get(reverse("addressbook:promoter-detail", args=[other.pk])).status_code == 404
