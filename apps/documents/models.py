import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel


def version_upload_to(instance, filename):
    # An unguessable folder per file: a stored path can never be found by trying numbers.
    return f"contracts/{uuid.uuid4().hex}/{filename}"


def signed_upload_to(instance, filename):
    # The uploader's own file name is not kept.
    return f"contracts/{uuid.uuid4().hex}/contrat-signe.pdf"


class Contract(TenantOwnedModel):
    """The cession contract (Contrat de cession) PDF linked to a Gig."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Brouillon")
        SIGNED = "signed", _("Signé")

    gig = models.OneToOneField("gigs.Gig", on_delete=models.CASCADE, related_name="contract")
    status = models.CharField(
        _("statut"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    signatory_name = models.CharField(_("nom du signataire"), max_length=255, blank=True)
    signatory_role = models.CharField(_("qualité du signataire"), max_length=255, blank=True)
    reference = models.CharField(_("référence"), max_length=20, blank=True)
    signed_at = models.DateTimeField(_("signé le"), null=True, blank=True)
    # The version frozen when the contract was signed (RG-08); it can never be deleted.
    signed_version = models.ForeignKey(
        "ContractVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    signed_pdf = models.FileField(_("PDF signé"), upload_to=signed_upload_to, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "reference"],
                condition=~models.Q(reference=""),
                name="unique_contract_reference_per_tenant",
            ),
        ]

    def __str__(self):
        return f"Contrat — {self.gig}"

    @property
    def latest_version(self):
        return self.versions.order_by("-number").first()


class ContractVersion(TenantOwnedModel):
    """One generated PDF of a Contract. Versions are never overwritten or deleted."""

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField(_("numéro de version"))
    pdf_file = models.FileField(_("fichier PDF"), upload_to=version_upload_to)
    created_at = models.DateTimeField(_("généré le"), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(fields=["contract", "number"], name="unique_contract_version"),
        ]

    def __str__(self):
        return f"{self.contract} — v{self.number}"


class ContractSequence(TenantOwnedModel):
    """Last contract number handed out for a tenant and a year (no gaps, see services)."""

    year = models.PositiveIntegerField(_("année"))
    last_number = models.PositiveIntegerField(_("dernier numéro"), default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "year"], name="unique_contract_sequence"),
        ]

    def __str__(self):
        return f"{self.tenant} — {self.year} : {self.last_number}"


def document_upload_to(instance, filename):
    # Same idea as contracts: an unguessable folder per file.
    return f"{instance._meta.model_name}s/{uuid.uuid4().hex}/{filename}"


class ImmutableDocument(Exception):
    """Raised when someone tries to change or delete an issued quote, invoice or line."""


class DocumentSequence(TenantOwnedModel):
    """Last invoice (or quote) number handed out for a tenant and a year.

    The row is locked while a number is assigned, so numbers never repeat or skip.
    """

    class Kind(models.TextChoices):
        INVOICE = "invoice", _("Facture")
        QUOTE = "quote", _("Devis")

    kind = models.CharField(_("type"), max_length=20, choices=Kind.choices)
    year = models.PositiveIntegerField(_("année"))
    last_number = models.PositiveIntegerField(_("dernier numéro"), default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "kind", "year"], name="unique_document_sequence"
            ),
        ]

    def __str__(self):
        return f"{self.tenant} — {self.kind} {self.year} : {self.last_number}"


class BillingDocument(TenantOwnedModel):
    """What a quote and an invoice share. Only a draft can change (RG-06)."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Brouillon")
        ISSUED = "issued", _("Émis")

    # Fields that may still be written once the document is no longer a draft.
    # The title is an internal label with no legal value: it stays editable (set_title).
    MUTABLE_AFTER_ISSUE = {"status", "title"}

    gig = models.ForeignKey("gigs.Gig", on_delete=models.PROTECT, related_name="+")
    number = models.CharField(_("numéro"), max_length=20, blank=True)
    title = models.CharField(_("nom"), max_length=100, blank=True)
    status = models.CharField(_("statut"), max_length=20, choices=Status.choices, default="draft")
    issue_date = models.DateField(_("date d'émission"), null=True, blank=True)
    # Copied at issue time: later edits of the tenant or the promoter never change it (RG-07).
    issuer_snapshot = models.JSONField(_("émetteur (figé)"), default=dict, blank=True)
    customer_snapshot = models.JSONField(_("client (figé)"), default=dict, blank=True)
    total_excl_tax = models.DecimalField(_("total HT"), max_digits=10, decimal_places=2, default=0)
    total_vat = models.DecimalField(_("total TVA"), max_digits=10, decimal_places=2, default=0)
    total_incl_tax = models.DecimalField(_("total TTC"), max_digits=10, decimal_places=2, default=0)
    pdf_file = models.FileField(_("fichier PDF"), upload_to=document_upload_to, blank=True)
    created_at = models.DateTimeField(_("créé le"), auto_now_add=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            stored = type(self).objects.filter(pk=self.pk).values_list("status", "pdf_file").first()
            if stored is not None and stored[0] != self.Status.DRAFT:
                # The PDF may be stored once if the document has none yet, never replaced.
                allowed = set(self.MUTABLE_AFTER_ISSUE) | ({"pdf_file"} if not stored[1] else set())
                update_fields = kwargs.get("update_fields")
                only_allowed = update_fields is not None and set(update_fields) <= allowed
                if not only_allowed or self.status == self.Status.DRAFT:
                    raise ImmutableDocument(_("Un document émis ne peut plus être modifié."))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status != self.Status.DRAFT:
            raise ImmutableDocument(_("Un document émis ne peut pas être supprimé."))
        return super().delete(*args, **kwargs)

    @property
    def is_draft(self):
        return self.status == self.Status.DRAFT


class Invoice(BillingDocument):
    """An invoice, or a credit note (avoir: a negative invoice linked to the original)."""

    class Kind(models.TextChoices):
        DEPOSIT = "deposit", _("Acompte")
        BALANCE = "balance", _("Solde")
        FULL = "full", _("Facture totale")
        CREDIT_NOTE = "credit_note", _("Avoir")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Brouillon")
        ISSUED = "issued", _("Émise")
        PAID = "paid", _("Payée")
        CANCELLED = "cancelled", _("Annulée par avoir")

    kind = models.CharField(_("type"), max_length=20, choices=Kind.choices)
    status = models.CharField(
        _("statut"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    due_date = models.DateField(_("échéance"), null=True, blank=True)
    credit_note_of = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="credit_notes",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "number"],
                condition=~models.Q(number=""),
                name="unique_invoice_number_per_tenant",
            ),
            models.CheckConstraint(
                condition=models.Q(kind="credit_note", credit_note_of__isnull=False)
                | (~models.Q(kind="credit_note") & models.Q(credit_note_of__isnull=True)),
                name="invoice_credit_note_link",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.number or '(brouillon)'}"


class Quote(BillingDocument):
    valid_until = models.DateField(_("valable jusqu'au"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "number"],
                condition=~models.Q(number=""),
                name="unique_quote_number_per_tenant",
            ),
        ]

    def __str__(self):
        return f"Devis {self.number or '(brouillon)'}"


