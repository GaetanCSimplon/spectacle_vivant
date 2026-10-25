from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AddressMixin, TenantOwnedModel


class Roadmap(TenantOwnedModel):
    """Logistics sheet of a gig (Feuille de route), shareable through a secret link."""

    gig = models.OneToOneField("gigs.Gig", on_delete=models.CASCADE, related_name="roadmap")
    # Empty when sharing is off. Never an ID: see services.publish().
    token = models.CharField(max_length=64, blank=True)
    is_published = models.BooleanField(_("partage activé"), default=False)
    notes = models.TextField(_("notes"), blank=True)
    # Shown to the team: +1 at each saved change made while sharing is on (services.bump_version).
    version = models.PositiveIntegerField(_("version"), default=1)
    updated_at = models.DateTimeField(_("dernière mise à jour"), null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["token"],
                condition=~models.Q(token=""),
                name="unique_roadmap_token",
            ),
        ]

    def __str__(self):
        return f"Feuille de route — {self.gig}"


class RoadmapSlot(TenantOwnedModel):
    """One time slot of the day (arrival, soundcheck, concert…)."""

    class Kind(models.TextChoices):
        ARRIVAL = "arrival", _("Arrivée")
        SOUNDCHECK = "soundcheck", _("Balances")
        MEAL = "meal", _("Repas")
        PERFORMANCE = "performance", _("Concert")
        DEPARTURE = "departure", _("Départ")
        OTHER = "other", _("Autre")

    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="slots")
    kind = models.CharField(_("type"), max_length=20, choices=Kind.choices, default=Kind.OTHER)
    time = models.TimeField(_("heure"))
    label = models.CharField(_("intitulé"), max_length=255, blank=True)
    note = models.TextField(_("note"), blank=True)

    class Meta:
        ordering = ["time", "id"]

    def __str__(self):
        return f"{self.time:%H:%M} {self.label or self.get_kind_display()}"


class Lodging(AddressMixin, TenantOwnedModel):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="lodgings")
    name = models.CharField(_("nom"), max_length=255)
    address = models.CharField(_("adresse"), max_length=255, blank=True)
    arrival_time = models.TimeField(_("heure d'arrivée"), null=True, blank=True)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Meal(TenantOwnedModel):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="meals")
    place = models.CharField(_("lieu"), max_length=255)
    time = models.TimeField(_("heure"), null=True, blank=True)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        ordering = ["time", "id"]

    def __str__(self):
        return self.place
