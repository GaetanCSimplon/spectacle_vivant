from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import Person

from .models import Expense, Payment

MAX_RECEIPT_SIZE = 10 * 1024 * 1024
# The extension proves nothing: the content must start like a PDF, a JPEG or a PNG.
RECEIPT_SIGNATURES = (b"%PDF-", b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")


def _date_widget():
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


def _money_widget():
    return forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"})


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "date", "method"]
        widgets = {"amount": _money_widget(), "date": _date_widget()}


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["category", "label", "amount", "date", "person", "receipt_file"]
        help_texts = {
            "person": _(
                "Laissez « La structure » si c'est elle qui a payé. Si un membre a avancé "
                "l'argent, la dépense sera à lui rembourser."
            )
        }
        widgets = {
            "amount": _money_widget(),
            "date": _date_widget(),
            "receipt_file": forms.ClearableFileInput(
                attrs={"accept": "application/pdf,image/jpeg,image/png"}
            ),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only the people of this structure can be chosen.
        self.fields["person"].queryset = Person.objects.filter(tenant=tenant)
        self.fields["person"].empty_label = _("La structure")

    def clean_receipt_file(self):
        file = self.cleaned_data["receipt_file"]
        if not isinstance(file, UploadedFile):  # unchanged, cleared or empty
            return file
        if file.size > MAX_RECEIPT_SIZE:
            raise forms.ValidationError(_("Le fichier est trop lourd (10 Mo au maximum)."))
        head = file.read(8)
        file.seek(0)
        if not head.startswith(RECEIPT_SIGNATURES):
            raise forms.ValidationError(_("Le justificatif doit être un PDF, un JPEG ou un PNG."))
        return file


class PeriodForm(forms.Form):
    """The period of an export: both days included."""

    start = forms.DateField(label=_("Du"), widget=_date_widget())
    end = forms.DateField(label=_("Au"), widget=_date_widget())

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start"), cleaned.get("end")
        if start and end and start > end:
            raise forms.ValidationError(_("La date de fin doit être après la date de début."))
        return cleaned
