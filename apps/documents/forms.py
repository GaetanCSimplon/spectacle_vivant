from django import forms
from django.utils.translation import gettext_lazy as _

from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show
from apps.gigs.models import Gig
from apps.tenants.models import Tenant

from .models import Contract

TIME_FORMAT = "%H:%M"


def _time_widget():
    return forms.TimeInput(attrs={"type": "time"}, format=TIME_FORMAT)


class GigCompletionForm(forms.ModelForm):
    class Meta:
        model = Gig
        fields = [
            "get_in_time",
            "soundcheck_time",
            "performance_time",
            "crew_headcount",
            "invitations_count",
            "signing_place",
            "is_free",
            "ticket_price",
        ]
        widgets = {
            "get_in_time": _time_widget(),
            "soundcheck_time": _time_widget(),
            "performance_time": _time_widget(),
            "is_free": forms.CheckboxInput(attrs={"x-model": "free"}),
            "ticket_price": forms.NumberInput(attrs={":disabled": "free", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A disabled input is not submitted: an empty price simply means 0.
        self.fields["ticket_price"].required = False
        self.fields["invitations_count"].required = False

    def clean_invitations_count(self):
        return self.cleaned_data["invitations_count"] or 0

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("is_free") or cleaned_data.get("ticket_price") is None:
            cleaned_data["ticket_price"] = 0
        return cleaned_data


class ShowCompletionForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = ["group_name", "sacem_number", "sacem_object_number"]


class VenueCompletionForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["capacity"]


class PromoterCompletionForm(forms.ModelForm):
    class Meta:
        model = Promoter
        fields = ["siret", "licence_number", "representative_name", "representative_role"]


class TenantCompletionForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = [
            "siret",
            "address",
            "licence_number",
            "representative_name",
            "representative_role",
            "jurisdiction_city",
            "contract_party_label",
        ]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "jurisdiction_city": _("Ville dont les tribunaux sont compétents en cas de litige."),
            "contract_party_label": _(
                "Comment vous êtes nommé dans le contrat : « L'artiste » ou « Le producteur »."
            ),
        }


class ContractCompletionForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ["signatory_name", "signatory_role"]
        help_texts = {
            "signatory_name": _("À remplir seulement si le signataire n'est pas le représentant."),
        }
