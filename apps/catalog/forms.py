from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import MultiSelectDropdown, SectionedFormMixin
from apps.tenants.models import Person

from .models import Show
from .validators import ObjectNumberMixin


class ShowForm(ObjectNumberMixin, SectionedFormMixin, forms.ModelForm):
    layout = [
        (_("Le spectacle"), ["title", "group_name", "cast", "duration_minutes", "default_price"]),
        (
            _("En tournée"),
            [
                "crew_size",
                "artists_count",
                "technicians_count",
                "soundcheck_minutes",
                "soundcheck_to_set_minutes",
            ],
        ),
        (_("Documents"), ["tech_sheet_text", "tech_sheet_file", "rider_file", "epk_url"]),
        (_("Droits et suivi"), ["sacem_number", "sacem_object_number", "analytic_code"]),
    ]

    # A link typed without a scheme ("exemple.fr/epk") is completed with https://. Said here,
    # on the field, because the global setting that did it is going away with Django 6.
    epk_url = forms.URLField(
        label=Show._meta.get_field("epk_url").verbose_name, required=False, assume_scheme="https"
    )

    # Someone who is not in the team yet: created and added to the team when the form is saved.
    new_first_name = forms.CharField(label=_("Prénom"), max_length=100, required=False)
    new_last_name = forms.CharField(label=_("Nom"), max_length=100, required=False)
    new_is_artist = forms.BooleanField(label=_("Artiste"), required=False)
    new_is_technician = forms.BooleanField(label=_("Technicien"), required=False)

    NEW_MEMBER_FIELDS = ["new_first_name", "new_last_name", "new_is_artist", "new_is_technician"]

    class Meta:
        model = Show
        fields = [
            "title",
            "group_name",
            "cast",
            "duration_minutes",
            "default_price",
            "crew_size",
            "artists_count",
            "technicians_count",
            "soundcheck_minutes",
            "soundcheck_to_set_minutes",
            "analytic_code",
            "tech_sheet_text",
            "tech_sheet_file",
            "rider_file",
            "epk_url",
            "sacem_number",
            "sacem_object_number",
        ]
        widgets = {
            "cast": MultiSelectDropdown,
            "tech_sheet_text": forms.Textarea(attrs={"rows": 5}),
        }
        help_texts = {
            "cast": _("Les membres de votre équipe. Il manque quelqu'un ? Ajoutez-le plus bas."),
            "artists_count": _("Calculé d'après la distribution dès qu'un membre est choisi."),
            "technicians_count": _("Calculé d'après la distribution dès qu'un membre est choisi."),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        # Only the people of this structure can be chosen.
        self.fields["cast"].queryset = Person.objects.filter(tenant=tenant)

    @property
    def sections(self):
        """The titled blocks of the show; the new-member fields have their own card."""
        blocks = super().sections
        return [
            block
            for block in blocks
            if not any(field.name in self.NEW_MEMBER_FIELDS for field in block["fields"])
        ]

    @property
    def new_member_fields(self):
        return [self[name] for name in self.NEW_MEMBER_FIELDS]

    def clean(self):
        cleaned = super().clean()
        first = " ".join((cleaned.get("new_first_name") or "").split())
        last = " ".join((cleaned.get("new_last_name") or "").split())
        cleaned["new_first_name"], cleaned["new_last_name"] = first, last
        if bool(first) != bool(last):
            missing = "new_last_name" if first else "new_first_name"
            self.add_error(missing, _("Indiquez le prénom et le nom du nouveau membre."))
        return cleaned

    def save(self, commit=True):
        show = super().save(commit=commit)
        if not commit:
            return show
        cast = list(self.cleaned_data["cast"])
        if self.cleaned_data.get("new_first_name"):
            member = Person.objects.create(
                tenant=self.tenant,
                first_name=self.cleaned_data["new_first_name"],
                last_name=self.cleaned_data["new_last_name"],
                is_artist=self.cleaned_data["new_is_artist"],
                is_technician=self.cleaned_data["new_is_technician"],
            )
            show.cast.add(member)
            cast.append(member)
        if cast:
            # The counts follow the chosen members instead of being typed twice.
            show.artists_count = sum(1 for person in cast if person.is_artist)
            show.technicians_count = sum(1 for person in cast if person.is_technician)
            show.save(update_fields=["artists_count", "technicians_count"])
        return show
