import datetime

import factory

from apps.gigs.factories import GigFactory

from .models import Expense


class ExpenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Expense

    gig = factory.SubFactory(GigFactory)
    tenant = factory.SelfAttribute("gig.tenant")
    category = Expense.Category.TRANSPORT
    label = "Essence"
    amount = "40.00"
    date = factory.LazyFunction(datetime.date.today)
