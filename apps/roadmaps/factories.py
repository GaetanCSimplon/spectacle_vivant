import datetime

import factory

from apps.gigs.factories import GigFactory

from .models import Lodging, Meal, Roadmap, RoadmapSlot


class RoadmapFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Roadmap

    gig = factory.SubFactory(GigFactory)
    tenant = factory.SelfAttribute("gig.tenant")


class _ChildFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    roadmap = factory.SubFactory(RoadmapFactory)
    tenant = factory.SelfAttribute("roadmap.tenant")


class RoadmapSlotFactory(_ChildFactory):
    class Meta:
        model = RoadmapSlot

    time = datetime.time(18, 0)


class LodgingFactory(_ChildFactory):
    class Meta:
        model = Lodging

    name = "Hôtel des Arts"


class MealFactory(_ChildFactory):
    class Meta:
        model = Meal

    place = "Restaurant de la gare"
