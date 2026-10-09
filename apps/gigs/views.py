import datetime

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.core.views import TenantScopedMixin, wants_fragment
from apps.documents.models import Invoice
from apps.finance import services as finance_services
from apps.tenants.models import Person

from . import services
from .forms import (
    GigDetailsStepForm,
    GigFilterForm,
    GigPromoterStepForm,
    GigShowStepForm,
    GigVenueStepForm,
    PromoterQuickCreateForm,
    ShowQuickCreateForm,
    VenueQuickCreateForm,
)
from .models import Gig

WIZARD_SESSION_KEY = "gig_wizard"

WIZARD_STEP_LABELS = [
    _("Spectacle"),
    _("Organisateur"),
    _("Lieu"),
    _("Détails"),
    _("Récapitulatif"),
]


# URL name of each step, in order: "Précédent" on step N goes to step N-1.
WIZARD_STEP_URLS = [
    "gigs:wizard-show",
    "gigs:wizard-promoter",
    "gigs:wizard-venue",
    "gigs:wizard-details",
    "gigs:wizard-recap",
]


class GigWizardMixin(TenantScopedMixin):
    """Shared session handling for the gig creation wizard steps."""

    def get_wizard_data(self):
        return self.request.session.get(WIZARD_SESSION_KEY, {})

    def update_wizard_data(self, **kwargs):
        data = self.get_wizard_data()
        data.update(kwargs)
        self.request.session[WIZARD_SESSION_KEY] = data

    def require_wizard_data(self, *keys):
        """Redirect to step 1 if a prerequisite step hasn't been completed yet."""
        data = self.get_wizard_data()
        for key in keys:
            if key not in data:
                return redirect("gigs:wizard-show")
        return None

    def wizard_context(self, step, **extra):
        previous_url = reverse(WIZARD_STEP_URLS[step - 2]) if step > 1 else None
        return {
            "step": step,
            "wizard_steps": WIZARD_STEP_LABELS,
            "previous_url": previous_url,
            **extra,
        }


class GigWizardShowStepView(GigWizardMixin, View):
    template_name = "gigs/wizard/step_show.html"

    def get(self, request):
        data = self.get_wizard_data()
        choice_form = GigShowStepForm(tenant=request.tenant, initial={"show": data.get("show_id")})
        create_form = ShowQuickCreateForm()
        return render(request, self.template_name, self._context(choice_form, create_form))

    def post(self, request):
        if request.POST.get("mode") == "new":
            create_form = ShowQuickCreateForm(request.POST)
            choice_form = GigShowStepForm(tenant=request.tenant)
            if create_form.is_valid():
                show = create_form.save(commit=False)
                show.tenant = request.tenant
                show.save()
                self.update_wizard_data(show_id=show.pk)
                return redirect("gigs:wizard-promoter")
        else:
            choice_form = GigShowStepForm(request.POST, tenant=request.tenant)
            create_form = ShowQuickCreateForm()
            if choice_form.is_valid():
                self.update_wizard_data(show_id=choice_form.cleaned_data["show"].pk)
                return redirect("gigs:wizard-promoter")

        return render(request, self.template_name, self._context(choice_form, create_form))

    def _context(self, choice_form, create_form):
        has_choices = choice_form.fields["show"].queryset.exists()
        return self.wizard_context(
            1, choice_form=choice_form, create_form=create_form, has_choices=has_choices
        )


class GigWizardPromoterStepView(GigWizardMixin, View):
    template_name = "gigs/wizard/step_promoter.html"

    def get(self, request):
        redirect_response = self.require_wizard_data("show_id")
        if redirect_response:
            return redirect_response
        data = self.get_wizard_data()
        choice_form = GigPromoterStepForm(
            tenant=request.tenant, initial={"promoter": data.get("promoter_id")}
        )
        create_form = PromoterQuickCreateForm()
        return render(request, self.template_name, self._context(choice_form, create_form))

    def post(self, request):
        redirect_response = self.require_wizard_data("show_id")
        if redirect_response:
            return redirect_response

        if request.POST.get("mode") == "new":
            create_form = PromoterQuickCreateForm(request.POST)
            choice_form = GigPromoterStepForm(tenant=request.tenant)
            if create_form.is_valid():
                promoter = create_form.save(commit=False)
                promoter.tenant = request.tenant
                promoter.save()
                self.update_wizard_data(promoter_id=promoter.pk)
                return redirect("gigs:wizard-venue")
        else:
            choice_form = GigPromoterStepForm(request.POST, tenant=request.tenant)
            create_form = PromoterQuickCreateForm()
            if choice_form.is_valid():
                self.update_wizard_data(promoter_id=choice_form.cleaned_data["promoter"].pk)
                return redirect("gigs:wizard-venue")

        return render(request, self.template_name, self._context(choice_form, create_form))

    def _context(self, choice_form, create_form):
        has_choices = choice_form.fields["promoter"].queryset.exists()
        return self.wizard_context(
            2, choice_form=choice_form, create_form=create_form, has_choices=has_choices
        )


