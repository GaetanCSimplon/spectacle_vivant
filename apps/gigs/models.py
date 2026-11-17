from collections import namedtuple
from decimal import Decimal
from functools import cached_property

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel

from . import payment_terms
from .hospitality import CoveredBy
from .payment_terms import BalanceTerm, DepositTerm

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

    class Setting(models.TextChoices):
        INDOOR = "indoor", _("Intérieur")
        OUTDOOR = "outdoor", _("Plein air")

    class OutdoorFallback(models.TextChoices):
        PROVIDED = "provided", _("Un repli est prévu")
        NONE_ACCEPTED = "none_accepted", _("Pas de repli, accepté par les deux parties")

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
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Part du prix proposée en facture d'acompte."),
    )
    # None = not answered yet (the checks of the contract ask for an answer).
    deposit_required = models.BooleanField(_("acompte demandé"), null=True, blank=True)
    conditions = models.TextField(_("conditions particulières"), blank=True)
    get_in_time = models.TimeField(_("heure de get in"), null=True, blank=True)
    soundcheck_time = models.TimeField(_("heure des balances"), null=True, blank=True)
    performance_time = models.TimeField(_("heure de passage"), null=True, blank=True)
    crew_headcount = models.PositiveIntegerField(
        _("personnes en tournée (tous profils)"), null=True, blank=True
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
    # The terms are rules; `deposit_due_on` and `balance_due_on` hold the date a rule gives (empty
    # until the contract is signed for the rules that start from the signature), or the date typed
    # for "Date précise" (CTR-05).
    deposit_term = models.CharField(
        _("échéance de l'acompte"),
        max_length=30,
        choices=DepositTerm,
        default=DepositTerm.SPECIFIC,
    )
    deposit_term_days = models.PositiveSmallIntegerField(
        _("jours avant la prestation"), null=True, blank=True
    )
    balance_term = models.CharField(
        _("échéance du solde"), max_length=30, choices=BalanceTerm, default=BalanceTerm.SPECIFIC
    )
    payment_method = models.CharField(
        _("mode de paiement"), max_length=20, choices=PaymentMethod, blank=True
    )
    signature_deadline_days = models.PositiveIntegerField(
        _("délai de retour du contrat signé (jours)"), null=True, blank=True
    )
    copies_count = models.PositiveIntegerField(
        _("nombre d'exemplaires du contrat"), default=2, validators=[MinValueValidator(1)]
    )
    # What the contract prints, composed from the answers below (see hospitality.py).
    meals = models.CharField(_("repas pris en charge"), max_length=255, blank=True)
    lodging = models.CharField(_("hébergement pris en charge"), max_length=255, blank=True)
    meals_covered_by = models.CharField(
        _("repas pris en charge par"), max_length=20, choices=CoveredBy, blank=True
    )
    meals_people = models.PositiveSmallIntegerField(_("personnes nourries"), null=True, blank=True)
    meals_count = models.PositiveSmallIntegerField(_("nombre de repas"), null=True, blank=True)
    meals_notes = models.CharField(
        _("précisions sur les repas"),
        max_length=150,
        blank=True,
        help_text=_("Par exemple : régime alimentaire, répartition. Imprimé dans le contrat."),
    )
    lodging_covered_by = models.CharField(
        _("hébergement pris en charge par"), max_length=20, choices=CoveredBy, blank=True
    )
    lodging_people = models.PositiveSmallIntegerField(
        _("personnes hébergées"), null=True, blank=True
    )
    lodging_nights = models.PositiveSmallIntegerField(_("nombre de nuits"), null=True, blank=True)
    lodging_notes = models.CharField(
        _("précisions sur l'hébergement"),
        max_length=150,
        blank=True,
        help_text=_("Par exemple : chambres, répartition. Imprimé dans le contrat."),
    )
    local_transport = models.CharField(_("transports locaux"), max_length=255, blank=True)
    other_hospitality = models.CharField(
        _("autres éléments d'accueil"),
        max_length=255,
        blank=True,
        help_text=_("Par exemple : parking, catering, petits-déjeuners, backline."),
    )

    setting = models.CharField(
        _("lieu de la représentation"), max_length=10, choices=Setting, blank=True
    )
    outdoor_fallback = models.CharField(
        _("repli en cas d'intempéries"), max_length=20, choices=OutdoorFallback, blank=True
    )
    outdoor_fallback_details = models.TextField(_("modalités du repli"), blank=True)
    outdoor_procedure = models.TextField(
        _("décision de maintien, de report ou d'arrêt"), blank=True
    )
    outdoor_referents = models.TextField(_("référents des deux parties"), blank=True)
    outdoor_financial_terms = models.TextField(
        _("conditions financières en cas d'intempéries"),
        blank=True,
        help_text=_("Laissez vide pour appliquer les règles d'annulation et de force majeure."),
    )
    transport_covered_by = models.CharField(
        _("transport pris en charge par"), max_length=20, choices=CoveredBy, blank=True
    )
    transport_notes = models.CharField(_("précisions sur le transport"), max_length=150, blank=True)
    extra_fees_description = models.TextField(_("frais supplémentaires"), blank=True)
    extra_fees_amount = models.DecimalField(
        _("montant des frais supplémentaires"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    extra_fees_accepted = models.BooleanField(_("frais acceptés par l'organisateur"), default=False)
    price_includes = models.TextField(_("le prix comprend"), blank=True)
    billing_notes = models.TextField(
        _("modalités de facturation"),
        blank=True,
        help_text=_("Par exemple : n° de bon de commande, service payeur."),
    )
    onsite_contact_name = models.CharField(_("contact sur place"), max_length=255, blank=True)
    onsite_contact_phone = models.CharField(
        _("téléphone du contact sur place"), max_length=50, blank=True
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

    @property
    def display_title(self):
        """What names the date on a card or in a breadcrumb: "Lieu, Ville, Spectacle" (DAT-02)."""
        parts = (self.venue.name, self.venue.city, self.show.title)
        return ", ".join(part for part in parts if part)

    @property
    def deposit_due_phrase(self):
        """How the contract states the deposit date: a rule, a date or both; "" when not set."""
        return payment_terms.deposit_phrase(
            self.deposit_term, self.deposit_term_days, self.deposit_due_on
        )

    @property
    def balance_due_phrase(self):
        return payment_terms.balance_phrase(self.balance_term, self.balance_due_on)

    @property
    def deposit_due_display(self):
        """The deposit date for a screen, or the rule while it has no date ("" if nothing)."""
        return payment_terms.deposit_short(
            self.deposit_term, self.deposit_term_days, self.deposit_due_on
        )

    @property
    def balance_due_display(self):
        return payment_terms.balance_short(self.balance_term, self.balance_due_on)

    @property
    def has_payment_terms(self):
        """Some term is chosen: a date, or a rule whose date is still to come."""
        return bool(
            self.deposit_due_on
            or self.balance_due_on
            or self.deposit_term != DepositTerm.SPECIFIC
            or self.balance_term != BalanceTerm.SPECIFIC
        )

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


class GigChecklist(TenantOwnedModel):
    """Which steps of the contracting of a gig are done (Checklist contractualisation).

    `items` only holds the boxes that were touched, as {key: bool}; an absent key means not
    done. The list of boxes lives in `checklist.py`. The author is kept for the audit.
    """

    gig = models.OneToOneField(Gig, on_delete=models.CASCADE, related_name="checklist")
    items = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    def __str__(self):
        return f"Checklist — {self.gig}"


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
    # Social management (F-93): what this person is paid for this date, as information for
    # whoever does the payroll. Private (owner only), never copied to a roadmap, never computed
    # from or against the expenses: nothing here is a payment.
    cachet_count = models.PositiveSmallIntegerField(_("nombre de cachets"), null=True, blank=True)
    cachet_amount = models.DecimalField(
        _("montant du cachet (brut)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

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
