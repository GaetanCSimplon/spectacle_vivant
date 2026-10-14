from django.contrib import admin
from django.db import models

from .models import Show


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    # Same as the show form: a link without a scheme is completed with https://.
    formfield_overrides = {models.URLField: {"assume_scheme": "https"}}
