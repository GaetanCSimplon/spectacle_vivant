from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel

from . import colors


class Show(TenantOwnedModel):
    """A show (Spectacle) the artist sells."""

    title = models.CharField(_("titre"), max_length=255)
    # A key of `colors.PALETTE` ("" = no colour): tells the shows apart in the lists.
    color = models.CharField(_("couleur"), max_length=20, blank=True, choices=colors.CHOICES)
    group_name = models.CharField(_("nom du groupe / de l'artiste"), max_length=255, blank=True)
    # Free text typed before the distribution became a choice among the team: kept, read only,
    # and shown until at least one member is chosen.
    performers = models.TextField(_("ancienne distribution (texte)"), blank=True)
    cast = models.ManyToManyField(
        "tenants.Person", blank=True, related_name="shows", verbose_name=_("distribution")
    )
    duration_minutes = models.PositiveIntegerField(_("durée (minutes)"))
    default_price = models.DecimalField(_("prix indicatif"), max_digits=8, decimal_places=2)
    sacem_number = models.CharField(_("n° SACEM"), max_length=50, blank=True)
    sacem_object_number = models.CharField(_("n° d'objet"), max_length=50, blank=True)
    rider_file = models.FileField(_("fiche d'exigences (rider)"), upload_to="riders/", blank=True)
    crew_size = models.PositiveIntegerField(
        _("effectif (personnes en tournée)"), null=True, blank=True
    )
    artists_count = models.PositiveIntegerField(_("nombre d'artistes"), null=True, blank=True)
    technicians_count = models.PositiveIntegerField(
        _("nombre de techniciens"), null=True, blank=True
    )
    soundcheck_minutes = models.PositiveIntegerField(
        _("durée minimale des balances (minutes)"), null=True, blank=True
    )
    soundcheck_to_set_minutes = models.PositiveIntegerField(
        _("temps minimum entre la fin des balances et le set (minutes)"), null=True, blank=True
    )
    analytic_code = models.CharField(
        _("code analytique"),
        max_length=30,
        blank=True,
        help_text=_("Pour le suivi et les exports (colonne ajoutée aux fichiers CSV)."),
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

    @property
    def distribution_text(self):
        """Names of the chosen members (a technician only is not a performer), else the old text."""
        people = [p for p in self.cast.all() if p.is_artist or not p.is_technician]
        if people:
            return ", ".join(p.full_name for p in people)
        return self.performers

    @property
    def color_hex(self):
        return colors.hex_of(self.color)

    @property
    def color_name(self):
        return colors.name_of(self.color)

    def get_absolute_url(self):
        return reverse("catalog:show-detail", args=[self.pk])
