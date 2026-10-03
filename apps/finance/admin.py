from django.contrib import admin

from .models import Expense, Payment

admin.site.register([Payment, Expense])
