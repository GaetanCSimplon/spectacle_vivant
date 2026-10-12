from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import AddressMixin, TenantOwnedModel


class Promoter(AddressMixin, TenantOwnedModel):
    """The client (Organisateur) who buys the show and gets invoiced."""

    street_field = "billing_address"

    class Kind(models.TextChoices):
        MUNICIPALITY = "municipality", _("Mairie / collectivité")
        FESTIVAL = "festival", _("Festival")
        VENUE = "venue", _("Salle / théâtre")
        ASSOCIATION = "association", _("Association")
        BAR = "bar", _("Bar / café-concert")
        OTHER = "other", _("Autre")

    class FollowUp(models.TextChoices):
        PROSPECT = "prospect", _("Prospect")
        NEGOTIATING = "negotiating", _("En négociation")
        SIGNING = "signing", _("En signature")
        ACTIVE = "active", _("Client actif")
        DROPPED = "dropped", _("Sans suite")

    name = models.CharField(_("nom"), max_length=255)
    siret = models.CharField(_("SIRET"), max_length=14, blank=True)
    licence_number = models.CharField(_("n° de licence"), max_length=50, blank=True)
    representative_name = models.CharField(_("représentant légal"), max_length=255, blank=True)
    representative_role = models.CharField(_("qualité du représentant"), max_length=255, blank=True)
    billing_address = models.TextField(_("adresse de facturation"), blank=True)
    email = models.EmailField(_("e-mail"), blank=True)
    phone = models.CharField(_("téléphone"), max_length=30, blank=True)
    kind = models.CharField(_("type d'organisateur"), max_length=20, choices=Kind, blank=True)
    # Prospecting: set by hand, it is only a visual landmark (F-15).
    follow_up = models.CharField(_("suivi"), max_length=20, choices=FollowUp, blank=True)
    event_type = models.CharField(_("type d'évènement"), max_length=100, blank=True)
    aesthetic = models.CharField(_("esthétique"), max_length=100, blank=True)
    notes = models.TextField(_("notes"), blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("addressbook:promoter-detail", args=[self.pk])


class Venue(AddressMixin, TenantOwnedModel):
    """The physical place (Lieu / Salle) where the gig happens."""

    name = models.CharField(_("nom"), max_length=255)
    address = models.TextField(_("adresse"), blank=True)
    capacity = models.PositiveIntegerField(_("jauge (places)"), null=True, blank=True)
    phone = models.CharField(_("téléphone"), max_length=30, blank=True)
    access_info = models.TextField(_("infos d'accès (parking, chargement…)"), blank=True)
    notes = models.TextField(_("notes"), blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("addressbook:venue-detail", args=[self.pk])


class Contact(TenantOwnedModel):
    """A person (Contact) attached to either a Promoter or a Venue, never both."""

    promoter = models.ForeignKey(
        Promoter, on_delete=models.CASCADE, related_name="contacts", null=True, blank=True
    )
    venue = models.ForeignKey(
        Venue, on_delete=models.CASCADE, related_name="contacts", null=True, blank=True
    )
    name = models.CharField(_("nom"), max_length=255)
    role = models.CharField(_("fonction"), max_length=255, blank=True)
    email = models.EmailField(_("e-mail"), blank=True)
    phone = models.CharField(_("téléphone"), max_length=30, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(promoter__isnull=False, venue__isnull=True)
                    | models.Q(promoter__isnull=True, venue__isnull=False)
                ),
                name="contact_belongs_to_promoter_or_venue",
            ),
        ]

    def clean(self):
        super().clean()
        parent = self.promoter or self.venue
        if parent and parent.tenant_id != self.tenant_id:
            raise ValidationError(
                _("Le contact doit appartenir à la même structure que son organisateur ou lieu.")
            )

    def __str__(self):
        return self.name


class PromoterInvitation(TenantOwnedModel):
    """A temporary secret link that lets an organiser fill in their own details (F-16).

    The answers wait in `response` until the user reviews them and applies them to the
    Promoter; `response` is emptied afterwards, so the data is not kept twice.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", _("Lien actif")
        ANSWERED = "answered", _("Réponse à vérifier")
        REVIEWED = "reviewed", _("Réponse traitée")
        EXPIRED = "expired", _("Lien expiré")
        REVOKED = "revoked", _("Lien annulé")

    promoter = models.ForeignKey(Promoter, on_delete=models.CASCADE, related_name="invitations")
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
        return f"Formulaire — {self.promoter}"

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
