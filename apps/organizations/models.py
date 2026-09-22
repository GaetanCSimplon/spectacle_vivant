from django.db import models
from django.utils.translation import gettext_lazy as _


class Organization(models.Model):
    """The tenant: the artist, association or company using the app."""

    name = models.CharField(_("nom"), max_length=255)
    legal_form = models.CharField(_("forme juridique"), max_length=255, blank=True)
    plan = models.CharField(_("offre"), max_length=50, default="free")

    def __str__(self):
        return self.name
