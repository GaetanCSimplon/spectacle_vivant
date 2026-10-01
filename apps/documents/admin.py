from django.contrib import admin

from .models import (
    Contract,
    ContractSequence,
    ContractVersion,
    DocumentLine,
    DocumentSequence,
    Invoice,
    Quote,
)

admin.site.register(Contract)
admin.site.register(ContractVersion)
admin.site.register(ContractSequence)
admin.site.register(Invoice)
admin.site.register(Quote)
admin.site.register(DocumentLine)
admin.site.register(DocumentSequence)
