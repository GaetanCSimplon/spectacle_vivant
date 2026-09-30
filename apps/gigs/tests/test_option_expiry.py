import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.documents.factories import ContractFactory
from apps.tenants.factories import MembershipFactory

from ..factories import GigFactory
from ..models import Gig, OptionExpiry

pytestmark = pytest.mark.django_db

S = Gig.Status


def _days(n):
    # Same clock as the app (Europe/Paris), so tests do not flake around midnight UTC.
    return timezone.localdate() + datetime.timedelta(days=n)


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


# --- model ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (-3, OptionExpiry("expired", 3)),
        (-1, OptionExpiry("expired", 1)),
        (0, OptionExpiry("soon", 0)),
        (1, OptionExpiry("soon", 1)),
        (7, OptionExpiry("soon", 7)),
        (8, OptionExpiry("ok", 8)),
        (60, OptionExpiry("ok", 60)),
    ],
)
def test_option_expiry_states(offset, expected):
    gig = GigFactory(option_expires_on=_days(offset), date=_days(90))

    assert gig.option_expiry == expected


def test_option_expiry_is_none_without_a_date():
    assert GigFactory().option_expiry is None


@pytest.mark.parametrize("status", [S.CONFIRMED, S.SIGNED, S.CANCELLED])
def test_option_expiry_only_applies_to_a_live_option(status):
    gig = GigFactory(status=status, option_expires_on=_days(2))

    assert gig.option_expiry is None


def test_option_expiry_field_is_optional_in_the_database():
    gig = GigFactory()
    gig.refresh_from_db()

    assert gig.option_expires_on is None


# --- wizard --------------------------------------------------------------


def _run_wizard(client, tenant, **details):
    from apps.addressbook.factories import PromoterFactory, VenueFactory
    from apps.catalog.factories import ShowFactory

    show = ShowFactory(tenant=tenant)
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)
    client.post(reverse("gigs:wizard-show"), {"mode": "existing", "show": show.pk})
    client.post(reverse("gigs:wizard-promoter"), {"mode": "existing", "promoter": promoter.pk})
    client.post(reverse("gigs:wizard-venue"), {"mode": "existing", "venue": venue.pk})
    payload = {"date": _days(30).isoformat(), "price": "800.00", "conditions": ""}
    payload.update(details)
    return client.post(reverse("gigs:wizard-details"), payload)


def test_wizard_stores_the_option_expiry_on_the_gig(client):
    tenant = _login(client)

    response = _run_wizard(client, tenant, option_expires_on=_days(10).isoformat())
    recap = client.get(reverse("gigs:wizard-recap"))
    client.post(reverse("gigs:wizard-recap"))

    assert response.status_code == 302
    assert "Option valable jusqu" in recap.content.decode()
    assert Gig.objects.get().option_expires_on == _days(10)


def test_wizard_works_without_an_option_expiry(client):
    tenant = _login(client)

    _run_wizard(client, tenant)
    recap = client.get(reverse("gigs:wizard-recap"))
    client.post(reverse("gigs:wizard-recap"))

    assert "Option valable jusqu" not in recap.content.decode()
    assert Gig.objects.get().option_expires_on is None


def test_wizard_rejects_an_option_lasting_beyond_the_gig_date(client):
    tenant = _login(client)

    response = _run_wizard(client, tenant, option_expires_on=_days(31).isoformat())

    assert response.status_code == 200
    assert "ne peut pas se prolonger" in response.content.decode()


def test_wizard_accepts_an_option_expiring_on_the_gig_date(client):
    tenant = _login(client)

    response = _run_wizard(client, tenant, option_expires_on=_days(30).isoformat())

    assert response.status_code == 302


def test_wizard_details_step_keeps_the_expiry_when_going_back(client):
    tenant = _login(client)
    _run_wizard(client, tenant, option_expires_on=_days(10).isoformat())

    content = client.get(reverse("gigs:wizard-details")).content.decode()

    assert f'value="{_days(10).isoformat()}"' in content


# --- "Compléter la date" form -------------------------------------------


def _complete_url(gig):
    return reverse("documents:contract-complete", args=[gig.pk])


