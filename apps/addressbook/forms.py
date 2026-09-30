from django import forms

from .models import Contact, Promoter, Venue


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


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["name", "address", "capacity"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}


class ContactForm(forms.ModelForm):
    """The parent (Promoter or Venue) is set by the view, never chosen in the form."""

    class Meta:
        model = Contact
        fields = ["name", "role", "email", "phone"]
        # Suggestions only (Accueil, Technique, Comm'...): the role stays free text.
        widgets = {"role": forms.TextInput(attrs={"list": "contact-roles"})}
