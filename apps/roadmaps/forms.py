from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import AddressModelForm
from apps.gigs.models import GigMember
from apps.tenants.models import Person

from . import documents
from .models import Lodging, Meal, PlaceContact, Roadmap, RoadmapSlot
from .tour_requests import ALL_KEYS

TIME_FORMAT = "%H:%M"


def _time_widget():
    return forms.TimeInput(attrs={"type": "time"}, format=TIME_FORMAT)


class NotesForm(forms.ModelForm):
    class Meta:
        model = Roadmap
        fields = ["notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}


class SlotForm(forms.ModelForm):
    class Meta:
        model = RoadmapSlot
        fields = ["kind", "time", "label", "note"]
        widgets = {"time": _time_widget(), "note": forms.Textarea(attrs={"rows": 2})}


class LodgingForm(AddressModelForm):
    class Meta:
        model = Lodging
        fields = ["name", "address", "postal_code", "city", "department", "arrival_time", "notes"]
        widgets = {"arrival_time": _time_widget(), "notes": forms.Textarea(attrs={"rows": 2})}


class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ["place", "time", "notes"]
        widgets = {"time": _time_widget(), "notes": forms.Textarea(attrs={"rows": 2})}


class PlaceContactForm(forms.ModelForm):
    class Meta:
        model = PlaceContact
        fields = ["name", "role", "phone"]
        help_texts = {"phone": "Visible par toute personne qui a le lien de la feuille de route."}


class MemberForm(forms.ModelForm):
    class Meta:
        model = GigMember
        fields = ["name", "role", "phone", "email"]
        widgets = {"role": forms.TextInput(attrs={"list": "member-roles"})}


def _public_time():
    return forms.TimeInput(attrs={"type": "time"}, format=TIME_FORMAT)


class TourRequestForm(forms.Form):
    """What an organiser answers from the "Régie de tournée" link (F-90).

    Nothing is saved from here: the answer waits until the owner reviews it. Every field is
    optional, but at least one must be filled in. There is no file field, and nothing in it
    chooses a structure or a date: those come from the link.
    """

    get_in_time = forms.TimeField(
        label=_("Arrivée de l'équipe (get in)"), required=False, widget=_public_time()
    )
    soundcheck_time = forms.TimeField(label=_("Balances"), required=False, widget=_public_time())
    performance_time = forms.TimeField(label=_("Concert"), required=False, widget=_public_time())
    access_notes = forms.CharField(
        label=_("Accès, chargement, stationnement, loges, wifi, consignes"),
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    meal_place = forms.CharField(label=_("Lieu du repas"), required=False, max_length=255)
    meal_time = forms.TimeField(label=_("Heure du repas"), required=False, widget=_public_time())
    meal_notes = forms.CharField(
        label=_("Nombre de couverts, régimes particuliers"),
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    lodging_name = forms.CharField(label=_("Nom de l'hébergement"), required=False, max_length=255)
    lodging_address = forms.CharField(label=_("Adresse"), required=False, max_length=255)
    lodging_arrival_time = forms.TimeField(
        label=_("Heure d'arrivée"), required=False, widget=_public_time()
    )
    lodging_notes = forms.CharField(
        label=_("Détails (petit-déjeuner, accès tardif…)"),
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    contact_name = forms.CharField(label=_("Nom"), required=False, max_length=255)
    contact_role = forms.CharField(label=_("Fonction"), required=False, max_length=255)
    contact_phone = forms.CharField(label=_("Téléphone"), required=False, max_length=30)
    remarks = forms.CharField(
        label=_("Autres remarques"),
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        if not any(cleaned.get(key) not in (None, "") for key in ALL_KEYS):
            raise forms.ValidationError(_("Remplissez au moins un champ."))
        if (cleaned.get("contact_role") or cleaned.get("contact_phone")) and not cleaned.get(
            "contact_name"
        ):
            self.add_error("contact_name", _("Indiquez le nom de ce contact."))
        return cleaned


class RoadmapDocumentForm(forms.Form):
    """A file for the team of a date: a PDF, a JPEG or a PNG of 10 MB at most, judged by content."""

    title = forms.CharField(label=_("Titre"), max_length=150)
    file = forms.FileField(label=_("Fichier (PDF, JPEG ou PNG, 10 Mo au maximum)"))
    person = forms.ModelChoiceField(
        label=_("Pour qui ?"),
        queryset=None,
        required=False,
        empty_label=_("Toute l'équipe de la date"),
    )

    def __init__(self, *args, gig=None, **kwargs):
        super().__init__(*args, **kwargs)
        ids = [person.pk for person in documents.audience_choices(gig)] if gig else []
        # Only people who are on this date: the form cannot reach anybody else.
        self.fields["person"].queryset = (
            Person.objects.filter(tenant=gig.tenant, pk__in=ids) if gig else Person.objects.none()
        )
        self.kind = None

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError(_("Donnez un titre au document."))
        return title

    def clean_file(self):
        file = self.cleaned_data["file"]
        if file.size > documents.MAX_SIZE:
            raise forms.ValidationError(_("Le fichier est trop lourd (10 Mo au maximum)."))
        self.kind = documents.kind_of(file.read(8))
        file.seek(0)
        if self.kind is None:
            raise forms.ValidationError(_("Le document doit être un PDF, un JPEG ou un PNG."))
        return file
