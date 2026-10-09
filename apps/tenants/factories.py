import factory

from apps.accounts.factories import UserFactory
from apps.accounts.models import Membership

from .models import Person, Tenant


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Sequence(lambda n: f"Structure {n}")


class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Membership

    user = factory.SubFactory(UserFactory)
    tenant = factory.SubFactory(TenantFactory)
    role = Membership.Role.OWNER


class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person

    tenant = factory.SubFactory(TenantFactory)
    first_name = factory.Sequence(lambda n: f"Prénom{n}")
    last_name = factory.Sequence(lambda n: f"Nom{n}")
