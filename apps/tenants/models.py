import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import AddressMixin, TenantOwnedModel

from .validators import (
    format_social_security_number,
    validate_bic,
    validate_iban,
    validate_social_security_number,
)


def logo_upload_to(instance, filename):
    # An unguessable folder per file, and the uploader's own file name is not kept.
    extension = "png" if filename.lower().endswith("png") else "jpg"
    return f"logos/{uuid.uuid4().hex}/logo.{extension}"


class Tenant(AddressMixin, models.Model):
    """The tenant: the artist, association or company using the app."""

    class VatRegime(models.TextChoices):
        TAXABLE = "taxable", _("Assujetti")
        FRANCHISE = "franchise", _("Franchise en base")
        NOT_TAXABLE = "not_taxable", _("Non assujetti")

    name = models.CharField(_("nom"), max_length=255)
    legal_form = models.CharField(_("forme juridique"), max_length=255, blank=True)
    plan = models.CharField(_("offre"), max_length=50, default="free")
    address = models.TextField(_("adresse"), blank=True)
    siret = models.CharField(_("SIRET"), max_length=14, blank=True)
    code_ape = models.CharField(_("Code APE"), max_length=5, blank=True)
    vat_regime = models.CharField(
        _("régime de TVA"),
        max_length=20,
        choices=VatRegime.choices,
        default=VatRegime.FRANCHISE,
    )
    vat_rate = models.DecimalField(
        _("taux de TVA (%)"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_(
            "Le spectacle vivant a souvent un taux réduit, différent du taux standard : "
            "vérifiez le taux qui s'applique à vos dates. Laissez vide pour l'indiquer "
            "à la main sur le contrat."
        ),
    )
    logo = models.FileField(_("logo"), upload_to=logo_upload_to, blank=True)
    vat_number = models.CharField(
        _("n° de TVA intracommunautaire"),
        max_length=20,
        blank=True,
        help_text=_("Seulement si vous êtes assujetti à la TVA. Exemple : FR12345678901."),
    )
    iban = models.CharField(
        _("IBAN"),
        max_length=34,
        blank=True,
        validators=[validate_iban],
        help_text=_("Affiché sur vos factures pour être payé par virement."),
    )
    bic = models.CharField(
        _("BIC"),
        max_length=11,
        blank=True,
        validators=[validate_bic],
        help_text=_("Affiché avec l'IBAN sur les contrats qui le demandent."),
    )
    phone = models.CharField(_("téléphone"), max_length=30, blank=True)
    email = models.EmailField(_("e-mail"), blank=True)
    licence_number = models.CharField(_("n° de licence"), max_length=50, blank=True)
    licence_exempt = models.BooleanField(
        _("moins de 7 représentations par an (pas de licence)"), default=False
    )
    share_capital = models.CharField(_("capital social"), max_length=50, blank=True)
    rcs = models.CharField(_("immatriculation RCS"), max_length=100, blank=True)
    vat_on_debits = models.BooleanField(_("TVA payée d'après les débits"), default=False)
    quote_validity_days = models.PositiveSmallIntegerField(
        _("durée de validité d'un devis (jours)"),
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
    )
    payment_term_days = models.PositiveSmallIntegerField(
        _("délai de paiement d'une facture (jours)"),
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(60)],
    )
    mediator = models.CharField(
        _("médiateur de la consommation"),
        max_length=255,
        blank=True,
        help_text=_(
            "Nom et site du médiateur. Obligatoire si vous facturez des particuliers : "
            "il est imprimé sur leurs factures."
        ),
    )
    # The documents print `representative_name`. The form asks for the first and the last name
    # apart and writes "First Last" back into it, so no document changes (STR-05).
    representative_name = models.CharField(_("représentant légal"), max_length=255, blank=True)
    representative_first_name = models.CharField(
        _("prénom du représentant"), max_length=100, blank=True
    )
    representative_last_name = models.CharField(
        _("nom du représentant"), max_length=150, blank=True
    )
    representative_role = models.CharField(_("qualité du représentant"), max_length=255, blank=True)
    jurisdiction_city = models.CharField(
        _("ville du tribunal compétent"), max_length=255, blank=True
    )

    # Set when the owner asks to delete the structure; the data is purged after a grace period.
    deletion_requested_at = models.DateTimeField(
        _("suppression demandée le"), null=True, blank=True
    )

    def __str__(self):
        return self.name


class Person(AddressMixin, TenantOwnedModel):
    """A member of the structure's team (artist, musician, technician...). Tracking only:
    nothing here is used to compute pay or social contributions (F-06).

    The address, the GUSO number, the birth date and the social security number are private:
    only the owner sees them (they are there for the person in charge of the accounts and
    the paperwork), and they are never copied to a roadmap.
    """

    first_name = models.CharField(_("prénom"), max_length=100)
    last_name = models.CharField(_("nom"), max_length=100)
    role = models.CharField(_("fonction"), max_length=100, blank=True)
    status = models.CharField(_("statut"), max_length=100, blank=True)
    phone = models.CharField(_("téléphone"), max_length=30, blank=True)
    email = models.EmailField(_("e-mail"), blank=True)
    address = models.TextField(_("adresse"), blank=True)
    guso_number = models.CharField(_("n° GUSO"), max_length=50, blank=True)
    birth_date = models.DateField(_("date de naissance"), null=True, blank=True)
    social_security_number = models.CharField(
        _("n° de sécurité sociale"),
        max_length=15,
        blank=True,
        validators=[validate_social_security_number],
    )
    is_artist = models.BooleanField(_("artiste"), default=False)
    is_technician = models.BooleanField(_("technicien"), default=False)
    average_fee = models.DecimalField(
        _("cachet moyen (€)"), max_digits=10, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(_("notes"), blank=True)
    # Secret of the personal space (a link, no account): empty = no access. Whoever has it sees
    # this person's dates, so it is never in an export, a log or a list (see services).
    access_token = models.CharField(max_length=64, blank=True, editable=False)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = _("personne")
        verbose_name_plural = _("personnes")
        constraints = [
            models.UniqueConstraint(
                fields=["access_token"],
                condition=~models.Q(access_token=""),
                name="unique_person_access_token",
            ),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def formatted_social_security_number(self):
        return format_social_security_number(self.social_security_number)

    def age(self, today=None):
        """Full years at `today`; None when there is no birth date."""
        if self.birth_date is None:
            return None
        today = today or timezone.localdate()
        before_birthday = (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        return today.year - self.birth_date.year - before_birthday

    def get_absolute_url(self):
        return reverse("tenants:person-detail", args=[self.pk])


class MessageTemplate(TenantOwnedModel):
    """The subject and text a structure wrote for one of its e-mails, in place of the default.

    The `[Variables]` allowed are listed in `message_templates`; no row means the default text.
    """

    class Kind(models.TextChoices):
        FORM = "form", _("Formulaire de l'organisateur")
        CONTRACT = "contract", _("Envoi du contrat")
        REMINDER = "reminder", _("Relance d'un contrat non signé")
        INFO = "info", _("Formulaire d'un contact ou d'un membre")

    kind = models.CharField(_("message"), max_length=20, choices=Kind.choices)
    subject = models.CharField(_("objet"), max_length=200)
    body = models.TextField(_("texte"), max_length=2000)

    class Meta:
        verbose_name = _("modèle de message")
        verbose_name_plural = _("modèles de messages")
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "kind"], name="one_message_template_per_kind"
            ),
        ]

    def __str__(self):
        return self.get_kind_display()
