from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import AddressMixin, TenantOwnedModel


class Promoter(AddressMixin, TenantOwnedModel):
    """The client (Organisateur) who buys the show and gets invoiced."""

    street_field = "billing_address"

    # Qualification criteria (F-15): each is a list of these values, several can apply.
    class Kind(models.TextChoices):
        VENUE = "venue", _("Salle")
        FESTIVAL = "festival", _("Festival")
        MUNICIPALITY = "municipality", _("Collectivité")
        ASSOCIATION = "association", _("Association")
        PRODUCER = "producer", _("Producteur")
        AGENCY = "agency", _("Agence")
        COMPANY = "company", _("Entreprise")
        CULTURAL_INSTITUTION = "cultural_institution", _("Établissement culturel")
        OTHER = "other", _("Autre")

    class EventType(models.TextChoices):
        CONCERT = "concert", _("Concert")
        FESTIVAL = "festival", _("Festival")
        CULTURAL_SEASON = "cultural_season", _("Saison culturelle")
        MUNICIPAL_EVENT = "municipal_event", _("Évènement municipal")
        PRIVATE_EVENT = "private_event", _("Évènement privé")
        TRADE_SHOW = "trade_show", _("Salon")
        CULTURAL_ACTION = "cultural_action", _("Action culturelle")
        OTHER = "other", _("Autre")

    class Aesthetic(models.TextChoices):
        CHANSON = "chanson", _("Chanson")
        CONTEMPORARY_MUSIC = "contemporary_music", _("Musiques actuelles")
        JAZZ = "jazz", _("Jazz")
        CLASSICAL = "classical", _("Classique")
        THEATRE = "theatre", _("Théâtre")
        DANCE = "dance", _("Danse")
        CIRCUS = "circus", _("Cirque")
        STREET_ARTS = "street_arts", _("Arts de la rue")
        MULTIDISCIPLINARY = "multidisciplinary", _("Pluridisciplinaire")
        OTHER = "other", _("Autre")

    class Format(models.TextChoices):
        SMALL_CAPACITY = "small_capacity", _("Petite jauge")
        OPEN_AIR = "open_air", _("Plein air")
        TOURING = "touring", _("Itinérant")
        SEATED = "seated", _("Assis")
        STANDING = "standing", _("Debout")
        OTHER = "other", _("Autre")

    class Period(models.TextChoices):
        SEASON = "season", _("Saison")
        FESTIVAL_PERIOD = "festival_period", _("Période de festival")
        ONE_OFF = "one_off", _("Dates ponctuelles")
        KNOWN_PROGRAMMING = "known_programming", _("Période de programmation connue")
        OTHER = "other", _("Autre")

    class EventRole(models.TextChoices):
        ORGANISER = "organiser", _("Organisateur")
        PROGRAMMER = "programmer", _("Programmateur")
        PRODUCER = "producer", _("Producteur")
        CO_PRODUCER = "co_producer", _("Coproducteur")
        DISTRIBUTOR = "distributor", _("Diffuseur")
        SERVICE_PROVIDER = "service_provider", _("Prestataire")
        OTHER = "other", _("Autre")

    # field name -> (choices, title): the order is the order of the form and of the pages.
    QUALIFICATION = {
        "kinds": (Kind, _("Type d'organisateur")),
        "event_types": (EventType, _("Type d'évènement")),
        "aesthetics": (Aesthetic, _("Esthétique / discipline")),
        "formats": (Format, _("Format / jauge")),
        "usual_periods": (Period, _("Période habituelle")),
        "event_roles": (EventRole, _("Rôle dans l'évènement")),
    }

    class FollowUp(models.TextChoices):
        PROSPECT = "prospect", _("Prospect")
        NEGOTIATING = "negotiating", _("En négociation")
        SIGNING = "signing", _("En signature")
        ACTIVE = "active", _("Client actif")
        DROPPED = "dropped", _("Sans suite")

    name = models.CharField(_("nom"), max_length=255)
    siret = models.CharField(_("SIRET"), max_length=14, blank=True)
    code_ape = models.CharField(_("Code APE"), max_length=5, blank=True)
    vat_number = models.CharField(_("n° de TVA intracommunautaire"), max_length=20, blank=True)
    licence_number = models.CharField(_("n° de licence"), max_length=50, blank=True)
    representative_name = models.CharField(_("représentant légal"), max_length=255, blank=True)
    representative_role = models.CharField(_("qualité du représentant"), max_length=255, blank=True)
    billing_address = models.TextField(_("adresse de facturation"), blank=True)
    email = models.EmailField(_("e-mail"), blank=True)
    phone = models.CharField(_("téléphone"), max_length=30, blank=True)
    # Prospecting: set by hand, it is only a visual landmark (F-15).
    follow_up = models.CharField(_("suivi"), max_length=20, choices=FollowUp, blank=True)
    kinds = models.JSONField(_("type d'organisateur"), default=list, blank=True)
    event_types = models.JSONField(_("type d'évènement"), default=list, blank=True)
    aesthetics = models.JSONField(_("esthétique / discipline"), default=list, blank=True)
    formats = models.JSONField(_("format / jauge"), default=list, blank=True)
    usual_periods = models.JSONField(_("période habituelle"), default=list, blank=True)
    event_roles = models.JSONField(_("rôle dans l'évènement"), default=list, blank=True)
    indicative_capacity = models.PositiveIntegerField(_("jauge indicative"), null=True, blank=True)
    qualification_other = models.CharField(_("autres précisions"), max_length=255, blank=True)
    notes = models.TextField(_("notes"), blank=True)

    def __str__(self):
        return self.name

    def labels_for(self, field):
        choices = self.QUALIFICATION[field][0]
        return [str(choices(v).label) for v in getattr(self, field) if v in choices.values]

    @property
    def kind_labels(self):
        return self.labels_for("kinds")

    @property
    def event_type_labels(self):
        return self.labels_for("event_types")

    @property
    def aesthetic_labels(self):
        return self.labels_for("aesthetics")

    @property
    def qualification_tags(self):
        """(title, labels) of every criterion that has a value, in display order."""
        tags = []
        for field, (_choices, title) in self.QUALIFICATION.items():
            labels = self.labels_for(field)
            if labels:
                tags.append((title, labels))
        return tags

    def get_absolute_url(self):
        return reverse("addressbook:promoter-detail", args=[self.pk])


