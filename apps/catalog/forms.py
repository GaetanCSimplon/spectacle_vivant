from django import forms

from .models import Show


class ShowForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = [
            "title",
            "group_name",
            "performers",
            "duration_minutes",
            "default_price",
            "crew_size",
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