class GigWizardVenueStepView(GigWizardMixin, View):
    template_name = "gigs/wizard/step_venue.html"

    def get(self, request):
        redirect_response = self.require_wizard_data("show_id", "promoter_id")
        if redirect_response:
            return redirect_response
        data = self.get_wizard_data()
        choice_form = GigVenueStepForm(
            tenant=request.tenant, initial={"venue": data.get("venue_id")}
        )
        create_form = VenueQuickCreateForm()
        return render(request, self.template_name, self._context(choice_form, create_form))

    def post(self, request):
        redirect_response = self.require_wizard_data("show_id", "promoter_id")
        if redirect_response:
            return redirect_response

        if request.POST.get("mode") == "new":
            create_form = VenueQuickCreateForm(request.POST)
            choice_form = GigVenueStepForm(tenant=request.tenant)
            if create_form.is_valid():
                venue = create_form.save(commit=False)
                venue.tenant = request.tenant
                venue.save()
                self.update_wizard_data(venue_id=venue.pk)
                return redirect("gigs:wizard-details")
        else:
            choice_form = GigVenueStepForm(request.POST, tenant=request.tenant)
            create_form = VenueQuickCreateForm()
            if choice_form.is_valid():
                self.update_wizard_data(venue_id=choice_form.cleaned_data["venue"].pk)
                return redirect("gigs:wizard-details")

        return render(request, self.template_name, self._context(choice_form, create_form))

    def _context(self, choice_form, create_form):
        has_choices = choice_form.fields["venue"].queryset.exists()
        return self.wizard_context(
            3, choice_form=choice_form, create_form=create_form, has_choices=has_choices
        )


class GigWizardDetailsStepView(GigWizardMixin, View):
    template_name = "gigs/wizard/step_details.html"

    def get(self, request):
        redirect_response = self.require_wizard_data("show_id", "promoter_id", "venue_id")
        if redirect_response:
            return redirect_response
        data = self.get_wizard_data()
        form = GigDetailsStepForm(
            initial={
                "date": data.get("date"),
                "option_expires_on": data.get("option_expires_on"),
                "price": data.get("price"),
                "conditions": data.get("conditions", ""),
            }
        )
        return render(request, self.template_name, self.wizard_context(4, form=form))

    def post(self, request):
        redirect_response = self.require_wizard_data("show_id", "promoter_id", "venue_id")
        if redirect_response:
            return redirect_response

        form = GigDetailsStepForm(request.POST)
        if form.is_valid():
            expires_on = form.cleaned_data["option_expires_on"]
            self.update_wizard_data(
                date=form.cleaned_data["date"].isoformat(),
                option_expires_on=expires_on.isoformat() if expires_on else "",
                price=str(form.cleaned_data["price"]),
                conditions=form.cleaned_data["conditions"],
            )
            return redirect("gigs:wizard-recap")

        return render(request, self.template_name, self.wizard_context(4, form=form))


class GigWizardRecapView(GigWizardMixin, View):
    template_name = "gigs/wizard/recap.html"

    def get(self, request):
        redirect_response = self.require_wizard_data(
            "show_id", "promoter_id", "venue_id", "date", "price"
        )
        if redirect_response:
            return redirect_response

        data = self.get_wizard_data()
        show, promoter, venue = services.get_wizard_related_objects(request.tenant, data)
        context = self.wizard_context(
            5,
            show=show,
            promoter=promoter,
            venue=venue,
            date=datetime.date.fromisoformat(data["date"]),
            option_expires_on=(
                datetime.date.fromisoformat(data["option_expires_on"])
                if data.get("option_expires_on")
                else None
            ),
            price=data["price"],
            conditions=data.get("conditions", ""),
        )
        return render(request, self.template_name, context)

    def post(self, request):
        redirect_response = self.require_wizard_data(
            "show_id", "promoter_id", "venue_id", "date", "price"
        )
        if redirect_response:
            return redirect_response

        data = self.get_wizard_data()
        gig = services.create_gig_from_wizard_data(request.tenant, data)
        del request.session[WIZARD_SESSION_KEY]
        messages.success(request, _("La date a bien été créée."))
        return redirect("gigs:detail", pk=gig.pk)


