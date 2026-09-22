import factory

from apps.organizations.factories import OrganizationFactory

from .models import Show


class ShowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Show

    organization = factory.SubFactory(OrganizationFactory)
    title = factory.Sequence(lambda n: f"Spectacle {n}")
    duration_minutes = 60
    default_price = "500.00"
