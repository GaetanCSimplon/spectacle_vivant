from django.contrib import admin

from .models import Contract, ContractSequence, ContractVersion

admin.site.register(Contract)
admin.site.register(ContractVersion)
admin.site.register(ContractSequence)
