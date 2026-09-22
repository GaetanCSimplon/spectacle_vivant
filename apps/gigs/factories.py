import datetime

import factory

from apps.addressbook.factories import PromoterFactory, VenueFactory
from apps.catalog.factories import ShowFactory
from apps.organizations.factories import OrganizationFactory

from .models import Gig


class GigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Gig

    organization = factory.SubFactory(OrganizationFactory)
    show = factory.SubFactory(ShowFactory, organization=factory.SelfAttribute("..organization"))
    promoter = factory.SubFactory(
        PromoterFactory, organization=factory.SelfAttribute("..organization")
    )
    venue = factory.SubFactory(VenueFactory, organization=factory.SelfAttribute("..organization"))
    date = factory.LazyFunction(lambda: datetime.date.today() + datetime.timedelta(days=30))
    price = "500.00"
