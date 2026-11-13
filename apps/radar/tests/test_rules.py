import datetime

import pytest

from apps.addressbook.factories import VenueFactory
from apps.finance.factories import ExpenseFactory
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.radar import rules
from apps.tenants.factories import TenantFactory

pytestmark = pytest.mark.django_db

TODAY = datetime.date(2027, 3, 1)
T = datetime.time


def _gig(tenant=None, days=30, **kwargs):
    tenant = tenant or TenantFactory(
        siret="12345678901234", iban="FR76", bic="ABCDEFGH", city="Pau"
    )
    venue = kwargs.pop("venue", None) or VenueFactory(tenant=tenant, city="Lyon")
    gig = GigFactory(
        tenant=tenant, venue=venue, date=TODAY + datetime.timedelta(days=days), **kwargs
    )
    gig.refresh_from_db()  # the factory keeps the price as typed (a string)
    return gig


def _codes(found):
    return [f.code for f in found]


def test_a_complete_structure_and_date_give_nothing():
    gig = _gig()

    assert rules.all_findings(gig.tenant, TODAY) == []


def test_rad_01_names_what_is_missing_in_the_legal_information():
    tenant = TenantFactory(siret="", iban="FR76", bic="ABCDEFGH")

    (finding,) = rules.tenant_findings(tenant)

    assert finding.code == "RAD-01"
    assert finding.severity == rules.IMPORTANT
    assert "le SIRET" in finding.message and "l'adresse" in finding.message


def test_rad_02_asks_for_iban_and_bic_together():
    tenant = TenantFactory(siret="12345678901234", city="Pau", iban="FR76", bic="")

    assert _codes(rules.tenant_findings(tenant)) == ["RAD-02"]


def test_rad_26_flags_a_venue_without_address_or_city():
    gig = _gig(venue=None)
    gig.venue.city = ""
    gig.venue.save()

    assert _codes(rules.all_findings(gig.tenant, TODAY)) == ["RAD-26"]


def test_rad_35_flags_a_missing_price_but_not_a_free_concert():
    assert _codes(rules.all_findings(_gig(price="0.00").tenant, TODAY)) == ["RAD-35"]
    assert rules.all_findings(_gig(price="0.00", is_free=True).tenant, TODAY) == []


def test_rad_29_flags_expenses_above_the_price_only():
    gig = _gig(price="100.00")
    ExpenseFactory(gig=gig, amount="100.00")
    assert rules.all_findings(gig.tenant, TODAY) == []

    ExpenseFactory(gig=gig, amount="0.01")

    (finding,) = rules.all_findings(gig.tenant, TODAY)
    assert finding.code == "RAD-29"
    assert "100.01" in finding.message


def test_rad_20_only_within_a_week_of_the_concert():
    soon = _gig(days=7, performance_time=T(21, 0))
    far = _gig(days=8)

    found = rules.gig_findings(soon, TODAY)
    assert _codes(found) == ["RAD-20"]
    assert "l'arrivée" in found[0].message and "le concert" not in found[0].message
    assert rules.gig_findings(far, TODAY) == []


def test_rad_20_is_quiet_once_the_times_are_entered():
    gig = _gig(days=3, get_in_time=T(16), soundcheck_time=T(17), performance_time=T(21))

    assert rules.gig_findings(gig, TODAY) == []


def test_rad_22_flags_times_in_the_wrong_order_and_ignores_empty_ones():
    wrong = _gig(get_in_time=T(18), soundcheck_time=T(17))
    gap = _gig(get_in_time=T(16), performance_time=T(21))

    assert _codes(rules.gig_findings(wrong, TODAY)) == ["RAD-22"]
    assert rules.gig_findings(gap, TODAY) == []


def test_cancelled_and_past_dates_are_left_alone():
    tenant = TenantFactory(siret="12345678901234", iban="FR76", bic="ABCDEFGH", city="Pau")
    _gig(tenant, price="0.00", status=Gig.Status.CANCELLED)
    _gig(tenant, days=-1, price="0.00")

    assert rules.all_findings(tenant, TODAY) == []


def test_findings_are_sorted_most_serious_first_then_by_date():
    tenant = TenantFactory(siret="", iban="FR76", bic="ABCDEFGH", city="Pau")
    later = _gig(tenant, days=20, price="0.00")
    sooner = _gig(tenant, days=10, price="0.00")

    found = rules.all_findings(tenant, TODAY)

    assert [f.code for f in found] == ["RAD-01", "RAD-35", "RAD-35"]
    assert [f.gig for f in found[1:]] == [sooner, later]


def test_every_rule_has_its_explanation():
    codes = {f"RAD-{n:02d}" for n in (1, 2, 10, 20, 22, 26, 29, 35)}

    assert codes == set(rules.EXPLANATIONS)
    for explanation in rules.EXPLANATIONS.values():
        assert explanation.why and explanation.admin


def test_rad_10_lists_what_the_contract_of_a_confirmed_date_lacks():
    gig = _gig(status=Gig.Status.CONFIRMED)

    found = rules.gig_findings(gig, TODAY)

    assert _codes(found) == ["RAD-10"]
    assert found[0].severity == rules.IMPORTANT
    for word in ("SIRET", "représentant", "mode de paiement", "lieu de signature"):
        assert word in found[0].message


def test_rad_10_is_quiet_when_complete_and_for_other_statuses():
    complete = _gig(
        status=Gig.Status.CONFIRMED,
        payment_method=Gig.PaymentMethod.TRANSFER,
        signing_place="Lyon",
    )
    complete.promoter.siret = "12345678901234"
    complete.promoter.representative_name = "Marie Durand"
    complete.promoter.representative_role = "Maire"
    option = _gig()  # an option has no contract yet

    assert rules.gig_findings(complete, TODAY) == []
    assert rules.gig_findings(option, TODAY) == []
