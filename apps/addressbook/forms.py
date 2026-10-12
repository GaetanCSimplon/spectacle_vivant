from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import AddressModelForm

from . import services
from .models import Contact, Promoter, Venue


class PromoterForm(AddressModelForm):
    class Meta:
        model = Promoter
        fields = [
            "name",
            "kind",
            "follow_up",
            "event_type",
            "aesthetic",
            "email",
            "phone",
            "siret",
            "licence_number",
            "representative_name",
            "representative_role",
            "billing_address",
            "postal_code",
            "city",
            "department",
            "notes",
        ]
        widgets = {
            "billing_address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "event_type": forms.TextInput(attrs={"list": "event-type-options"}),
            "aesthetic": forms.TextInput(attrs={"list": "aesthetic-options"}),
        }
        help_texts = {
            "follow_up": _("Un repère pour vous : à vous de le changer au fil des échanges."),
            "event_type": _("Choisissez une proposition ou écrivez la vôtre."),
            "aesthetic": _("Choisissez une proposition ou écrivez la vôtre."),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_type_options = services.suggestions(
            tenant, "event_type", services.EVENT_TYPE_SUGGESTIONS
        )
        self.aesthetic_options = services.suggestions(
            tenant, "aesthetic", services.AESTHETIC_SUGGESTIONS
        )

    def clean_event_type(self):
        return " ".join(self.cleaned_data["event_type"].split())

    def clean_aesthetic(self):
        return " ".join(self.cleaned_data["aesthetic"].split())


class PromoterFilterForm(forms.Form):
    """Filters of the organisers list. Every field is optional; an invalid value is ignored."""

    follow_up = forms.ChoiceField(
        label=_("Suivi"),
        required=False,
        choices=[("", _("Tous les suivis")), *Promoter.FollowUp.choices],
    )
    event_type = forms.ChoiceField(label=_("Type d'évènement"), required=False)
    aesthetic = forms.ChoiceField(label=_("Esthétique"), required=False)

    def __init__(self, *args, tenant, **kwargs):
        super().__init__(*args, **kwargs)
        # Only values this tenant has typed can be chosen: anything else is ignored.
        for name, empty in (
            ("event_type", _("Tous les types")),
            ("aesthetic", _("Toutes les esthétiques")),
        ):
            values = services.used_values(tenant, name)
            self.fields[name].choices = [("", empty), *[(v, v) for v in values]]

    def apply(self, queryset):
        self.is_valid()  # fills cleaned_data with the valid fields, drops the invalid ones
        data = self.cleaned_data
        if data.get("follow_up"):
            queryset = queryset.filter(follow_up=data["follow_up"])
        if data.get("event_type"):
            queryset = queryset.filter(event_type__iexact=data["event_type"])
        if data.get("aesthetic"):
            queryset = queryset.filter(aesthetic__iexact=data["aesthetic"])
        return queryset

    @property
    def is_active(self):
        return any(self.cleaned_data.get(name) for name in self.fields)


class VenueForm(AddressModelForm):
    class Meta:
        model = Venue
        fields = [
            "name",
            "address",
            "postal_code",
            "city",
            "department",
            "capacity",
            "phone",
            "access_info",
            "notes",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "access_info": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class ContactForm(forms.ModelForm):
    """The parent (Promoter or Venue) is set by the view, never chosen in the form."""

    class Meta:
        model = Contact
        fields = ["name", "role", "email", "phone"]
        # Suggestions only (Accueil, Technique, Comm'...): the role stays free text.
        widgets = {"role": forms.TextInput(attrs={"list": "contact-roles"})}


class NewContactForm(ContactForm):
    """A contact created from the home page: the user picks the organiser or venue here.

    Only this tenant's organisers and venues are offered, so a choice that is not in the list
    (another tenant's id, a made-up value) is an invalid choice, never a hidden link.
    """

    parent = forms.ChoiceField(label=_("Rattaché à"))
    field_order = ["parent", "name", "role", "email", "phone"]

    def __init__(self, *args, tenant, **kwargs):
        super().__init__(*args, **kwargs)
        self.promoters = {
            str(p.pk): p for p in Promoter.objects.filter(tenant=tenant).order_by("name")
        }
        self.venues = {str(v.pk): v for v in Venue.objects.filter(tenant=tenant).order_by("name")}
        groups = []
        if self.promoters:
            groups.append(
                (
                    _("Organisateurs"),
                    [(f"promoter:{pk}", p.name) for pk, p in self.promoters.items()],
                )
            )
        if self.venues:
            groups.append((_("Lieux"), [(f"venue:{pk}", v.name) for pk, v in self.venues.items()]))
        self.fields["parent"].choices = [("", _("Choisir…")), *groups]
        self.has_parents = bool(groups)

    def clean(self):
        cleaned = super().clean()
        kind, _sep, pk = cleaned.get("parent", "").partition(":")
        if kind == "promoter":
            self.instance.promoter, self.instance.venue = self.promoters.get(pk), None
        elif kind == "venue":
            self.instance.venue, self.instance.promoter = self.venues.get(pk), None
        return cleaned


class PromoterPublicForm(AddressModelForm):
    """What an organiser fills in from the link they received (F-16).

    It is built on a blank, unsaved Promoter and never saved: the answer is only stored until
    the user has reviewed it. Nothing of the real card is shown or touched here. Every field
    is optional, but at least one must be filled in.
    """

    # Declared here so that "213 400 000 000 19" is accepted and cleaned to 14 digits.
    siret = forms.CharField(label=_("SIRET"), required=False, max_length=20)
    contact_name = forms.CharField(label=_("Nom"), required=False, max_length=255)
    contact_role = forms.CharField(label=_("Fonction"), required=False, max_length=255)
    contact_email = forms.EmailField(label=_("E-mail"), required=False)
    contact_phone = forms.CharField(label=_("Téléphone"), required=False, max_length=30)

    class Meta:
        model = Promoter
        fields = [key for key, _label in services.PROMOTER_FIELDS]
        widgets = {"billing_address": forms.Textarea(attrs={"rows": 2})}
        labels = {
            "billing_address": _("Adresse"),
            "representative_name": _("Nom du représentant légal"),
            "representative_role": _("Qualité du représentant"),
            "licence_number": _("N° de licence d'entrepreneur de spectacles"),
        }
        help_texts = {
            "representative_name": _("La personne qui signe le contrat (maire, président…)."),
            "licence_number": _("Si votre structure en a une."),
        }

    def clean_siret(self):
        siret = "".join(self.cleaned_data["siret"].split())
        if siret and not (siret.isdigit() and len(siret) == 14):
            raise forms.ValidationError(_("Un SIRET comporte 14 chiffres."))
        return siret

    def clean(self):
        cleaned = super().clean()
        contact = [cleaned.get(f"contact_{key}") for key in services.CONTACT_KEYS]
        if any(contact) and not cleaned.get("contact_name"):
            self.add_error("contact_name", _("Indiquez le nom de ce contact."))
        answered = [cleaned.get(key) for key, _label in services.PROMOTER_FIELDS] + contact
        if not self.errors and not any(answered):
            raise forms.ValidationError(_("Merci de remplir au moins un champ."))
        return cleaned