class Venue(AddressMixin, TenantOwnedModel):
    """The physical place (Lieu / Salle) where the gig happens."""

    name = models.CharField(_("nom"), max_length=255)
    address = models.TextField(_("adresse"), blank=True)
    capacity = models.PositiveIntegerField(_("jauge (places)"), null=True, blank=True)
    configuration = models.CharField(
        _("configuration"),
        max_length=255,
        blank=True,
        help_text=_("Par exemple : assis, debout, plein air."),
    )
    phone = models.CharField(_("téléphone"), max_length=30, blank=True)
    access_info = models.TextField(_("infos d'accès (parking, chargement…)"), blank=True)
    notes = models.TextField(_("notes"), blank=True)

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


class PromoterInvitation(TenantOwnedModel):
    """A temporary secret link that lets an organiser fill in their own details (F-16).

    The answers wait in `response` until the user reviews them and applies them to the
    Promoter; `response` is emptied afterwards, so the data is not kept twice.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", _("Lien actif")
        ANSWERED = "answered", _("Réponse à vérifier")
        REVIEWED = "reviewed", _("Réponse traitée")
        EXPIRED = "expired", _("Lien expiré")
        REVOKED = "revoked", _("Lien annulé")

    promoter = models.ForeignKey(Promoter, on_delete=models.CASCADE, related_name="invitations")
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Formulaire — {self.promoter}"

    @property
    def status(self):
        if self.reviewed_at:
            return self.Status.REVIEWED
        if self.completed_at:
            return self.Status.ANSWERED
        if self.revoked_at:
            return self.Status.REVOKED
        if self.expires_at <= timezone.now():
            return self.Status.EXPIRED
        return self.Status.ACTIVE
