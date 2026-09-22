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

    def __str__(self):
        return f"{self.show} — {self.date}"
