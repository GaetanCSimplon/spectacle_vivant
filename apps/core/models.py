from django.db import models


class TenantOwnedModel(models.Model):
    """Abstract base for models scoped to an Organization (the tenant)."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class Note(TenantOwnedModel):
    """Disposable model used only to validate the tenant isolation mechanism."""

    text = models.TextField(blank=True)

    def __str__(self):
        return self.text[:50]
