from django.contrib import admin

from .models import Contact, Promoter, Venue

admin.site.register(Promoter)
admin.site.register(Venue)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "tenant")
    filter_horizontal = ("promoters", "venues")