def test_complete_form_offers_the_expiry_for_an_option(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, option_expires_on=_days(10))

    content = client.get(_complete_url(gig)).content.decode()

    assert 'name="gig-option_expires_on"' in content
    assert f'value="{_days(10).isoformat()}"' in content


def test_complete_form_hides_the_expiry_once_confirmed(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=S.CONFIRMED)

    content = client.get(_complete_url(gig)).content.decode()

    assert "gig-option_expires_on" not in content


def test_complete_form_rejects_an_expiry_after_the_gig_date(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=_days(20))

    response = client.post(_complete_url(gig), {"gig-option_expires_on": _days(25).isoformat()})

    assert response.status_code == 200
    assert "ne peut pas se prolonger" in response.content.decode()
    gig.refresh_from_db()
    assert gig.option_expires_on is None


def test_complete_form_saves_and_can_clear_the_expiry(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=_days(20))

    client.post(_complete_url(gig), {"gig-option_expires_on": _days(5).isoformat()})
    gig.refresh_from_db()
    assert gig.option_expires_on == _days(5)

    client.post(_complete_url(gig), {"gig-option_expires_on": ""})
    gig.refresh_from_db()
    assert gig.option_expires_on is None


def test_confirmed_gig_keeps_its_expiry_untouched_by_the_form(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=S.CONFIRMED, option_expires_on=_days(3))

    client.post(_complete_url(gig), {"gig-option_expires_on": ""})

    gig.refresh_from_db()
    assert gig.option_expires_on == _days(3)


def test_signed_contract_still_freezes_the_form(client):
    tenant = _login(client)
    contract = ContractFactory(
        tenant=tenant, gig__tenant=tenant, gig__option_expires_on=_days(4), status="signed"
    )

    response = client.post(_complete_url(contract.gig), {"gig-option_expires_on": ""})

    assert response.status_code == 302
    contract.gig.refresh_from_db()
    assert contract.gig.option_expires_on == _days(4)


# --- display -------------------------------------------------------------


def test_list_highlights_an_option_about_to_expire(client):
    tenant = _login(client)
    GigFactory(tenant=tenant, date=_days(40), option_expires_on=_days(3))

    content = client.get(reverse("gigs:list")).content.decode()

    assert "expire dans 3 jours" in content


def test_list_highlights_an_expired_option(client):
    tenant = _login(client)
    GigFactory(tenant=tenant, date=_days(40), option_expires_on=_days(-2))

    content = client.get(reverse("gigs:list")).content.decode()

    assert "expirée depuis 2 jours" in content


def test_list_says_nothing_for_a_distant_expiry_or_a_confirmed_gig(client):
    tenant = _login(client)
    GigFactory(tenant=tenant, date=_days(90), option_expires_on=_days(30))
    GigFactory(tenant=tenant, date=_days(40), status=S.CONFIRMED, option_expires_on=_days(2))

    content = client.get(reverse("gigs:list")).content.decode()

    assert "Option :" not in content
    assert "Option expirée" not in content


@pytest.mark.parametrize(
    ("offset", "text"),
    [(0, "expire aujourd"), (1, "expire demain"), (-1, "expirée depuis hier")],
)
def test_singular_and_special_wordings(client, offset, text):
    tenant = _login(client)
    GigFactory(tenant=tenant, date=_days(40), option_expires_on=_days(offset))

    content = client.get(reverse("gigs:list")).content.decode()

    assert text in content


def test_detail_shows_the_expiry_date_and_the_warning(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=_days(40), option_expires_on=_days(2))

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert _days(2).strftime("%d/%m/%Y") in content
    assert "expire dans 2 jours" in content


def test_detail_of_an_expired_option_suggests_to_decide(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=_days(40), option_expires_on=_days(-1))

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert "L&#x27;option a expiré" in content or "L'option a expiré" in content
    assert "Confirmer la date" in content  # still possible, nothing is cancelled automatically


def test_expired_option_is_never_cancelled_automatically(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, date=_days(40), option_expires_on=_days(-5))

    client.get(reverse("gigs:list"))
    client.get(reverse("gigs:detail", args=[gig.pk]))

    gig.refresh_from_db()
    assert gig.status == S.OPTION
