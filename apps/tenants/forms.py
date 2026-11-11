from datetime import date

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Show
from apps.core.forms import AddressModelForm, SectionedFormMixin
from apps.finance import bord

from . import choices, services
from .models import Person, Tenant
from .validators import (
    format_siret,
    normalize_bic,
    normalize_code_ape,
    normalize_iban,
    normalize_siret,
    normalize_social_security_number,
    validate_code_ape,
    validate_siret,
    validate_social_security_number,
)

OTHER = "other"


def _legal_form_choices():
    return [
        ("", "---------"),
        *((label, label) for label in choices.LEGAL_FORMS),
        (OTHER, _("Autre (à préciser)")),
    ]


def _role_choices():
    return [
        ("", "---------"),
        *(
            (group, [(role, role) for role in roles])
            for group, roles in choices.REPRESENTATIVE_ROLES
        ),
        (OTHER, _("Autre (à préciser)")),
    ]


class ChoiceOrOtherMixin:
    """A field offered as a list with "Autre (à préciser)" and a free text next to it.

    The model field keeps the readable text, so a value typed before the list existed is shown
    under "Autre" and is never lost. Subclasses declare `<name>` (the list) and `<name>_other`.
    """

    other_fields = ()  # ((field name, the values of its list), ...)

    def _show_current_choices(self):
        for name, known in self.other_fields:
            current = getattr(self.instance, name, "")
            if current and current not in known:
                self.initial[name] = OTHER
                self.initial[f"{name}_other"] = current

    def _merge_others(self, cleaned):
        for name, _known in self.other_fields:
            other = " ".join(cleaned.pop(f"{name}_other", "").split())
            if cleaned.get(name) == OTHER:
                if not other:
                    self.add_error(f"{name}_other", _("Précisez votre choix."))
                cleaned[name] = other


