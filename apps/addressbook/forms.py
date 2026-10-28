from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import AddressModelForm, MultiSelectDropdown, SectionedFormMixin
from apps.tenants.validators import normalize_code_ape, validate_code_ape

from . import services
from .models import Contact, Promoter, Venue


class PromoterIdentifiersMixin(forms.Form):
    """The APE code and the VAT number of an organiser, typed with spaces or dots."""

    # Declared here because people type "90.01 Z": the model's 5 characters apply after cleaning.
    code_ape = forms.CharField(label=_("Code APE"), required=False, max_length=10)
    vat_number = forms.CharField(
        label=_("N° de TVA intracommunautaire"), required=False, max_length=30
    )

    def clean_code_ape(self):
        code = normalize_code_ape(self.cleaned_data["code_ape"])
        if code:
            validate_code_ape(code)
        return code

    def clean_vat_number(self):
        return "".join(self.cleaned_data["vat_number"].split()).upper()[:20]


class OrderedMultipleChoiceField(forms.MultipleChoiceField):
    """A drop-down of checkboxes whose picked values always come back in the order of the list."""

    widget = MultiSelectDropdown

    def clean(self, value):
        picked = super().clean(value)
        return [key for key, _label in self.choices if key in picked]


def _criterion(field):
    choices, title = Promoter.QUALIFICATION[field]
    return OrderedMultipleChoiceField(label=title, choices=choices.choices, required=False)


class PromoterForm(SectionedFormMixin, PromoterIdentifiersMixin, AddressModelForm):
    kinds = _criterion("kinds")
    event_types = _criterion("event_types")
    aesthetics = _criterion("aesthetics")
    formats = _criterion("formats")
    usual_periods = _criterion("usual_periods")
    event_roles = _criterion("event_roles")

    layout = [
        (_("L'organisateur"), ["name", "follow_up", "email", "phone"]),
        (
            _("Qualification"),
            [
                "kinds",
                "event_types",
                "aesthetics",
                "formats",
                "indicative_capacity",
                "usual_periods",
                "event_roles",
                "qualification_other",
            ],
        ),
        (
            _("Informations légales"),
            [
                "siret",
                "code_ape",
                "vat_number",
                "licence_number",
                "representative_name",
                "representative_role",
            ],
        ),
        (_("Adresse de facturation"), ["billing_address", "postal_code", "city", "department"]),
        (_("Notes"), ["notes"]),
    ]

    class Meta:
        model = Promoter
        fields = [
            "name",
            "follow_up",
            "kinds",
            "event_types",
            "aesthetics",
            "formats",
            "indicative_capacity",
            "usual_periods",
            "event_roles",
            "qualification_other",
            "email",
            "phone",
            "siret",
            "code_ape",
            "vat_number",
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
        }
        help_texts = {
            "follow_up": _("Un repère pour vous : à vous de le changer au fil des échanges."),
            "qualification_other": _("Pour tout ce qui ne figure pas dans les listes ci-dessus."),
        }


class PromoterFilterForm(forms.Form):
    """Filters of the organisers list. Every field is optional; an invalid value is ignored."""

    follow_up = forms.ChoiceField(
        label=_("Suivi"),
        required=False,
        choices=[("", _("Tous les suivis")), *Promoter.FollowUp.choices],
    )
    # query parameter -> (model field, label of the "everything" choice)
    CRITERIA = {
        "kind": ("kinds", _("Tous les types d'organisateur")),
        "event_type": ("event_types", _("Tous les types d'évènement")),
        "aesthetic": ("aesthetics", _("Toutes les esthétiques")),
        "format": ("formats", _("Tous les formats")),
        "period": ("usual_periods", _("Toutes les périodes")),
        "role": ("event_roles", _("Tous les rôles")),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, (field, empty) in self.CRITERIA.items():
            choices, title = Promoter.QUALIFICATION[field]
            self.fields[name] = forms.ChoiceField(
                label=title, required=False, choices=[("", empty), *choices.choices]
            )

    def apply(self, queryset):
        self.is_valid()  # fills cleaned_data with the valid fields, drops the invalid ones
        data = self.cleaned_data
        if data.get("follow_up"):
            queryset = queryset.filter(follow_up=data["follow_up"])
        for name, (field, _empty) in self.CRITERIA.items():
            if data.get(name):
                # The organiser has this value among its several ones.
                queryset = queryset.filter(**{f"{field}__contains": [data[name]]})
        return queryset

    @property
    def is_active(self):
        return any(self.cleaned_data.get(name) for name in self.fields)


class VenueForm(SectionedFormMixin, AddressModelForm):
    layout = [
        (_("Le lieu"), ["name", "capacity", "configuration", "phone"]),
        (_("Adresse"), ["address", "postal_code", "city", "department"]),
        (_("Accès et notes"), ["access_info", "notes"]),
    ]

    class Meta:
        model = Venue
        fields = [
            "name",
            "address",
            "postal_code",
            "city",
            "department",
            "capacity",
            "configuration",
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


class PromoterPublicForm(PromoterIdentifiersMixin, AddressModelForm):
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
