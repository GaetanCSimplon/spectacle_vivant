from django import forms
from django.utils.translation import gettext_lazy as _

from . import services
from .models import Contact, Promoter, Venue


class PromoterForm(forms.ModelForm):
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
            "notes",
        ]
        widgets = {
            "billing_address": forms.Textarea(attrs={"rows": 3}),
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


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["name", "address", "capacity", "phone", "access_info", "notes"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
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
