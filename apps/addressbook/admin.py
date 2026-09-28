from django.contrib import admin

from .models import Contact, Promoter, Venue

admin.site.register(Promoter)
admin.site.register(Venue)
admin.site.register(Contact)
