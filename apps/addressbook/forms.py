from django import forms

from .models import Promoter


class PromoterForm(forms.ModelForm):
    class Meta:
        model = Promoter
        fields = [
            "name",
            "email",
            "siret",
            "licence_number",
            "representative_name",
            "representative_role",
            "billing_address",
        ]
        widgets = {"billing_address": forms.Textarea(attrs={"rows": 3})}
