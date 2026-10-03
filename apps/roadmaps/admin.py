from django.contrib import admin

from .models import Lodging, Meal, Roadmap, RoadmapSlot

admin.site.register([Roadmap, RoadmapSlot, Lodging, Meal])
