import factory

from apps.gigs.factories import GigFactory

from .models import Contract


class ContractFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contract

    tenant = factory.SelfAttribute("gig.tenant")
    gig = factory.SubFactory(GigFactory)
