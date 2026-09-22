from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel


class Promoter(TenantOwnedModel):
    """The client (Organisateur) who buys the show and gets invoiced."""

    name = models.CharField(_("nom"), max_length=255)
    siret = models.CharField(_("SIRET"), max_length=14, blank=True)
    billing_address = models.TextField(_("adresse de facturation"), blank=True)
    email = models.EmailField(_("e-mail"), blank=True)

    def __str__(self):
        return self.name


class Venue(TenantOwnedModel):
    """The physical place (Lieu / Salle) where the gig happens."""

    name = models.CharField(_("nom"), max_length=255)
    address = models.TextField(_("adresse"), blank=True)

    def __str__(self):
        return self.name