class GigListView(TenantScopedMixin, ListView):
    """ "Mes dates": upcoming gigs first (soonest on top), then past ones, then cancelled ones."""

    model = Gig
    template_name = "gigs/gig_list.html"
    results_template_name = "gigs/_gig_results.html"

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = GigFilterForm(self.request.GET, tenant=self.request.tenant)
        return self._filter_form

    def get_queryset(self):
        queryset = super().get_queryset().select_related("show", "venue", "promoter")
        return self.get_filter_form().apply(queryset)

    def get_template_names(self):
        if wants_fragment(self.request):
            return [self.results_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        gigs = context["object_list"]
        live, cancelled = (
            gigs.exclude(status=Gig.Status.CANCELLED),
            gigs.filter(status=Gig.Status.CANCELLED),
        )
        context["upcoming_gigs"] = live.filter(date__gte=today).order_by("date")
        context["past_gigs"] = live.filter(date__lt=today).order_by("-date")
        context["cancelled_gigs"] = cancelled.order_by("-date")
        context["filter_form"] = self.get_filter_form()
        context["has_any_gig"] = Gig.objects.filter(tenant=self.request.tenant).exists()
        context["year"] = today.year
        context["year_count"] = services.count_gigs_for_year(self.request.tenant, today.year)
        return context


class GigCalendarView(TenantScopedMixin, TemplateView):
    """Monthly calendar of "Mes dates": a grid of the month plus the list of its gigs."""

    template_name = "gigs/gig_calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month_start = services.parse_month(self.request.GET.get("mois"))
        gigs = (
            Gig.objects.filter(
                tenant=self.request.tenant,
                date__year=month_start.year,
                date__month=month_start.month,
            )
            .select_related("show", "venue", "promoter")
            .order_by("date", "pk")
        )
        previous_month = (month_start - datetime.timedelta(days=1)).replace(day=1)
        next_month = (month_start + datetime.timedelta(days=32)).replace(day=1)
        monday = datetime.date(2024, 1, 1)  # a Monday: gives the localized weekday names
        context.update(
            month_start=month_start,
            weeks=services.build_month_grid(month_start, gigs),
            gigs=gigs,
            weekdays=[date_format(monday + datetime.timedelta(days=i), "D") for i in range(7)],
            previous_month=previous_month
            if previous_month.year in services.CALENDAR_YEARS
            else None,
            next_month=next_month if next_month.year in services.CALENDAR_YEARS else None,
            is_current_month=month_start == timezone.localdate().replace(day=1),
        )
        return context


class GigDetailView(TenantScopedMixin, DetailView):
    model = Gig
    template_name = "gigs/gig_detail.html"

    def get_queryset(self):
        return super().get_queryset().select_related("show", "promoter", "venue")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["balance"] = finance_services.gig_balance(self.object)
        context["crew"] = list(self.object.members.all())
        context["team_total"] = Person.objects.filter(tenant=self.request.tenant).count()
        context["team_on_gig"] = sum(1 for member in context["crew"] if member.person_id)
        return context


class GigTransitionView(TenantScopedMixin, View):
    """Base for the POST-only buttons that change a gig's status."""

    http_method_names = ["post"]
    success_message = ""

    def apply(self, gig):
        raise NotImplementedError

    def get_success_message(self, gig):
        return self.success_message

    def post(self, request, pk):
        gig = get_object_or_404(Gig, pk=pk, tenant=request.tenant)
        try:
            self.apply(gig)
        except services.InvalidTransition as error:
            messages.error(request, error.args[0])
        else:
            messages.success(request, self.get_success_message(gig))
        return redirect("gigs:detail", pk=gig.pk)


class GigConfirmView(GigTransitionView):
    success_message = _("La date est confirmée.")

    def apply(self, gig):
        services.change_status(gig, Gig.Status.CONFIRMED)


class GigReactivateView(GigTransitionView):
    def apply(self, gig):
        services.reactivate_gig(gig)

    def get_success_message(self, gig):
        if gig.status == Gig.Status.SIGNED:
            return _("La date est réactivée : son contrat signé reste valable.")
        return _("La date est réactivée : elle repasse en option.")


class GigDeleteView(TenantScopedMixin, View):
    """Permanent deletion, only for a gig with no legal or financial trace."""

    def _gig(self, request, pk):
        return get_object_or_404(Gig, pk=pk, tenant=request.tenant)

    def get(self, request, pk):
        gig = self._gig(request, pk)
        blockers = services.deletion_blockers(gig)
        return render(request, "gigs/gig_confirm_delete.html", {"gig": gig, "blockers": blockers})

    def post(self, request, pk):
        gig = self._gig(request, pk)
        try:
            services.delete_blank_gig(gig)
        except services.CannotDelete as error:
            messages.error(request, error.args[0])
            return redirect("gigs:detail", pk=gig.pk)
        messages.success(request, _("La date est supprimée."))
        return redirect("gigs:list")


class GigCancelView(GigTransitionView):
    """Cancelling asks for a confirmation first; the gig is kept, never deleted (F-36)."""

    http_method_names = ["get", "post"]
    success_message = _("La date est annulée. Elle reste consultable dans votre historique.")

    def get(self, request, pk):
        gig = get_object_or_404(Gig, pk=pk, tenant=request.tenant)
        open_invoices = (
            Invoice.objects.filter(tenant=request.tenant, gig=gig, status=Invoice.Status.ISSUED)
            .exclude(kind=Invoice.Kind.CREDIT_NOTE)
            .order_by("number")
        )
        return render(
            request,
            "gigs/gig_confirm_cancel.html",
            {"gig": gig, "open_invoices": open_invoices},
        )

    def apply(self, gig):
        services.change_status(gig, Gig.Status.CANCELLED)
