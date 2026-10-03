from django.contrib import admin

from .models import Gig, GigMember

admin.site.register([Gig, GigMember])
