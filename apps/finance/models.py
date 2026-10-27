import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel

MIN_AMOUNT = Decimal("0.01")


def receipt_upload_to(instance, filename):
    # An unguessable folder per file, like contracts and invoices.
    return f"expenses/{uuid.uuid4().hex}/{filename}"


class Payment(TenantOwnedModel):
    """Money received for an invoice (Paiement)."""

    class Method(models.TextChoices):
        TRANSFER = "transfer", _("Virement")
        CHEQUE = "cheque", _("Chèque")
        CASH = "cash", _("Espèces")
        CARD = "card", _("Carte")
        OTHER = "other", _("Autre")

    invoice = models.ForeignKey(
        "documents.Invoice", on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(
        _("montant"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(MIN_AMOUNT)],
    )
    date = models.DateField(_("date de réception"))
    method = models.CharField(_("mode"), max_length=20, choices=Method.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="payment_amount_positive"
            ),
        ]

    def __str__(self):
        return f"{self.amount} € — {self.invoice}"


class Expense(TenantOwnedModel):
    """Money spent for a gig (Dépense)."""

    class Category(models.TextChoices):
        FEES = "fees", _("Cachets")
        TRANSPORT = "transport", _("Transport")
        LODGING = "lodging", _("Hébergement")
        TECHNICAL = "technical", _("Technique")
        COMMUNICATION = "communication", _("Communication")
        OTHER = "other", _("Autres")

    gig = models.ForeignKey("gigs.Gig", on_delete=models.PROTECT, related_name="expenses")
    category = models.CharField(_("catégorie"), max_length=20, choices=Category.choices)
    label = models.CharField(_("libellé"), max_length=255)
    amount = models.DecimalField(
        _("montant"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(MIN_AMOUNT)],
    )
    date = models.DateField(_("date"))
    # Empty: the structure paid. Set: a member of the team advanced the money, and the
    # structure owes it back until `reimbursed_on` is filled (tracking only, no payment made).
    person = models.ForeignKey(
        "tenants.Person",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expenses",
        verbose_name=_("dépense faite par"),
    )
    reimbursed_on = models.DateField(_("remboursée le"), null=True, blank=True)
    receipt_file = models.FileField(_("justificatif"), upload_to=receipt_upload_to, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="expense_amount_positive"
            ),
        ]

    def __str__(self):
        return f"{self.label} — {self.amount} €"

    @property
    def to_reimburse(self):
        """A member advanced it and has not been paid back yet."""
        return self.person_id is not None and self.reimbursed_on is None

    def save(self, *args, **kwargs):
        if self.person_id is None:  # nobody to pay back
            self.reimbursed_on = None
        super().save(*args, **kwargs)


def claim_receipt_upload_to(instance, filename):
    # An unguessable folder per file, like the receipts of expenses.
    return f"claims/{uuid.uuid4().hex}/{filename}"


class ExpenseClaim(TenantOwnedModel):
    """An expense a team member declares from their personal space (Proposition de dépense).

    It is only a proposal: it counts nowhere until the owner accepts it, and then it becomes a
    real `Expense` made by this member (so "to reimburse"). Kept apart from `Expense` so that no
    total can include an unchecked amount.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("En attente de validation")
        ACCEPTED = "accepted", _("Validée")
        REFUSED = "refused", _("Refusée")

    person = models.ForeignKey(
        "tenants.Person", on_delete=models.CASCADE, related_name="expense_claims"
    )
    gig = models.ForeignKey("gigs.Gig", on_delete=models.CASCADE, related_name="expense_claims")
    category = models.CharField(_("catégorie"), max_length=20, choices=Expense.Category.choices)
    label = models.CharField(_("libellé"), max_length=255)
    amount = models.DecimalField(
        _("montant"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(MIN_AMOUNT)],
    )
    date = models.DateField(_("date de la dépense"))
    receipt_file = models.FileField(
        _("justificatif"), upload_to=claim_receipt_upload_to, blank=True
    )
    status = models.CharField(
        _("état"), max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    # Set when the owner accepts it: the expense it became (the receipt moves to it).
    expense = models.OneToOneField(
        Expense, on_delete=models.SET_NULL, null=True, blank=True, related_name="claim"
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="expense_claim_amount_positive"
            ),
        ]

    def __str__(self):
        return f"{self.label} — {self.amount} € ({self.person})"

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING
