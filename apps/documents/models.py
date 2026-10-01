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
