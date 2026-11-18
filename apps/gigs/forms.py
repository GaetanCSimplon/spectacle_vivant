from django import forms
from django.db.models import Case, IntegerField, When
from django.utils.translation import gettext_lazy as _

from apps.addressbook.models import Promoter, Venue
from apps.catalog.models import Show
from apps.core.forms import AddressModelForm

from . import services
from .models import Gig, GigMember
from .payment_terms import BalanceTerm, DepositTerm


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
    """The venue of the date: the usual venues of the chosen organiser come first."""

    venue = forms.ModelChoiceField(label=_("Lieu"), queryset=Venue.objects.none())

    def __init__(self, *args, tenant=None, promoter=None, **kwargs):
        super().__init__(*args, **kwargs)
        venues = Venue.objects.filter(tenant=tenant)
        self.usual = set()
        if promoter is not None:
            self.usual = set(venues.filter(promoters=promoter).values_list("pk", flat=True))
            venues = venues.annotate(
                is_usual=Case(
                    When(pk__in=self.usual, then=0), default=1, output_field=IntegerField()
                )
            )
            venues = venues.order_by("is_usual", "name")
        else:
            venues = venues.order_by("name")
        self.fields["venue"].queryset = venues
        self.fields["venue"].label_from_instance = lambda venue: (
            f"{venue.name} ({_('lieu habituel')})" if venue.pk in self.usual else venue.name
        )


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
        fields = ["event_name", "date", "option_expires_on", "price"]
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


class PaymentTermsMixin:
    """The rule of the deposit and of the balance, and the date each one gives (CTR-05).

    A rule other than "Date précise" gives the date: it replaces what was typed. The rules that
    start from the signature have no date until the contract is signed.
    """

    term_fields = (
        "deposit_term",
        "deposit_term_days",
        "deposit_due_on",
        "balance_term",
        "balance_due_on",
    )

    @staticmethod
    def term_widgets():
        return {
            "deposit_due_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "balance_due_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "deposit_term_days": forms.NumberInput(attrs={"min": 0, "max": 365}),
        }

    def _prepare_terms(self):
        # A rule left out of a request keeps its current value (see `clean_terms`).
        self.fields["deposit_term"].required = False
        self.fields["balance_term"].required = False
        self.fields["deposit_term_days"].help_text = _(
            "Seulement pour « Un nombre de jours avant la prestation »."
        )
        self.fields["deposit_due_on"].help_text = _("Seulement pour « Date précise ».")
        self.fields["balance_due_on"].help_text = _("Seulement pour « Date précise ».")

    def clean_terms(self, cleaned):
        gig = self.instance
        deposit_term = cleaned["deposit_term"] = cleaned.get("deposit_term") or gig.deposit_term
        balance_term = cleaned["balance_term"] = cleaned.get("balance_term") or gig.balance_term
        days = cleaned.get("deposit_term_days")
        if deposit_term == DepositTerm.DAYS_BEFORE and days is None:
            self.add_error("deposit_term_days", _("Indiquez le nombre de jours."))
        if deposit_term != DepositTerm.DAYS_BEFORE:
            days = cleaned["deposit_term_days"] = None
        deposit, balance = services.due_dates(gig, deposit_term, days, balance_term)
        if deposit_term != DepositTerm.SPECIFIC:
            cleaned["deposit_due_on"] = deposit
        if balance_term != BalanceTerm.SPECIFIC:
            cleaned["balance_due_on"] = balance
        return cleaned


class TermsForm(PaymentTermsMixin, forms.ModelForm):
    """The payment terms of the future contract (quick edit from the card)."""

    class Meta:
        model = Gig
        fields = [*PaymentTermsMixin.term_fields, "payment_method"]
        widgets = PaymentTermsMixin.term_widgets()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prepare_terms()

    def clean(self):
        return self.clean_terms(super().clean())


class MemberCachetForm(forms.ModelForm):
    """The cachet of one person for this date (owner only): how many, and the gross amount."""

    class Meta:
        model = GigMember
        fields = ["cachet_count", "cachet_amount", "hours"]
        widgets = {
            "cachet_count": forms.NumberInput(attrs={"min": 0, "max": 99}),
            "cachet_amount": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
            "hours": forms.NumberInput(attrs={"min": 0, "max": 999, "step": "0.25"}),
        }
