from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel


class Contract(TenantOwnedModel):
    """The cession contract (Contrat de cession) PDF linked to a Gig."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Brouillon")
        SIGNED = "signed", _("Signé")

    gig = models.OneToOneField("gigs.Gig", on_delete=models.CASCADE, related_name="contract")
    status = models.CharField(
        _("statut"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    pdf_file = models.FileField(_("fichier PDF"), upload_to="contracts/", blank=True)
    generated_at = models.DateTimeField(_("généré le"), null=True, blank=True)

    def __str__(self):
        return f"Contrat — {self.gig}"
