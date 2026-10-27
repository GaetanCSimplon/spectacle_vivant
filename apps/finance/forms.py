import datetime

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import Person
from apps.tenants.services import RECENT_DAYS, team_space_gigs

from .models import Expense, ExpenseClaim, Payment

MAX_RECEIPT_SIZE = 10 * 1024 * 1024
# The extension proves nothing: the content must start like a PDF, a JPEG or a PNG.
RECEIPT_SIGNATURES = (b"%PDF-", b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")


def validate_receipt(file):
    """A receipt must be a PDF, a JPEG or a PNG of 10 MB at most, judged by its content."""
    if not isinstance(file, UploadedFile):  # unchanged, cleared or empty
        return file
    if file.size > MAX_RECEIPT_SIZE:
        raise forms.ValidationError(_("Le fichier est trop lourd (10 Mo au maximum)."))
    head = file.read(8)
    file.seek(0)
    if not head.startswith(RECEIPT_SIGNATURES):
        raise forms.ValidationError(_("Le justificatif doit être un PDF, un JPEG ou un PNG."))
    return file


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
        return validate_receipt(self.cleaned_data["receipt_file"])


class ExpenseClaimForm(forms.ModelForm):
    """What a team member fills in: one of their own dates, what was spent, an optional receipt."""

    class Meta:
        model = ExpenseClaim
        fields = ["gig", "category", "label", "amount", "date", "receipt_file"]
        widgets = {
            "amount": _money_widget(),
            "date": _date_widget(),
            "receipt_file": forms.ClearableFileInput(attrs={"accept": "image/*,application/pdf"}),
        }
        labels = {"gig": _("Pour quelle date ?")}
        help_texts = {
            "receipt_file": _(
                "Prenez le reçu en photo ou joignez un PDF. Sans reçu, la dépense risque "
                "de ne pas être remboursée."
            ),
        }

    def __init__(self, *args, person=None, today=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.today = today
        # Only the person's own dates, recent or coming (never somebody else's).
        window_start = today - datetime.timedelta(days=RECENT_DAYS)
        self.fields["gig"].queryset = team_space_gigs(person).filter(date__gte=window_start)
        self.fields["gig"].empty_label = None
        self.fields["gig"].label_from_instance = lambda gig: (
            f"{gig.date:%d/%m/%Y} — {gig.show.title}"
        )
        # A team member declares what they spent on a date, not a fee for themselves.
        self.fields["category"].choices = [
            (value, label)
            for value, label in Expense.Category.choices
            if value != Expense.Category.FEES
        ]
        self.fields["receipt_file"].required = False
        self.fields["date"].initial = today  # most of the time, the expense is today's

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date > self.today:
            raise forms.ValidationError(_("Cette date est dans le futur."))
        return date

    def clean_receipt_file(self):
        return validate_receipt(self.cleaned_data["receipt_file"])


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
