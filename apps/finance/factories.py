import datetime

import factory

from apps.gigs.factories import GigFactory

from .models import Expense, ExpenseClaim


class ExpenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Expense

    gig = factory.SubFactory(GigFactory)
    tenant = factory.SelfAttribute("gig.tenant")
    category = Expense.Category.TRANSPORT
    label = "Essence"
    amount = "40.00"
    date = factory.LazyFunction(datetime.date.today)


class ExpenseClaimFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExpenseClaim

    gig = factory.SubFactory(GigFactory)
    tenant = factory.SelfAttribute("gig.tenant")
    person = factory.SubFactory(
        "apps.tenants.factories.PersonFactory", tenant=factory.SelfAttribute("..tenant")
    )
    category = Expense.Category.TRANSPORT
    label = "Train"
    amount = "30.00"
    date = factory.LazyFunction(datetime.date.today)
