import factory

from apps.gigs.factories import GigFactory

from .models import Contract


class ContractFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contract

    tenant = factory.SelfAttribute("gig.tenant")
    gig = factory.SubFactory(GigFactory)


def make_contract_ready(gig):
    """Fill in everything the contract checks ask for, and confirm what needs confirming."""
    import datetime

    from . import checks

    tenant, promoter, venue, show = gig.tenant, gig.promoter, gig.venue, gig.show
    for obj, values in (
        (
            tenant,
            dict(
                name="Les Nocturnes",
                legal_form="Association loi 1901",
                siret="73282932000074",
                address="1 rue des Arts",
                postal_code="69001",
                city="Lyon",
                contact_name="Léa Roux",
                email="prod@nocturnes.fr",
                phone="0102030405",
                licence_exempt=False,
                licence_number="L-1",
                licence_categories="2",
                licence_valid_until=datetime.date(2099, 1, 1),
                vat_confirmed_on=datetime.date(2026, 1, 1),
            ),
        ),
        (
            promoter,
            dict(
                billing_address="2 place du Marché",
                postal_code="31000",
                city="Toulouse",
                legal_form="Association",
                siret="73282932000074",
                licence_exempt=False,
                licence_number="L-2",
                licence_categories="1",
                representative_name="Paul Durand",
                representative_role="Maire",
                admin_contact_name="Sam Petit",
                admin_contact_email="sam@asso.fr",
                phone="0102030406",
            ),
        ),
        (venue, dict(address="3 rue du Port", city="Toulouse", capacity=300)),
        (show, dict(group_name="Les Nocturnes", tech_sheet_text="Scène 6 x 4 m, 2 prises.")),
        (
            gig,
            dict(
                setting="indoor",
                performance_time=datetime.time(21, 0),
                get_in_time=datetime.time(16, 0),
                soundcheck_time=datetime.time(17, 0),
                crew_headcount=4,
                meals_covered_by="none",
                lodging_covered_by="none",
                transport_covered_by="none",
                deposit_required=False,
                deposit_percent=0,
                balance_due_on=gig.date,
                billing_notes="Facture à l'organisateur",
                onsite_contact_name="Sam",
            ),
        ),
    ):
        for name, value in values.items():
            setattr(obj, name, value)
        obj.save()
    promoter.representative_confirmed_as = promoter.signatory_key
    promoter.save()
    contract, _created = Contract.objects.get_or_create(gig=gig, tenant=gig.tenant)
    contract.signatory_name, contract.signatory_role = "Léa Roux", "Trésorière"
    contract.save()
    gig.refresh_from_db()  # the factory keeps the price as typed (a string)
    for anomaly in checks.check_contract(gig, contract):
        if anomaly.level == checks.CONFIRMATION:
            checks.confirm(gig, anomaly.code, None)
    gig.refresh_from_db()  # drops the cached contract: a test reads it again from the database
    return contract
