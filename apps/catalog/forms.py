from django import forms

from .models import Show


class ShowForm(forms.ModelForm):
    # A link typed without a scheme ("exemple.fr/epk") is completed with https://. Said here,
    # on the field, because the global setting that did it is going away with Django 6.
    epk_url = forms.URLField(
        label=Show._meta.get_field("epk_url").verbose_name, required=False, assume_scheme="https"
    )

    class Meta:
        model = Show
        fields = [
            "title",
            "group_name",
            "performers",
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
            "performers": forms.Textarea(attrs={"rows": 3}),
            "tech_sheet_text": forms.Textarea(attrs={"rows": 5}),
        }
