from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import GeoPointMixin, TenantOwnedModel


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


class Lodging(GeoPointMixin, TenantOwnedModel):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="lodgings")
    name = models.CharField(_("nom"), max_length=255)
    address = models.CharField(_("adresse"), max_length=255, blank=True)
    arrival_time = models.TimeField(_("heure d'arrivée"), null=True, blank=True)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


def tel_link(phone):
    """A phone number as a tel: link wants it: digits and a leading +, no spaces."""
    return "".join(c for i, c in enumerate(phone.strip()) if c.isdigit() or (c == "+" and i == 0))


class PlaceContact(TenantOwnedModel):
    """Someone to call about a lodging or a meal (reception, caterer...). Seen by whoever has the
    roadmap link, so there is no e-mail address here, like for the other people of a roadmap."""

    lodging = models.ForeignKey(
        Lodging, on_delete=models.CASCADE, null=True, blank=True, related_name="contacts"
    )
    meal = models.ForeignKey(
        "Meal", on_delete=models.CASCADE, null=True, blank=True, related_name="contacts"
    )
    name = models.CharField(_("nom"), max_length=255)
    role = models.CharField(_("fonction"), max_length=100, blank=True)
    phone = models.CharField(_("téléphone"), max_length=50, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            # Exactly one of the two: a contact belongs to a lodging or to a meal.
            models.CheckConstraint(
                condition=models.Q(lodging__isnull=False, meal__isnull=True)
                | models.Q(lodging__isnull=True, meal__isnull=False),
                name="place_contact_one_place",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def tel(self):
        return tel_link(self.phone)


class Meal(TenantOwnedModel):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="meals")
    place = models.CharField(_("lieu"), max_length=255)
    time = models.TimeField(_("heure"), null=True, blank=True)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        ordering = ["time", "id"]

    def __str__(self):
        return self.place


class RoadmapRequest(TenantOwnedModel):
    """The "Régie de tournée" form sent to an organiser for one date (F-90).

    A temporary secret link, like the form of the organiser's card (F-16): valid for a week, used
    once, giving access to nothing but a form. The answers wait in `response` until the owner
    reviews them and applies the ones they choose to the date and its roadmap; `response` is
    emptied afterwards, so the data is not kept twice.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", _("Lien actif")
        ANSWERED = "answered", _("Réponse à vérifier")
        REVIEWED = "reviewed", _("Réponse traitée")
        EXPIRED = "expired", _("Lien expiré")
        REVOKED = "revoked", _("Lien annulé")

    gig = models.ForeignKey("gigs.Gig", on_delete=models.CASCADE, related_name="roadmap_requests")
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Régie de tournée — {self.gig}"

    @property
    def status(self):
        if self.reviewed_at:
            return self.Status.REVIEWED
        if self.completed_at:
            return self.Status.ANSWERED
        if self.revoked_at:
            return self.Status.REVOKED
        if self.expires_at <= timezone.now():
            return self.Status.EXPIRED
        return self.Status.ACTIVE
