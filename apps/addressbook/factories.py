import factory

from apps.tenants.factories import TenantFactory

from .models import Contact, Promoter, Venue


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


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact

    promoter = factory.SubFactory(PromoterFactory)
    venue = None
    tenant = factory.LazyAttribute(lambda o: getattr(o.promoter or o.venue, "tenant", None))
    name = factory.Sequence(lambda n: f"Contact {n}")
