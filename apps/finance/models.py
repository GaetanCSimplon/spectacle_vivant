import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel

MIN_AMOUNT = "0.01"


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
