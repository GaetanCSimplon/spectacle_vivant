import datetime

import factory
from django.utils import timezone

from apps.gigs.factories import GigFactory

from .models import Lodging, Meal, PlaceContact, Roadmap, RoadmapRequest, RoadmapSlot


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


class PlaceContactFactory(factory.django.DjangoModelFactory):
    """A contact of a lodging (pass `meal=...` instead for a meal)."""

    class Meta:
        model = PlaceContact

    lodging = factory.SubFactory(LodgingFactory)
    tenant = factory.SelfAttribute("lodging.tenant")
    name = "Accueil de l'hôtel"
    phone = "04 67 00 00 01"


class RoadmapRequestFactory(factory.django.DjangoModelFactory):
    """An active "Régie de tournée" link (set `completed_at` and `response` for an answered one)."""

    class Meta:
        model = RoadmapRequest

    gig = factory.SubFactory(GigFactory)
    tenant = factory.SelfAttribute("gig.tenant")
    token = factory.Sequence(lambda n: f"token-{n}")
    expires_at = factory.LazyFunction(lambda: timezone.now() + datetime.timedelta(days=7))
