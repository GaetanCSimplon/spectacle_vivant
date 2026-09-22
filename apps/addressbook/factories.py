import factory

from apps.organizations.factories import OrganizationFactory

from .models import Promoter, Venue


class PromoterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Promoter

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Organisateur {n}")


class VenueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Venue

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Salle {n}")
