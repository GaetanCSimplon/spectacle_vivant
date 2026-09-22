from django.db import models


class TenantOwnedModel(models.Model):
    """Abstract base for models scoped to an Organization (the tenant)."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True
