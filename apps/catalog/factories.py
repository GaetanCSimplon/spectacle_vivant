import factory

from apps.tenants.factories import TenantFactory

from .models import Show


class ShowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Show

    tenant = factory.SubFactory(TenantFactory)
    title = factory.Sequence(lambda n: f"Spectacle {n}")
    duration_minutes = 60
    default_price = "500.00"
