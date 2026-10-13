from decimal import Decimal

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.addressbook.forms import PromoterIdentifiersMixin
from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show
from apps.gigs.models import Gig

from .models import Contract

TIME_FORMAT = "%H:%M"


def _time_widget():
    return forms.TimeInput(attrs={"type": "time"}, format=TIME_FORMAT)


class GigCompletionForm(forms.ModelForm):
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
            "signature_deadline_days",
            "payment_method",
            "deposit_percent",
            "deposit_due_on",
            "balance_due_on",
            "meals",
            "lodging",
            "local_transport",
            "other_hospitality",
            "conditions",
            "is_free",
            "ticket_price",
        ]
        widgets = {
            "option_expires_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "conditions": forms.Textarea(attrs={"rows": 4}),
            "deposit_due_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "balance_due_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
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
        self.fields["performances_count"].required = False
        self.fields["copies_count"].required = False
        # An option's validity only matters while the gig is still an option.
        if self.instance.status != Gig.Status.OPTION:
            del self.fields["option_expires_on"]

    def clean_deposit_percent(self):
        # Left empty: keep the current value (30 % for a new gig).
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
        return cleaned_data


class ShowCompletionForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = ["group_name", "sacem_number", "sacem_object_number"]


class VenueCompletionForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["capacity"]


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


class DocumentLineForm(forms.Form):
    """A line of a draft quote or invoice. The VAT rate only matters to a taxable tenant."""

    label = forms.CharField(label=_("Désignation"), max_length=255)
    quantity = forms.DecimalField(
        label=_("Quantité"),
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
        initial=1,
    )
    unit_price_excl_tax = forms.DecimalField(
        label=_("Prix unitaire HT (€)"), max_digits=10, decimal_places=2
    )
    vat_rate = forms.DecimalField(
        label=_("TVA (%)"),
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        required=False,
    )

    def __init__(self, *args, show_vat=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not show_vat:
            del self.fields["vat_rate"]
        for name in ("quantity", "unit_price_excl_tax", "vat_rate"):
            if name in self.fields:
                self.fields[name].widget.attrs["step"] = "0.01"
                self.fields[name].widget.attrs["inputmode"] = "decimal"

    @classmethod
    def from_line(cls, line, data=None, show_vat=False):
        initial = {
            "label": line.label,
            "quantity": line.quantity,
            "unit_price_excl_tax": line.unit_price_excl_tax,
            "vat_rate": line.vat_rate,
        }
        return cls(data, initial=initial, show_vat=show_vat, prefix=f"line{line.pk}")
