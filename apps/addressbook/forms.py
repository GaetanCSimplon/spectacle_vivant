import datetime

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.forms import AddressModelForm, MultiSelectDropdown, SectionedFormMixin
from apps.tenants.models import Person
from apps.tenants.validators import (
    normalize_code_ape,
    normalize_social_security_number,
    validate_code_ape,
    validate_social_security_number,
)

from . import date_ranges, info_requests, services
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
                *[f"usual_range_{n}" for n in range(1, date_ranges.MAX_RANGES + 1)],
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dates that come back every year (ORG-03): up to MAX_RANGES, one text field each.
        ranges = self.instance.usual_date_ranges if self.instance.pk else []
        for number in range(1, date_ranges.MAX_RANGES + 1):
            known = ranges[number - 1] if number <= len(ranges) else None
            self.fields[f"usual_range_{number}"] = forms.CharField(
                label=_("Plage de dates %(n)s") % {"n": number},
                required=False,
                max_length=40,
                initial=date_ranges.input_text(known) if known else "",
                help_text=_("Chaque année, par exemple : 10/07 au 25/07 (jour/mois).")
                if number == 1
                else "",
            )

    def clean(self):
        cleaned = super().clean()
        parsed = []
        for number in range(1, date_ranges.MAX_RANGES + 1):
            name = f"usual_range_{number}"
            try:
                found = date_ranges.parse_range(cleaned.get(name))
            except forms.ValidationError as error:
                self.add_error(name, error)
                continue
            if found:
                parsed.append(found)
        # Saved with the rest of the organiser (the model form saves the whole instance).
        self.instance.usual_date_ranges = parsed
        return cleaned


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
    promoters = forms.ModelMultipleChoiceField(
        label=_("Organisateurs"),
        required=False,
        queryset=Promoter.objects.none(),
        widget=MultiSelectDropdown,
        help_text=_("Les organisateurs qui font des dates dans ce lieu (facultatif)."),
    )

    layout = [
        (_("Le lieu"), ["name", "capacity", "configuration", "phone", "promoters"]),
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
            "promoters",
            "access_info",
            "notes",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "access_info": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["promoters"].queryset = Promoter.objects.filter(tenant=tenant).order_by("name")


class ContactFilterForm(forms.Form):
    """The "Rattachement" filter of the address book: everyone, organisers, venues or none."""

    LINKS = [
        ("", _("Tous les contacts")),
        ("promoters", _("Liés à un organisateur")),
        ("venues", _("Liés à un lieu")),
        ("none", _("Sans rattachement")),
    ]

    link = forms.ChoiceField(label=_("Rattachement"), required=False, choices=LINKS)

    def apply(self, queryset):
        link = self.cleaned_data.get("link") if self.is_valid() else ""
        if link == "promoters":
            return queryset.filter(promoters__isnull=False)
        if link == "venues":
            return queryset.filter(venues__isnull=False)
        if link == "none":
            return queryset.filter(promoters__isnull=True, venues__isnull=True)
        return queryset


class ContactForm(forms.ModelForm):
    """A contact of the address book, with the organisers and venues it works for (all optional).

    Only this tenant's organisers and venues are offered: another structure's id is an invalid
    choice. A contact with none is simply "sans rattachement" (a directory entry).
    """

    promoters = forms.ModelMultipleChoiceField(
        label=_("Organisateurs"),
        required=False,
        queryset=Promoter.objects.none(),
        widget=MultiSelectDropdown,
    )
    venues = forms.ModelMultipleChoiceField(
        label=_("Lieux"), required=False, queryset=Venue.objects.none(), widget=MultiSelectDropdown
    )

    class Meta:
        model = Contact
        fields = ["name", "role", "email", "phone", "promoters", "venues"]
        # Suggestions only (Accueil, Technique, Comm'...): the role stays free text.
        widgets = {"role": forms.TextInput(attrs={"list": "contact-roles"})}
        help_texts = {
            "role": _("Une seule fonction : « Programmation / Direction » s'il y en a deux."),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["promoters"].queryset = Promoter.objects.filter(tenant=tenant).order_by("name")
        self.fields["venues"].queryset = Venue.objects.filter(tenant=tenant).order_by("name")


class PromoterPublicForm(PromoterIdentifiersMixin, AddressModelForm):
    """What an organiser fills in from the link they received (F-16).

    It is built on a blank, unsaved Promoter and never saved: the answer is only stored until
    the user has reviewed it. Nothing of the real card is shown or touched here. Every field
    is optional, but at least one must be filled in.
    """

    # Declared here so that "213 400 000 000 19" is accepted and cleaned to 14 digits.
    siret = forms.CharField(label=_("SIRET"), required=False, max_length=20)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Several contacts, each with a role (ORG-04): the role is free text with suggestions.
        for slot in range(1, services.CONTACT_SLOTS + 1):
            prefix = f"contact{slot}_"
            self.fields[prefix + "role"] = forms.CharField(
                label=_("Rôle"),
                required=False,
                max_length=255,
                widget=forms.TextInput(attrs={"list": "contact-roles"}),
            )
            self.fields[prefix + "name"] = forms.CharField(
                label=_("Nom"), required=False, max_length=255
            )
            self.fields[prefix + "email"] = forms.EmailField(label=_("E-mail"), required=False)
            self.fields[prefix + "phone"] = forms.CharField(
                label=_("Téléphone"), required=False, max_length=30
            )

    def clean_siret(self):
        siret = "".join(self.cleaned_data["siret"].split())
        if siret and not (siret.isdigit() and len(siret) == 14):
            raise forms.ValidationError(_("Un SIRET comporte 14 chiffres."))
        return siret

    def clean(self):
        cleaned = super().clean()
        contact = []
        for slot in range(1, services.CONTACT_SLOTS + 1):
            values = [cleaned.get(f"contact{slot}_{key}") for key in services.CONTACT_KEYS]
            if any(values) and not cleaned.get(f"contact{slot}_name"):
                self.add_error(f"contact{slot}_name", _("Indiquez le nom de ce contact."))
            contact += values
        answered = [cleaned.get(key) for key, _label in services.PROMOTER_FIELDS] + contact
        if not self.errors and not any(answered):
            raise forms.ValidationError(_("Merci de remplir au moins un champ."))
        return cleaned


class ImportUploadForm(forms.Form):
    """What to import and the CSV file (size and content are checked when it is read)."""

    KINDS = [
        ("contacts", _("Des contacts")),
        ("lieux", _("Des lieux")),
        ("organisateurs", _("Des organisateurs")),
    ]

    kind = forms.ChoiceField(label=_("Que voulez-vous importer ?"), choices=KINDS)
    file = forms.FileField(label=_("Fichier CSV"))

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if not upload.name.lower().endswith(".csv"):
            raise forms.ValidationError(_("Seuls les fichiers .csv sont acceptés."))
        return upload


class ContactInfoForm(forms.Form):
    """What a contact fills in about themselves from the link they received (ORG-07).

    Nothing is saved from here: the answer waits until the user has reviewed it. Every field is
    optional, but at least one must be filled in.
    """

    name = forms.CharField(label=_("Nom"), required=False, max_length=255)
    role = forms.CharField(label=_("Fonction"), required=False, max_length=255)
    email = forms.EmailField(label=_("E-mail"), required=False)
    phone = forms.CharField(label=_("Téléphone"), required=False, max_length=30)

    def clean(self):
        cleaned = super().clean()
        if not self.errors and not any(cleaned.values()):
            raise forms.ValidationError(_("Merci de remplir au moins un champ."))
        return cleaned


class PersonInfoForm(AddressModelForm):
    """What a team member fills in about themselves from the link they received (ORG-07).

    Built on a blank, unsaved Person and never saved here. It carries the private fields, the
    same checks as the team form apply to them.
    """

    social_security_number = forms.CharField(
        label=_("N° de sécurité sociale"),
        required=False,
        max_length=21,
        validators=[validate_social_security_number],
    )

    class Meta:
        model = Person
        fields = [key for key, _label in info_requests.PERSON_FIELDS]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_social_security_number(self):
        return normalize_social_security_number(self.cleaned_data["social_security_number"])

    def clean_birth_date(self):
        birth_date = self.cleaned_data["birth_date"]
        if birth_date is not None and not (
            datetime.date(1900, 1, 1) <= birth_date <= timezone.localdate()
        ):
            raise forms.ValidationError(_("Cette date de naissance n'est pas plausible."))
        return birth_date

    def clean(self):
        cleaned = super().clean()
        if not self.errors and not any(cleaned.values()):
            raise forms.ValidationError(_("Merci de remplir au moins un champ."))
        return cleaned
