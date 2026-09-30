from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel


class Promoter(TenantOwnedModel):
    """The client (Organisateur) who buys the show and gets invoiced."""

    name = models.CharField(_("nom"), max_length=255)
    siret = models.CharField(_("SIRET"), max_length=14, blank=True)
    licence_number = models.CharField(_("n° de licence"), max_length=50, blank=True)
    representative_name = models.CharField(_("représentant légal"), max_length=255, blank=True)
    representative_role = models.CharField(_("qualité du représentant"), max_length=255, blank=True)
    billing_address = models.TextField(_("adresse de facturation"), blank=True)
    email = models.EmailField(_("e-mail"), blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("addressbook:promoter-detail", args=[self.pk])


class Venue(TenantOwnedModel):
    """The physical place (Lieu / Salle) where the gig happens."""

    name = models.CharField(_("nom"), max_length=255)
    address = models.TextField(_("adresse"), blank=True)
    capacity = models.PositiveIntegerField(_("jauge (places)"), null=True, blank=True)

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
