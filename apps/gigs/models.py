from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel


class Gig(TenantOwnedModel):
    """A performance (Date): the central object linking Show, Promoter, Venue and date."""

    class Status(models.TextChoices):
        OPTION = "option", _("Option")
        CONFIRMED = "confirmed", _("Confirmée")
        SIGNED = "signed", _("Signée")
        CANCELLED = "cancelled", _("Annulée")

    show = models.ForeignKey("catalog.Show", on_delete=models.PROTECT, related_name="gigs")
    promoter = models.ForeignKey(
        "addressbook.Promoter", on_delete=models.PROTECT, related_name="gigs"
    )
    venue = models.ForeignKey("addressbook.Venue", on_delete=models.PROTECT, related_name="gigs")
    date = models.DateField(_("date"))
    status = models.CharField(
        _("statut"), max_length=20, choices=Status.choices, default=Status.OPTION
    )
    price = models.DecimalField(_("prix HT"), max_digits=8, decimal_places=2)
    conditions = models.TextField(_("conditions particulières"), blank=True)
    get_in_time = models.TimeField(_("heure de get in"), null=True, blank=True)
    soundcheck_time = models.TimeField(_("heure des balances"), null=True, blank=True)
    performance_time = models.TimeField(_("heure de passage"), null=True, blank=True)
    crew_headcount = models.PositiveIntegerField(
        _("nombre de participants (repas)"), null=True, blank=True
    )
    is_free = models.BooleanField(_("concert gratuit"), default=False)
    ticket_price = models.DecimalField(
        _("prix des places"), max_digits=8, decimal_places=2, default=0
    )
    invitations_count = models.PositiveIntegerField(_("nombre d'invitations"), default=0)
    signing_place = models.CharField(_("lieu de signature"), max_length=255, blank=True)

    def save(self, *args, **kwargs):
        # RG-12: a free gig always has a ticket price of 0.
        if self.is_free:
            self.ticket_price = 0
            update_fields = kwargs.get("update_fields")
            if update_fields is not None and "is_free" in update_fields:
                kwargs["update_fields"] = {*update_fields, "ticket_price"}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.show} — {self.date}"