class OnboardingForm(ChoiceOrOtherMixin, forms.ModelForm):
    other_fields = (("legal_form", choices.LEGAL_FORMS),)

    legal_form = forms.ChoiceField(
        label=_("Forme juridique"), required=False, choices=_legal_form_choices
    )
    legal_form_other = forms.CharField(
        label=_("Autre forme juridique"),
        required=False,
        max_length=255,
        help_text=_("À remplir seulement si vous avez choisi « Autre »."),
    )

    field_order = ["name", "legal_form", "legal_form_other", "vat_regime"]

    class Meta:
        model = Tenant
        fields = ["name", "legal_form", "vat_regime"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._show_current_choices()

    def clean(self):
        cleaned = super().clean()
        self._merge_others(cleaned)
        return cleaned


class TenantProfileForm(ChoiceOrOtherMixin, SectionedFormMixin, AddressModelForm):
    layout = [
        (
            _("La structure"),
            ["name", "legal_form", "legal_form_other", "siret", "code_ape", "licence_number"],
        ),
        (_("Adresse"), ["address", "postal_code", "city", "department"]),
        (_("Contact"), ["phone", "email"]),
        (_("TVA"), ["vat_regime", "vat_rate", "vat_number"]),
        (_("Coordonnées bancaires"), ["iban", "bic"]),
        (
            _("Représentant et tribunal"),
            [
                "representative_first_name",
                "representative_last_name",
                "representative_role",
                "representative_role_other",
                "jurisdiction_city",
            ],
        ),
    ]
    other_fields = (
        ("legal_form", choices.LEGAL_FORMS),
        ("representative_role", choices.ROLES),
    )

    legal_form = forms.ChoiceField(
        label=_("Forme juridique"), required=False, choices=_legal_form_choices
    )
    legal_form_other = forms.CharField(
        label=_("Autre forme juridique"),
        required=False,
        max_length=255,
        help_text=_("À remplir seulement si vous avez choisi « Autre »."),
    )
    representative_role = forms.ChoiceField(
        label=_("Qualité du représentant"), required=False, choices=_role_choices
    )
    representative_role_other = forms.CharField(
        label=_("Autre qualité"),
        required=False,
        max_length=255,
        help_text=_("À remplir seulement si vous avez choisi « Autre »."),
    )
    # Declared here because people type "123 456 789 00012": the model's 14 digits apply after
    # cleaning.
    siret = forms.CharField(
        label=_("SIRET"),
        required=False,
        max_length=20,
        help_text=_("14 chiffres. Les espaces sont acceptés."),
    )
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
            "representative_first_name",
            "representative_last_name",
            "representative_role",
            "jurisdiction_city",
        ]
        widgets = {"address": forms.Textarea(attrs={"rows": 2})}
        help_texts = {
            "licence_number": _(
                "Numéro de licence d'entrepreneur de spectacles, si vous en avez un."
            ),
            "jurisdiction_city": _("Ville dont les tribunaux sont compétents en cas de litige."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._show_current_choices()
        self.initial["siret"] = format_siret(self.instance.siret)
        instance = self.instance
        if instance.representative_name and not (
            instance.representative_first_name or instance.representative_last_name
        ):
            # Typed in one field before: shown as the last name, to be split once by the user.
            self.initial["representative_last_name"] = instance.representative_name
            self.fields["representative_last_name"].help_text = _(
                "Ce nom était saisi en un seul champ : répartissez-le entre prénom et nom."
            )

    def clean_siret(self):
        siret = normalize_siret(self.cleaned_data["siret"])
        if siret:
            validate_siret(siret)
        return siret

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

    def clean(self):
        cleaned = super().clean()
        self._merge_others(cleaned)
        first = " ".join(cleaned.get("representative_first_name", "").split())
        last = " ".join(cleaned.get("representative_last_name", "").split())
        cleaned["representative_first_name"], cleaned["representative_last_name"] = first, last
        # The documents print this one: "First Last".
        self.instance.representative_name = f"{first} {last}".strip()
        return cleaned


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


class PersonForm(SectionedFormMixin, AddressModelForm):
    layout = [
        (
            _("La personne"),
            ["last_name", "first_name", "role", "status", "is_artist", "is_technician"],
        ),
        (_("Contact"), ["phone", "email"]),
        (
            _("Informations privées (propriétaire seulement)"),
            [
                "birth_date",
                "social_security_number",
                "address",
                "postal_code",
                "city",
                "department",
                "guso_number",
            ],
        ),
        (_("Suivi"), ["average_fee", "notes"]),
    ]

    # Private data: only the owner sees and changes these (see __init__).
    PRIVATE_FIELDS = [
        "address",
        "postal_code",
        "city",
        "department",
        "guso_number",
        "birth_date",
        "social_security_number",
    ]

    # Typed with spaces ("1 85 05 78 006 084 91"): stored without them (see clean_*).
    social_security_number = forms.CharField(
        label=_("N° de sécurité sociale"),
        required=False,
        max_length=21,
        validators=[validate_social_security_number],
    )

    class Meta:
        model = Person
        fields = [
            "last_name",
            "first_name",
            "role",
            "is_artist",
            "is_technician",
            "status",
            "phone",
            "email",
            "birth_date",
            "social_security_number",
            "address",
            "postal_code",
            "city",
            "department",
            "guso_number",
            "average_fee",
            "notes",
        ]
        widgets = {
            "role": forms.TextInput(attrs={"list": "person-roles"}),
            "status": forms.TextInput(attrs={"list": "person-statuses"}),
            "average_fee": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }
        help_texts = {
            "role": _("Choisissez une proposition ou écrivez la vôtre."),
            "status": _("Choisissez une proposition ou écrivez la vôtre."),
            "address": _("Visible par le propriétaire de la structure seulement."),
            "guso_number": _("Visible par le propriétaire seulement. Pour votre suivi."),
            "birth_date": _("Visible par le propriétaire seulement."),
            "social_security_number": _(
                "Visible par le propriétaire seulement, pour la personne qui gère la paie et "
                "l'administratif. Il n'apparaît jamais dans vos documents."
            ),
            "is_artist": _("Cochez l'une, l'autre ou les deux."),
            "average_fee": _(
                "Facultatif, pour votre suivi. Il n'apparaît jamais dans vos documents."
            ),
            "notes": _("N'y notez pas de numéro de sécurité sociale : il a son propre champ."),
        }

    def __init__(self, *args, tenant=None, is_owner=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not is_owner:
            for name in self.PRIVATE_FIELDS:
                del self.fields[name]
        self.role_options = services.team_suggestions(tenant, "role", services.ROLE_SUGGESTIONS)
        self.status_options = services.team_suggestions(
            tenant, "status", services.STATUS_SUGGESTIONS
        )

    def clean_role(self):
        return " ".join(self.cleaned_data["role"].split())

    def clean_status(self):
        return " ".join(self.cleaned_data["status"].split())

    def clean_social_security_number(self):
        return normalize_social_security_number(self.cleaned_data["social_security_number"])

    def clean_birth_date(self):
        birth_date = self.cleaned_data["birth_date"]
        if birth_date is not None and not date(1900, 1, 1) <= birth_date <= timezone.localdate():
            raise forms.ValidationError(_("Cette date de naissance n'est pas plausible."))
        return birth_date

    def clean_average_fee(self):
        fee = self.cleaned_data["average_fee"]
        if fee is not None and fee < 0:
            raise forms.ValidationError(_("Le cachet ne peut pas être négatif."))
        return fee


class BordFilterForm(forms.Form):
    """Filters of the Bòrd page. Every field is optional; an invalid value is ignored."""

    PERIODS = [
        ("mois", _("Ce mois-ci")),
        ("trimestre", _("Ce trimestre")),
        ("annee", _("Cette année")),
        ("perso", _("Période choisie")),
    ]

    period = forms.ChoiceField(label=_("Période"), required=False, choices=PERIODS)
    start = forms.DateField(
        label=_("Du"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    end = forms.DateField(
        label=_("Au"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    show = forms.ModelChoiceField(
        label=_("Spectacle"),
        required=False,
        queryset=Show.objects.none(),
        empty_label=_("Tous les spectacles"),
    )
    figure = forms.ChoiceField(
        label=_("Chiffres à afficher"), required=False, choices=list(bord.FIGURES.items())
    )
    status = forms.ChoiceField(
        label=_("Statut"),
        required=False,
        choices=[("", _("Tous les statuts")), *bord.STATUSES.items()],
    )
    spender = forms.ChoiceField(label=_("Dépenses faites par"), required=False)

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only this tenant's shows can be chosen: another tenant's id is an invalid value.
        self.fields["show"].queryset = Show.objects.filter(tenant=tenant).order_by("title")
        self.fields["spender"].choices = [
            ("", _("Tout le monde")),
            ("structure", _("La structure")),
            *((str(p.pk), p.full_name) for p in Person.objects.filter(tenant=tenant)),
        ]

    def filters(self, today):
        """The `bord.Filters` for this form; whatever is missing or invalid takes its default."""
        self.is_valid()
        data = self.cleaned_data
        period = data.get("period") or "annee"
        start, end = data.get("start"), data.get("end")
        if period == "perso" and start and end and start <= end:
            bounds = (start, end)
        else:
            bounds = bord.period_bounds("annee" if period == "perso" else period, today)
        return bord.Filters(
            start=bounds[0],
            end=bounds[1],
            show=data.get("show"),
            figure=data.get("figure") or bord.DEFAULT_FIGURE,
            status=data.get("status") or "",
            spender=data.get("spender") or "",
        )
