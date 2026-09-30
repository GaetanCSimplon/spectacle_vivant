from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel


class Show(TenantOwnedModel):
    """A show (Spectacle) the artist sells."""

    title = models.CharField(_("titre"), max_length=255)
    group_name = models.CharField(_("nom du groupe / de l'artiste"), max_length=255, blank=True)
    performers = models.TextField(_("distribution"), blank=True)
    duration_minutes = models.PositiveIntegerField(_("durée (minutes)"))
    default_price = models.DecimalField(_("prix indicatif"), max_digits=8, decimal_places=2)
    sacem_number = models.CharField(_("n° SACEM"), max_length=50, blank=True)
    sacem_object_number = models.CharField(_("n° d'objet"), max_length=50, blank=True)
    rider_file = models.FileField(_("fiche d'exigences (rider)"), upload_to="riders/", blank=True)
    crew_size = models.PositiveIntegerField(
        _("effectif (personnes en tournée)"), null=True, blank=True
    )
    tech_sheet_text = models.TextField(_("fiche technique"), blank=True)
    tech_sheet_file = models.FileField(
        _("fiche technique (PDF)"),
        upload_to="tech_sheets/",
        blank=True,
        validators=[FileExtensionValidator(["pdf"])],
    )
    epk_url = models.URLField(_("lien du dossier de presse (EPK)"), blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("catalog:show-detail", args=[self.pk])
