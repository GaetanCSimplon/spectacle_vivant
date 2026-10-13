from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import AddressModelForm

from . import services
from .models import Person, Tenant
from .validators import normalize_bic, normalize_code_ape, normalize_iban, validate_code_ape


class OnboardingForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ["name", "legal_form", "vat_regime"]
        help_texts = {
            "legal_form": _("Par exemple : association loi 1901, micro-entreprise, SARL…"),
        }


class TenantProfileForm(AddressModelForm):
    # Declared here because people type "90.01 Z": the model's 5 characters apply after cleaning.
    code_ape = forms.CharField(
        label=_("Code APE"),
        required=False,
        max_length=10,
        help_text=_("4 chiffres et 1 lettre, par exemple 9001Z (spectacle vivant)."),
    )

    class Meta:
        model = Tenant
        fields = [
            "name",
            "legal_form",
            "siret",
            "code_ape",
            "address",
            "postal_code",
            "city",
            "department",
            "vat_regime",
            "vat_rate",
            "vat_number",
            "iban",
            "bic",
            "phone",
            "email",
            "licence_number",
            "representative_name",
            "representative_role",
            "jurisdiction_city",
        ]
        widgets = {"address": forms.Textarea(attrs={"rows": 2})}
        help_texts = {
            "legal_form": _("Par exemple : association loi 1901, micro-entreprise, SARL…"),
            "licence_number": _(
                "Numéro de licence d'entrepreneur de spectacles, si vous en avez un."
            ),
            "jurisdiction_city": _("Ville dont les tribunaux sont compétents en cas de litige."),
        }

    def clean_vat_number(self):
        return "".join(self.cleaned_data["vat_number"].split()).upper()

    def clean_code_ape(self):
        code = normalize_code_ape(self.cleaned_data["code_ape"])
        if code:
            validate_code_ape(code)
        return code

    def clean_iban(self):
        return normalize_iban(self.cleaned_data["iban"])

    def clean_bic(self):
        return normalize_bic(self.cleaned_data["bic"])


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


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            "last_name",
            "first_name",
            "role",
            "status",
            "phone",
            "email",
            "average_fee",
            "notes",
        ]
        widgets = {
            "role": forms.TextInput(attrs={"list": "person-roles"}),
            "status": forms.TextInput(attrs={"list": "person-statuses"}),
            "average_fee": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "role": _("Choisissez une proposition ou écrivez la vôtre."),
            "status": _("Choisissez une proposition ou écrivez la vôtre."),
            "average_fee": _(
                "Facultatif, pour votre suivi. Il n'apparaît jamais dans vos documents."
            ),
            "notes": _("N'y notez pas de numéro de sécurité sociale."),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_options = services.team_suggestions(tenant, "role", services.ROLE_SUGGESTIONS)
        self.status_options = services.team_suggestions(
            tenant, "status", services.STATUS_SUGGESTIONS
        )

    def clean_role(self):
        return " ".join(self.cleaned_data["role"].split())

    def clean_status(self):
        return " ".join(self.cleaned_data["status"].split())

    def clean_average_fee(self):
        fee = self.cleaned_data["average_fee"]
        if fee is not None and fee < 0:
            raise forms.ValidationError(_("Le cachet ne peut pas être négatif."))
        return fee
