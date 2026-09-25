from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel


class Show(TenantOwnedModel):
    """A show (Spectacle) the artist sells."""

    title = models.CharField(_("titre"), max_length=255)
    group_name = models.CharField(_("nom du groupe / de l'artiste"), max_length=255, blank=True)
    performers = models.TextField(_("distribution"), blank=True)
    duration_minutes = models.PositiveIntegerField(_("durée (minutes)"))
    default_price = models.DecimalField(_("prix indicatif"), max_digits=8, decimal_places=2)
    rider_file = models.FileField(_("fiche d'exigences (rider)"), upload_to="riders/", blank=True)

    def __str__(self):
        return self.title
