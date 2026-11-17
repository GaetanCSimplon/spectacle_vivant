import datetime
from decimal import Decimal

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.addressbook.forms import PromoterIdentifiersMixin
from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show
from apps.catalog.validators import ObjectNumberMixin
from apps.core.forms import MultiSelectDropdown
from apps.gigs import hospitality
from apps.gigs.forms import PaymentTermsMixin
from apps.gigs.models import Gig

from . import library
from .invoicing import MAX_DUE_DAYS
from .models import KIND_UNITS, Contract, LineKind, LineUnit, Quote

TIME_FORMAT = "%H:%M"


def _time_widget():
    return forms.TimeInput(attrs={"type": "time"}, format=TIME_FORMAT)


class GigCompletionForm(PaymentTermsMixin, forms.ModelForm):
    class Meta:
        model = Gig
        fields = [
            "option_expires_on",
            "get_in_time",
            "soundcheck_time",
            "performance_time",
            "crew_headcount",
            "invitations_count",
            "signing_place",
            "event_name",
            "performances_count",
            "copies_count",
            "setting",
            "outdoor_fallback",
            "outdoor_fallback_details",
            "outdoor_procedure",
            "outdoor_referents",
            "outdoor_financial_terms",
            "payment_method",
            "price_includes",
            "extra_fees_description",
            "extra_fees_amount",
            "extra_fees_accepted",
            "billing_notes",
            "deposit_required",
            "deposit_percent",
            "deposit_term",
            "deposit_term_days",
            "deposit_due_on",
            "balance_term",
            "balance_due_on",
            "meals_covered_by",
            "meals_count",
            "meals_notes",
            "lodging_covered_by",
            "lodging_nights",
            "lodging_notes",
            "transport_covered_by",
            "transport_notes",
            "local_transport",
            "other_hospitality",
            "onsite_contact_name",
            "onsite_contact_phone",
            "is_free",
            "ticket_price",
        ]
        widgets = {
            "option_expires_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "outdoor_fallback_details": forms.Textarea(attrs={"rows": 2}),
            "outdoor_procedure": forms.Textarea(attrs={"rows": 2}),
            "outdoor_referents": forms.Textarea(attrs={"rows": 2}),
            "outdoor_financial_terms": forms.Textarea(attrs={"rows": 2}),
            "price_includes": forms.Textarea(attrs={"rows": 2}),
            "extra_fees_description": forms.Textarea(attrs={"rows": 2}),
            "billing_notes": forms.Textarea(attrs={"rows": 2}),
            "setting": forms.Select(attrs={"x-model": "setting"}),
            **PaymentTermsMixin.term_widgets(),
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
        self.fields["deposit_percent"].required = False
        self.fields["deposit_required"].required = False
        self.fields["extra_fees_amount"].widget.attrs["step"] = "0.01"
        self.fields["performances_count"].required = False
        self.fields["copies_count"].required = False
        self._prepare_terms()
        self._keep_old_sentences()
        # An option's validity only matters while the gig is still an option.
        if self.instance.status != Gig.Status.OPTION:
            del self.fields["option_expires_on"]

    # The three blocks of the page "Compléter le contrat" (CTR-06), by volet.
    CONTRACT_FIELDS = (
        "event_name",
        "option_expires_on",
        "performances_count",
        "copies_count",
        "signing_place",
        "invitations_count",
        "is_free",
        "ticket_price",
    )
    OUTDOOR_FIELDS = (
        "setting",
        "outdoor_fallback",
        "outdoor_fallback_details",
        "outdoor_procedure",
        "outdoor_referents",
        "outdoor_financial_terms",
    )
    BUDGET_FIELDS = (
        "payment_method",
        "price_includes",
        "extra_fees_description",
        "extra_fees_amount",
        "extra_fees_accepted",
        "billing_notes",
        "deposit_required",
        "deposit_percent",
        "deposit_term",
        "deposit_term_days",
        "deposit_due_on",
        "balance_term",
        "balance_due_on",
        "meals_covered_by",
        "meals_count",
        "meals_notes",
        "lodging_covered_by",
        "lodging_nights",
        "lodging_notes",
        "transport_covered_by",
        "transport_notes",
    )
    ROADMAP_FIELDS = (
        "get_in_time",
        "soundcheck_time",
        "performance_time",
        "crew_headcount",
        "local_transport",
        "other_hospitality",
        "onsite_contact_name",
        "onsite_contact_phone",
    )

    def _block(self, names):
        return [self[name] for name in names if name in self.fields]

    @property
    def contract_fields(self):
        return self._block(self.CONTRACT_FIELDS)

    @property
    def outdoor_fields(self):
        return self._block(self.OUTDOOR_FIELDS)

    @property
    def budget_fields(self):
        return self._block(self.BUDGET_FIELDS)

    @property
    def roadmap_fields(self):
        return self._block(self.ROADMAP_FIELDS)

    def _keep_old_sentences(self):
        """A sentence typed before the choices existed becomes the "précisions", not lost."""
        gig = self.instance
        for sentence, covered_by, count, notes in (
            ("meals", "meals_covered_by", "meals_count", "meals_notes"),
            ("lodging", "lodging_covered_by", "lodging_nights", "lodging_notes"),
        ):
            old = getattr(gig, sentence)
            if old and not (getattr(gig, covered_by) or getattr(gig, count) or getattr(gig, notes)):
                self.initial[notes] = old[: self.fields[notes].max_length]

    def _compose_sentences(self, cleaned):
        """Write what the contract prints from the answers (it reads `meals` and `lodging`)."""
        for sentence, covered_by, count, notes, unit in (
            ("meals", "meals_covered_by", "meals_count", "meals_notes", hospitality.MEAL_UNIT),
            (
                "lodging",
                "lodging_covered_by",
                "lodging_nights",
                "lodging_notes",
                hospitality.NIGHT_UNIT,
            ),
        ):
            text = hospitality.compose(
                cleaned.get(covered_by), cleaned.get(count), unit, cleaned.get(notes)
            )
            # At most 150 characters of notes and a short phrase: always fits the 255 of the field.
            setattr(self.instance, sentence, text)

    def clean_deposit_percent(self):
        # Left empty: keep the current value (0 for a new gig).
        value = self.cleaned_data["deposit_percent"]
        return self.instance.deposit_percent if value is None else value

    def clean_performances_count(self):
        # Left empty: keep the current value (1 for a new gig).
        value = self.cleaned_data["performances_count"]
        return self.instance.performances_count if value is None else value

    def clean_copies_count(self):
        # Left empty: keep the current value (2 for a new gig).
        value = self.cleaned_data["copies_count"]
        return self.instance.copies_count if value is None else value

    def clean_invitations_count(self):
        return self.cleaned_data["invitations_count"] or 0

    def clean(self):
        cleaned_data = super().clean()
        expires_on = cleaned_data.get("option_expires_on")
        if expires_on and expires_on > self.instance.date:
            self.add_error(
                "option_expires_on",
                _("L'option ne peut pas se prolonger après la date du concert."),
            )
        if cleaned_data.get("is_free") or cleaned_data.get("ticket_price") is None:
            cleaned_data["ticket_price"] = 0
        self._compose_sentences(cleaned_data)
        return self.clean_terms(cleaned_data)


class ShowCompletionForm(ObjectNumberMixin, forms.ModelForm):
    class Meta:
        model = Show
        fields = [
            "group_name",
            "sacem_number",
            "sacem_object_number",
            "soundcheck_minutes",
            "soundcheck_to_set_minutes",
        ]


class VenueCompletionForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["capacity", "configuration"]


class PromoterCompletionForm(PromoterIdentifiersMixin, forms.ModelForm):
    class Meta:
        model = Promoter
        fields = [
            "siret",
            "code_ape",
            "vat_number",
            "licence_number",
            "representative_name",
            "representative_role",
        ]


class ContractCompletionForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ["signatory_name", "signatory_role"]
        help_texts = {
            "signatory_name": _("À remplir seulement si le signataire n'est pas le représentant."),
        }


MAX_SIGNED_PDF_SIZE = 10 * 1024 * 1024


class SignedPdfForm(forms.Form):
    """The scan of the signed contract: a real PDF of 10 Mo at most."""

    signed_pdf = forms.FileField(label=_("PDF signé"), required=False)

    def clean_signed_pdf(self):
        file = self.cleaned_data["signed_pdf"]
        if not file:
            return None
        if file.size > MAX_SIGNED_PDF_SIZE:
            raise forms.ValidationError(_("Le fichier est trop lourd (10 Mo au maximum)."))
        # The extension proves nothing: check that the content really is a PDF.
        if file.read(5) != b"%PDF-":
            raise forms.ValidationError(_("Le fichier doit être un PDF."))
        file.seek(0)
        return file


class QuoteAcceptForm(SignedPdfForm):
    """ "Devis signé reçu": the day it came back, and its scan when there is one."""

    accepted_on = forms.DateField(
        label=_("Reçu le"), widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    )


class InvoiceDetailsForm(forms.Form):
    """The optional details of a draft invoice: the customer's purchase order, the due date."""

    purchase_order_number = forms.CharField(
        label=_("N° de bon de commande"),
        required=False,
        max_length=50,
        help_text=_("Si l'organisateur vous en a donné un (souvent les collectivités)."),
    )
    due_date = forms.DateField(
        label=_("Échéance"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        help_text=_("Laissez vide pour reprendre le délai de « Ma structure »."),
    )

    def clean_due_date(self):
        due_date = self.cleaned_data["due_date"]
        if due_date and due_date > timezone.localdate() + datetime.timedelta(days=MAX_DUE_DAYS):
            raise forms.ValidationError(
                _("L'échéance ne peut pas dépasser %(n)s jours après l'émission.")
                % {"n": MAX_DUE_DAYS}
            )
        return due_date


# Alpine: show only the units the chosen kind allows, and move off a hidden one.
HIDE_OTHER_UNITS = (
    "(() => { for (const o of $el.options) {"
    " const ok = o.dataset.kinds.split(' ').includes(kind); o.hidden = !ok; o.disabled = !ok }"
    " if ($el.selectedOptions[0]?.disabled) {"
    " $el.value = [...$el.options].find(o => !o.disabled).value } })()"
)


class UnitSelect(forms.Select):
    """The unit list, each option tagged with the line kinds that allow it (the page hides the
    others; the form checks it again on the server)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["x-effect"] = HIDE_OTHER_UNITS

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        if value:
            kinds = [kind for kind, units in KIND_UNITS.items() if value in units]
            option["attrs"]["data-kinds"] = " ".join(kinds)
        return option


class DocumentLineForm(forms.Form):
    """A line of a draft quote or invoice. The VAT rate only matters to a taxable tenant.

    `document`: the draft the line belongs to. The « acompte déjà facturé » line is added by the
    application only, and the cession line of a quote is neither added nor changed to another kind.
    """

    kind = forms.ChoiceField(label=_("Type de ligne"), choices=LineKind.choices, required=False)
    label = forms.CharField(label=_("Désignation"), max_length=255)
    quantity = forms.DecimalField(
        label=_("Quantité"),
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
        initial=1,
    )
    unit = forms.ChoiceField(
        label=_("Unité"),
        choices=LineUnit.choices,
        widget=UnitSelect,
        required=False,
        initial=LineUnit.FLAT,
    )
    unit_price_excl_tax = forms.DecimalField(
        label=_("Prix unitaire HT (€)"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Pour une remise, saisissez le montant à retirer (positif)."),
    )
    vat_rate = forms.DecimalField(
        label=_("TVA (%)"),
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        required=False,
    )
    field_order = ["kind", "label", "quantity", "unit", "unit_price_excl_tax", "vat_rate"]

    def __init__(self, *args, show_vat=False, document=None, line=None, **kwargs):
        super().__init__(*args, **kwargs)
        fixed = line is not None and line.kind in (
            LineKind.DEPOSIT_DEDUCTED,
            *([LineKind.CESSION] if isinstance(document, Quote) else []),
        )
        excluded = {LineKind.DEPOSIT_DEDUCTED}
        if isinstance(document, Quote):
            excluded.add(LineKind.CESSION)
        if fixed:
            excluded.discard(line.kind)
            self.fields["kind"].disabled = True
        self.fields["kind"].choices = [c for c in LineKind.choices if c[0] not in excluded]
        self.fields["kind"].initial = LineKind.OTHER
        self.fields["kind"].widget.attrs["x-model"] = "kind"
        if not show_vat:
            del self.fields["vat_rate"]
        for name in ("quantity", "unit_price_excl_tax", "vat_rate"):
            if name in self.fields:
                self.fields[name].widget.attrs["step"] = "0.01"
                self.fields[name].widget.attrs["inputmode"] = "decimal"

    def clean(self):
        data = super().clean()
        # Left empty (no JavaScript, or an older form): « Autre » and the first unit allowed.
        kind = data["kind"] = data.get("kind") or LineKind.OTHER
        unit = data["unit"] = data.get("unit") or KIND_UNITS[LineKind(kind)][0]
        if unit not in KIND_UNITS[LineKind(kind)]:
            self.add_error("unit", _("Cette unité ne convient pas à ce type de ligne."))
        return data

    @classmethod
    def from_line(cls, line, data=None, show_vat=False):
        price = line.unit_price_excl_tax
        initial = {
            "kind": line.kind,
            "label": line.label,
            "quantity": line.quantity,
            "unit": line.unit,
            "unit_price_excl_tax": abs(price) if line.kind == LineKind.DISCOUNT else price,
            "vat_rate": line.vat_rate,
        }
        return cls(
            data,
            initial=initial,
            show_vat=show_vat,
            document=line.parent,
            line=line,
            prefix=f"line{line.pk}",
        )


class DocumentFilterForm(forms.Form):
    """Filters of the "Documents" tab. Every field is optional; an invalid value is ignored."""

    types = forms.MultipleChoiceField(
        label=_("Types de document"),
        required=False,
        choices=library.DocType.CHOICES,
        widget=MultiSelectDropdown,
    )
    start = forms.DateField(
        label=_("Émis du"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    end = forms.DateField(
        label=_("au"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    shows = forms.ModelMultipleChoiceField(
        label=_("Spectacles"),
        required=False,
        queryset=Show.objects.none(),
        widget=MultiSelectDropdown,
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only this tenant's shows can be chosen: another tenant's id is an invalid value.
        self.fields["shows"].queryset = Show.objects.filter(tenant=tenant).order_by("title")
        self.tenant = tenant

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start"), cleaned.get("end")
        if start and end and start > end:
            self.add_error("end", _("La date de fin doit être après la date de début."))
        return cleaned

    def documents(self):
        self.is_valid()  # fills cleaned_data with the valid fields, drops the invalid ones
        data = self.cleaned_data
        return library.issued_documents(
            self.tenant,
            types=data.get("types", []),
            start=data.get("start"),
            end=data.get("end"),
            shows=data.get("shows", []),
        )
