from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Tenant


class OnboardingForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ["name", "legal_form", "vat_regime"]
        help_texts = {
            "legal_form": _("Par exemple : association loi 1901, micro-entreprise, SARL…"),
        }


class TenantProfileForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = [
            "name",
            "legal_form",
            "siret",
            "address",
            "vat_regime",
            "licence_number",
            "representative_name",
            "representative_role",
            "jurisdiction_city",
            "contract_party_label",
        ]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "legal_form": _("Par exemple : association loi 1901, micro-entreprise, SARL…"),
            "licence_number": _(
                "Numéro de licence d'entrepreneur de spectacles, si vous en avez un."
            ),
            "jurisdiction_city": _("Ville dont les tribunaux sont compétents en cas de litige."),
            "contract_party_label": _(
                "Comment vous êtes nommé dans le contrat : « L'artiste » ou « Le producteur »."
            ),
        }