class DocumentLine(TenantOwnedModel):
    """One line of a quote or of an invoice (exactly one of the two)."""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, null=True, blank=True, related_name="lines"
    )
    quote = models.ForeignKey(
        Quote, on_delete=models.CASCADE, null=True, blank=True, related_name="lines"
    )
    position = models.PositiveIntegerField(_("position"), default=0)
    label = models.CharField(_("désignation"), max_length=255)
    quantity = models.DecimalField(_("quantité"), max_digits=8, decimal_places=2, default=1)
    unit_price_excl_tax = models.DecimalField(
        _("prix unitaire HT"), max_digits=10, decimal_places=2
    )
    vat_rate = models.DecimalField(_("taux de TVA (%)"), max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(invoice__isnull=False, quote__isnull=True)
                | models.Q(invoice__isnull=True, quote__isnull=False),
                name="document_line_has_one_parent",
            ),
        ]

    @property
    def parent(self):
        return self.invoice or self.quote

    def _check_parent_is_draft(self):
        # A line without parent is left to the database constraint.
        if self.parent is not None and not self.parent.is_draft:
            raise ImmutableDocument(_("Les lignes d'un document émis ne peuvent plus changer."))

    def save(self, *args, **kwargs):
        self._check_parent_is_draft()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not self.parent.is_draft:
            raise ImmutableDocument(_("Les lignes d'un document émis ne peuvent plus changer."))
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.label
