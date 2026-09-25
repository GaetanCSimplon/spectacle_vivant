from django.db import models
from django.utils.translation import gettext_lazy as _


class Tenant(models.Model):
    """The tenant: the artist, association or company using the app."""

    class VatRegime(models.TextChoices):
        TAXABLE = "taxable", _("Assujetti")
        FRANCHISE = "franchise", _("Franchise en base")
        NOT_TAXABLE = "not_taxable", _("Non assujetti")

    name = models.CharField(_("nom"), max_length=255)
    legal_form = models.CharField(_("forme juridique"), max_length=255, blank=True)
    plan = models.CharField(_("offre"), max_length=50, default="free")
    address = models.TextField(_("adresse"), blank=True)
    siret = models.CharField(_("SIRET"), max_length=14, blank=True)
    vat_regime = models.CharField(
        _("régime de TVA"),
        max_length=20,
        choices=VatRegime.choices,
        default=VatRegime.FRANCHISE,
    )

    def __str__(self):
        return self.name
