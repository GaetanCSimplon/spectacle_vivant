from django import forms
from django.utils.translation import gettext_lazy as _

from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show

from .models import Gig


class GigShowStepForm(forms.Form):
    show = forms.ModelChoiceField(label=_("Spectacle"), queryset=Show.objects.none())

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["show"].queryset = Show.objects.filter(tenant=tenant)


class ShowQuickCreateForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = ["title", "duration_minutes", "default_price"]


class GigPromoterStepForm(forms.Form):
    promoter = forms.ModelChoiceField(label=_("Organisateur"), queryset=Promoter.objects.none())

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["promoter"].queryset = Promoter.objects.filter(tenant=tenant)


class PromoterQuickCreateForm(forms.ModelForm):
    class Meta:
        model = Promoter
        fields = ["name", "siret", "billing_address", "email"]


class GigVenueStepForm(forms.Form):
    venue = forms.ModelChoiceField(label=_("Lieu"), queryset=Venue.objects.none())

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["venue"].queryset = Venue.objects.filter(tenant=tenant)


class VenueQuickCreateForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["name", "address"]


class GigDetailsStepForm(forms.ModelForm):
    class Meta:
        model = Gig
        fields = ["date", "option_expires_on", "price", "conditions"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "option_expires_on": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        date, expires_on = cleaned.get("date"), cleaned.get("option_expires_on")
        if date and expires_on and expires_on > date:
            self.add_error(
                "option_expires_on",
                _("L'option ne peut pas se prolonger après la date du concert."),
            )
        return cleaned
