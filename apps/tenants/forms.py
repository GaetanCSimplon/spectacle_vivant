from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Tenant
from .validators import normalize_iban


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
            "vat_rate",
            "vat_number",
            "iban",
            "licence_number",
            "representative_name",
            "representative_role",
            "jurisdiction_city",
        ]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "legal_form": _("Par exemple : association loi 1901, micro-entreprise, SARL…"),
            "licence_number": _(
                "Numéro de licence d'entrepreneur de spectacles, si vous en avez un."
            ),
            "jurisdiction_city": _("Ville dont les tribunaux sont compétents en cas de litige."),
        }

    def clean_vat_number(self):
        return "".join(self.cleaned_data["vat_number"].split()).upper()

    def clean_iban(self):
        return normalize_iban(self.cleaned_data["iban"])


class DeleteTenantForm(forms.Form):
    """Asks for the structure's name and the user's password before a deletion."""

    name = forms.CharField(label=_("Nom de la structure"))
    password = forms.CharField(label=_("Votre mot de passe"), widget=forms.PasswordInput)

    def __init__(self, *args, user, tenant, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.tenant = tenant

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if name != self.tenant.name:
            raise forms.ValidationError(_("Ce n'est pas le nom exact de votre structure."))
        return name

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(_("Mot de passe incorrect."))
        return password
