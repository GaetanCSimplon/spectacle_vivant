import datetime

import pytest
from django.urls import reverse

from apps.addressbook.factories import VenueFactory
from apps.documents.factories import make_contract_ready
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
        licence_exempt=True, siret="12345678901234", iban="FR76", bic="ABCDEFGH", city="Pau"
    )
    venue = kwargs.pop("venue", None) or VenueFactory(tenant=tenant, city="Lyon")
    kwargs.setdefault("promoter__siret", "12345678901234")
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
    tenant = TenantFactory(licence_exempt=True, siret="", iban="FR76", bic="ABCDEFGH")

    (finding,) = rules.tenant_findings(tenant)

    assert finding.code == "RAD-01"
    assert finding.severity == rules.IMPORTANT
    assert "le SIRET" in finding.message and "l'adresse" in finding.message


def test_rad_02_asks_for_iban_and_bic_together():
    tenant = TenantFactory(
        licence_exempt=True, siret="12345678901234", city="Pau", iban="FR76", bic=""
    )

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
    tenant = TenantFactory(
        licence_exempt=True, siret="12345678901234", iban="FR76", bic="ABCDEFGH", city="Pau"
    )
    _gig(tenant, price="0.00", status=Gig.Status.CANCELLED)
    _gig(tenant, days=-1, price="0.00")

    assert rules.all_findings(tenant, TODAY) == []


def test_findings_are_sorted_most_serious_first_then_by_date():
    tenant = TenantFactory(licence_exempt=True, siret="", iban="FR76", bic="ABCDEFGH", city="Pau")
    later = _gig(tenant, days=20, price="0.00")
    sooner = _gig(tenant, days=10, price="0.00")

    found = rules.all_findings(tenant, TODAY)

    assert [f.code for f in found] == ["RAD-01", "RAD-35", "RAD-35"]
    assert [f.gig for f in found[1:]] == [sooner, later]


def test_every_rule_has_its_explanation():
    codes = {f"RAD-{n:02d}" for n in (1, 2, 10, 11, 20, 22, 26, 29, 35, 40, 41, 42, 43, 44, 65)}

    assert codes == set(rules.EXPLANATIONS)
    for explanation in rules.EXPLANATIONS.values():
        assert explanation.why and explanation.admin


def test_rad_10_counts_what_the_contract_of_a_confirmed_date_lacks():
    gig = _gig(status=Gig.Status.CONFIRMED, promoter__siret="")

    found = [f for f in rules.gig_findings(gig, TODAY) if f.code == "RAD-10"]

    assert _codes(found) == ["RAD-10"]
    assert found[0].severity == rules.IMPORTANT
    assert "éléments à compléter" in found[0].message
    assert found[0].fix_url == reverse("documents:contract-history", args=[gig.pk])


def test_rad_10_is_quiet_when_complete_and_for_other_statuses():
    complete = _gig(status=Gig.Status.CONFIRMED)
    make_contract_ready(complete)
    option = _gig()  # an option has no contract yet

    assert "RAD-10" not in _codes(rules.gig_findings(complete, TODAY))
    assert rules.gig_findings(option, TODAY) == []


def _sent_contract(gig, **version_kwargs):
    """A contract whose latest version was written from the date as it is now, then sent."""
    from django.utils import timezone

    from apps.documents.factories import ContractFactory
    from apps.documents.models import ContractVersion
    from apps.documents.services import contract_key_facts

    contract = ContractFactory(gig=gig, sent_at=timezone.now())
    ContractVersion.objects.create(
        tenant=gig.tenant,
        contract=contract,
        number=1,
        key_facts=version_kwargs.pop("key_facts", contract_key_facts(gig)),
        pdf_file="x.pdf",
    )
    return contract


def _rad_11(gig):
    gig = Gig.objects.get(pk=gig.pk)
    return [f for f in rules.gig_findings(gig, TODAY) if f.code == "RAD-11"]


def test_rad_11_is_quiet_while_the_sent_contract_matches_the_date():
    gig = _gig(status=Gig.Status.CONFIRMED)
    _sent_contract(gig)

    assert _rad_11(gig) == []


def test_rad_11_names_what_changed_after_the_contract_was_sent():
    gig = _gig(status=Gig.Status.CONFIRMED, price="3000.00")
    _sent_contract(gig)
    gig.price = "3200.00"
    gig.date += datetime.timedelta(days=1)
    gig.venue = VenueFactory(tenant=gig.tenant, name="Autre salle")
    gig.save()

    found = _rad_11(gig)

    assert _codes(found) == ["RAD-11"]
    assert found[0].severity == rules.IMPORTANT
    assert "3000.00" in found[0].message and "3200.00" in found[0].message
    assert "le jour du concert" in found[0].message and "le lieu" in found[0].message
    assert found[0].fix_url == reverse("documents:contract-history", args=[gig.pk])


def test_rad_11_ignores_drafts_old_versions_and_a_signed_contract_that_still_matches():
    from apps.documents.factories import ContractFactory
    from apps.documents.models import Contract

    draft = _gig(status=Gig.Status.CONFIRMED)
    contract = _sent_contract(draft)
    contract.sent_at = None
    contract.save()
    draft.price = "1.00"
    draft.save()

    old = _gig(status=Gig.Status.CONFIRMED)
    _sent_contract(old, key_facts={})  # a version written before RAD-11 states nothing
    old.price = "1.00"
    old.save()

    signed = _gig(status=Gig.Status.CONFIRMED)
    ContractFactory(gig=signed, status=Contract.Status.SIGNED)

    assert _rad_11(draft) == [] and _rad_11(old) == [] and _rad_11(signed) == []


def test_rad_11_is_read_for_a_signed_contract_and_shown_before_signing():
    from apps.documents.models import Contract

    gig = _gig(status=Gig.Status.CONFIRMED, price="3000.00")
    contract = _sent_contract(gig)
    contract.status = Contract.Status.SIGNED
    contract.save()
    gig.price = "100.00"
    gig.save()
    gig = Gig.objects.get(pk=gig.pk)

    assert "RAD-11" in _codes(rules.for_action("contract_sign", gig, TODAY))
    assert "RAD-11" not in _codes(rules.for_action("contract_send", gig, TODAY))


def test_generating_a_contract_records_its_key_facts():
    from apps.documents.services import generate_contract_pdf

    gig = _gig(status=Gig.Status.CONFIRMED, price="2500.00")
    make_contract_ready(gig)

    version = generate_contract_pdf(gig).latest_version

    assert version.key_facts == {
        "price": "2500.00",
        "date": gig.date.isoformat(),
        "venue_id": gig.venue_id,
        "venue": gig.venue.name,
    }
