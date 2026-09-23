import datetime

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.core.views import TenantScopedMixin

from . import services
from .forms import (
    GigDetailsStepForm,
    GigPromoterStepForm,
    GigShowStepForm,
    GigVenueStepForm,
    PromoterQuickCreateForm,
    ShowQuickCreateForm,
    VenueQuickCreateForm,
)

WIZARD_SESSION_KEY = "gig_wizard"

WIZARD_STEP_LABELS = [
    _("Spectacle"),
    _("Organisateur"),
    _("Lieu"),
    _("Détails"),
    _("Récapitulatif"),
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
        return {"step": step, "wizard_steps": WIZARD_STEP_LABELS, **extra}


class GigWizardShowStepView(GigWizardMixin, View):
    template_name = "gigs/wizard/step_show.html"

    def get(self, request):
        data = self.get_wizard_data()
        choice_form = GigShowStepForm(
            organization=request.organization, initial={"show": data.get("show_id")}
        )
        create_form = ShowQuickCreateForm()
        return render(request, self.template_name, self._context(choice_form, create_form))

    def post(self, request):
        if request.POST.get("mode") == "new":
            create_form = ShowQuickCreateForm(request.POST)
            choice_form = GigShowStepForm(organization=request.organization)
            if create_form.is_valid():
                show = create_form.save(commit=False)
                show.organization = request.organization
                show.save()
                self.update_wizard_data(show_id=show.pk)
                return redirect("gigs:wizard-promoter")
        else:
            choice_form = GigShowStepForm(request.POST, organization=request.organization)
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
            organization=request.organization, initial={"promoter": data.get("promoter_id")}
        )
        create_form = PromoterQuickCreateForm()
        return render(request, self.template_name, self._context(choice_form, create_form))

    def post(self, request):
        redirect_response = self.require_wizard_data("show_id")
        if redirect_response:
            return redirect_response

        if request.POST.get("mode") == "new":
            create_form = PromoterQuickCreateForm(request.POST)
            choice_form = GigPromoterStepForm(organization=request.organization)
            if create_form.is_valid():
                promoter = create_form.save(commit=False)
                promoter.organization = request.organization
                promoter.save()
                self.update_wizard_data(promoter_id=promoter.pk)
                return redirect("gigs:wizard-venue")
        else:
            choice_form = GigPromoterStepForm(request.POST, organization=request.organization)
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
            organization=request.organization, initial={"venue": data.get("venue_id")}
        )
        create_form = VenueQuickCreateForm()
        return render(request, self.template_name, self._context(choice_form, create_form))

    def post(self, request):
        redirect_response = self.require_wizard_data("show_id", "promoter_id")
        if redirect_response:
            return redirect_response

        if request.POST.get("mode") == "new":
            create_form = VenueQuickCreateForm(request.POST)
            choice_form = GigVenueStepForm(organization=request.organization)
            if create_form.is_valid():
                venue = create_form.save(commit=False)
                venue.organization = request.organization
                venue.save()
                self.update_wizard_data(venue_id=venue.pk)
                return redirect("gigs:wizard-details")
        else:
            choice_form = GigVenueStepForm(request.POST, organization=request.organization)
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
            self.update_wizard_data(
                date=form.cleaned_data["date"].isoformat(),
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
        show, promoter, venue = services.get_wizard_related_objects(request.organization, data)
        context = self.wizard_context(
            5,
            show=show,
            promoter=promoter,
            venue=venue,
            date=datetime.date.fromisoformat(data["date"]),
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
        services.create_gig_from_wizard_data(request.organization, data)
        del request.session[WIZARD_SESSION_KEY]
        messages.success(request, _("La date a bien été créée."))
        return redirect(reverse("home"))
