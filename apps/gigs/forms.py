from django import forms
from django.utils.translation import gettext_lazy as _

from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show
from apps.core.forms import AddressModelForm

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


class PromoterQuickCreateForm(AddressModelForm):
    class Meta:
        model = Promoter
        fields = [
            "name",
            "siret",
            "billing_address",
            "postal_code",
            "city",
            "department",
            "email",
        ]


class GigVenueStepForm(forms.Form):
    venue = forms.ModelChoiceField(label=_("Lieu"), queryset=Venue.objects.none())

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["venue"].queryset = Venue.objects.filter(tenant=tenant)


class VenueQuickCreateForm(AddressModelForm):
    class Meta:
        model = Venue
        fields = ["name", "address", "postal_code", "city", "department"]


class GigFilterForm(forms.Form):
    """Filters of "Mes dates". Every field is optional; an invalid value is simply ignored."""

    status = forms.ChoiceField(
        label=_("Statut"),
        required=False,
        choices=[("", _("Tous les statuts")), *Gig.Status.choices],
    )
    month = forms.DateField(
        label=_("Mois"),
        required=False,
        input_formats=["%Y-%m"],
        widget=forms.DateInput(attrs={"type": "month"}, format="%Y-%m"),
    )
    show = forms.ModelChoiceField(
        label=_("Spectacle"),
        required=False,
        queryset=Show.objects.none(),
        empty_label=_("Tous les spectacles"),
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only this tenant's shows can be chosen: another tenant's id is an invalid value.
        self.fields["show"].queryset = Show.objects.filter(tenant=tenant).order_by("title")

    def apply(self, queryset):
        self.is_valid()  # fills cleaned_data with the valid fields, drops the invalid ones
        data = self.cleaned_data
        if data.get("status"):
            queryset = queryset.filter(status=data["status"])
        if data.get("month"):
            queryset = queryset.filter(
                date__year=data["month"].year, date__month=data["month"].month
            )
        if data.get("show"):
            queryset = queryset.filter(show=data["show"])
        return queryset


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


class PriceForm(forms.Form):
    """New price HT of a gig; the amount is checked by `services.clean_price`."""

    price = forms.CharField(
        label=_("Prix HT (€)"),
        widget=forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off"}),
    )
    note = forms.CharField(
        label=_("Note (facultatif)"),
        max_length=255,
        required=False,
        help_text=_("Par exemple : négocié par téléphone, remise pour une 2e date."),
    )


class TermsForm(forms.ModelForm):
    """The payment terms of the future contract (quick edit from the card)."""

    class Meta:
        model = Gig
        fields = ["deposit_due_on", "balance_due_on", "payment_method"]
        widgets = {
            "deposit_due_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "balance_due_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
