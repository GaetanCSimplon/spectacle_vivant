import factory

from apps.tenants.factories import TenantFactory

from .models import Promoter, Venue


class PromoterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Promoter

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Organisateur {n}")


class VenueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Venue

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Salle {n}")
