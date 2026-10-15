from collections import namedtuple
from functools import cached_property

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel

# An option is highlighted as "soon" when it expires within this many days.
OPTION_WARNING_DAYS = 7

# state: "ok" | "soon" | "expired". days: days left, or days since expiry when expired.
OptionExpiry = namedtuple("OptionExpiry", ["state", "days"])


class Gig(TenantOwnedModel):
    """A performance (Date): the central object linking Show, Promoter, Venue and date."""

    class Status(models.TextChoices):
        OPTION = "option", _("Option")
        CONFIRMED = "confirmed", _("Confirmée")
        SIGNED = "signed", _("Signée")
        CANCELLED = "cancelled", _("Annulée")

    class PaymentMethod(models.TextChoices):
        TRANSFER = "transfer", _("Virement")
        CHEQUE = "cheque", _("Chèque")

    show = models.ForeignKey("catalog.Show", on_delete=models.PROTECT, related_name="gigs")
    promoter = models.ForeignKey(
        "addressbook.Promoter", on_delete=models.PROTECT, related_name="gigs"
    )
    venue = models.ForeignKey("addressbook.Venue", on_delete=models.PROTECT, related_name="gigs")
    date = models.DateField(_("date"))
    option_expires_on = models.DateField(_("option valable jusqu'au"), null=True, blank=True)
    status = models.CharField(
        _("statut"), max_length=20, choices=Status.choices, default=Status.OPTION
    )
    price = models.DecimalField(_("prix HT"), max_digits=8, decimal_places=2)
    deposit_percent = models.DecimalField(
        _("acompte (%)"),
        max_digits=5,
        decimal_places=2,
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Part du prix proposée en facture d'acompte. 30 % par défaut."),
    )
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

    # Wording of the contract (all optional: an empty value prints as dots).
    event_name = models.CharField(_("nom de l'évènement"), max_length=255, blank=True)
    performances_count = models.PositiveIntegerField(
        _("nombre de représentations"), default=1, validators=[MinValueValidator(1)]
    )
    deposit_due_on = models.DateField(_("acompte à régler le"), null=True, blank=True)
    balance_due_on = models.DateField(_("solde à régler le"), null=True, blank=True)
    payment_method = models.CharField(
        _("mode de paiement"), max_length=20, choices=PaymentMethod, blank=True
    )
    signature_deadline_days = models.PositiveIntegerField(
        _("délai de retour du contrat signé (jours)"), null=True, blank=True
    )
    copies_count = models.PositiveIntegerField(
        _("nombre d'exemplaires du contrat"), default=2, validators=[MinValueValidator(1)]
    )
    meals = models.CharField(_("repas pris en charge"), max_length=255, blank=True)
    lodging = models.CharField(_("hébergement pris en charge"), max_length=255, blank=True)
    local_transport = models.CharField(_("transports locaux"), max_length=255, blank=True)
    other_hospitality = models.CharField(
        _("autres éléments d'accueil"),
        max_length=255,
        blank=True,
        help_text=_("Par exemple : parking, catering, petits-déjeuners, backline."),
    )

    @cached_property
    def option_expiry(self):
        """How close a live option is to expiring, or None when it does not apply."""
        if self.status != self.Status.OPTION or self.option_expires_on is None:
            return None
        days_left = (self.option_expires_on - timezone.localdate()).days
        if days_left < 0:
            return OptionExpiry("expired", -days_left)
        if days_left <= OPTION_WARNING_DAYS:
            return OptionExpiry("soon", days_left)
        return OptionExpiry("ok", days_left)

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


class PriceChange(TenantOwnedModel):
    """One step in the negotiated price of a gig (Historique des prix).

    The first entry (no old price) is the price set when the date was created.
    """

    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name="price_changes")
    old_price = models.DecimalField(
        _("ancien prix HT"), max_digits=8, decimal_places=2, null=True, blank=True
    )
    new_price = models.DecimalField(_("nouveau prix HT"), max_digits=8, decimal_places=2)
    changed_at = models.DateTimeField(_("modifié le"), auto_now_add=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    note = models.CharField(_("note"), max_length=255, blank=True)

    class Meta:
        ordering = ["-changed_at", "-id"]

    def __str__(self):
        return f"{self.gig} : {self.old_price} → {self.new_price}"


class GigMember(TenantOwnedModel):
    """A person travelling for a gig (musician, technician…), shown on the roadmap."""

    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name="members")
    # Set when the person was picked from the team. The fields below are copies, so the
    # roadmap stays as it was if the team card changes or is deleted (F-06).
    person = models.ForeignKey(
        "tenants.Person",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participations",
    )
    name = models.CharField(_("nom"), max_length=255)
    role = models.CharField(_("fonction"), max_length=255, blank=True)
    phone = models.CharField(_("téléphone"), max_length=50, blank=True)
    email = models.EmailField(_("e-mail"), blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["gig", "person"],
                condition=models.Q(person__isnull=False),
                name="unique_person_per_gig",
            ),
        ]

    def __str__(self):
        return self.name
