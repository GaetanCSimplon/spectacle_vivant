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

    # `promoter` and `venue` are conveniences: the contact is attached to them after creation
    # (it can work for several of each: use `contact.promoters.add(...)`).
    promoter = factory.SubFactory(PromoterFactory)
    venue = None
    tenant = factory.LazyAttribute(
        lambda o: getattr(o.promoter or o.venue, "tenant", None) or TenantFactory()
    )
    name = factory.Sequence(lambda n: f"Contact {n}")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        promoter = kwargs.pop("promoter", None)
        venue = kwargs.pop("venue", None)
        contact = super()._create(model_class, *args, **kwargs)
        if promoter is not None:
            contact.promoters.add(promoter)
        if venue is not None:
            contact.venues.add(venue)
        return contact
