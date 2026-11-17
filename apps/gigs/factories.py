import datetime

import factory

from apps.addressbook.factories import PromoterFactory, VenueFactory
from apps.catalog.factories import ShowFactory
from apps.tenants.factories import TenantFactory

from .models import Gig, GigMember


class GigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Gig

    tenant = factory.SubFactory(TenantFactory)
    show = factory.SubFactory(ShowFactory, tenant=factory.SelfAttribute("..tenant"))
    promoter = factory.SubFactory(PromoterFactory, tenant=factory.SelfAttribute("..tenant"))
    venue = factory.SubFactory(VenueFactory, tenant=factory.SelfAttribute("..tenant"))
    date = factory.LazyFunction(lambda: datetime.date.today() + datetime.timedelta(days=30))
    price = "500.00"
    # The model starts at 0 (no universal deposit); most tests want a deposit to work with.
    deposit_percent = 30


class GigMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GigMember

    gig = factory.SubFactory(GigFactory)
    tenant = factory.SelfAttribute("gig.tenant")
    name = factory.Faker("name", locale="fr_FR")
