from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel

from .validators import validate_iban


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
    code_ape = models.CharField(_("Code APE"), max_length=5, blank=True)
    vat_regime = models.CharField(
        _("régime de TVA"),
        max_length=20,
        choices=VatRegime.choices,
        default=VatRegime.FRANCHISE,
    )
    vat_rate = models.DecimalField(
        _("taux de TVA (%)"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_(
            "Le spectacle vivant a souvent un taux réduit, différent du taux standard : "
            "vérifiez le taux qui s'applique à vos dates. Laissez vide pour l'indiquer "
            "à la main sur le contrat."
        ),
    )
    vat_number = models.CharField(
        _("n° de TVA intracommunautaire"),
        max_length=20,
        blank=True,
        help_text=_("Seulement si vous êtes assujetti à la TVA. Exemple : FR12345678901."),
    )
    iban = models.CharField(
        _("IBAN"),
        max_length=34,
        blank=True,
        validators=[validate_iban],
        help_text=_("Affiché sur vos factures pour être payé par virement."),
    )
    licence_number = models.CharField(_("n° de licence"), max_length=50, blank=True)
    representative_name = models.CharField(_("représentant légal"), max_length=255, blank=True)
    representative_role = models.CharField(_("qualité du représentant"), max_length=255, blank=True)
    jurisdiction_city = models.CharField(
        _("ville du tribunal compétent"), max_length=255, blank=True
    )

    # Set when the owner asks to delete the structure; the data is purged after a grace period.
    deletion_requested_at = models.DateTimeField(
        _("suppression demandée le"), null=True, blank=True
    )

    def __str__(self):
        return self.name


class Person(TenantOwnedModel):
    """A member of the structure's team (artist, musician, technician...). Tracking only:
    nothing here is used to compute pay or social contributions (F-06)."""

    first_name = models.CharField(_("prénom"), max_length=100)
    last_name = models.CharField(_("nom"), max_length=100)
    role = models.CharField(_("fonction"), max_length=100, blank=True)
    status = models.CharField(_("statut"), max_length=100, blank=True)
    phone = models.CharField(_("téléphone"), max_length=30, blank=True)
    email = models.EmailField(_("e-mail"), blank=True)
    average_fee = models.DecimalField(
        _("cachet moyen (€)"), max_digits=10, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = _("personne")
        verbose_name_plural = _("personnes")

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_absolute_url(self):
        return reverse("tenants:person-detail", args=[self.pk])
