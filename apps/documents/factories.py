import factory

from apps.gigs.factories import GigFactory

from .models import Contract


class ContractFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contract

    organization = factory.SelfAttribute("gig.organization")
    gig = factory.SubFactory(GigFactory)
