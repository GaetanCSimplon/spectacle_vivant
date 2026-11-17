import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.accounts.services import is_tenant_owner
from apps.addressbook import services as addressbook_services
from apps.addressbook.models import Promoter
from apps.core.views import TenantScopedMixin, wants_fragment
from apps.documents.models import Invoice
from apps.finance import bord
from apps.finance import services as finance_services
from apps.radar import rules as radar_rules
from apps.roadmaps import services as roadmap_services
from apps.roadmaps import tour_requests as roadmap_tour_requests
from apps.tenants.models import Person

from . import checklist, ical, mail, services
from .forms import (
    GigDetailsStepForm,
    GigFilterForm,
    GigPromoterStepForm,
    GigShowStepForm,
    GigVenueStepForm,
    MemberCachetForm,
    PriceForm,
    PromoterQuickCreateForm,
    ShowQuickCreateForm,
    TermsForm,
    VenueQuickCreateForm,
)
from .models import Gig, GigMember

WIZARD_SESSION_KEY = "gig_wizard"
OFFER_FORM_SESSION_KEY = "offer_promoter_form"

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

    def chosen_promoter(self, data):
        """The organiser picked at the previous step (this structure's own, or None)."""
        return Promoter.objects.filter(
            tenant=self.request.tenant, pk=data.get("promoter_id")
        ).first()

    def get(self, request):
        redirect_response = self.require_wizard_data("show_id", "promoter_id")
        if redirect_response:
            return redirect_response
        data = self.get_wizard_data()
        choice_form = GigVenueStepForm(
            tenant=request.tenant,
            promoter=self.chosen_promoter(data),
            initial={"venue": data.get("venue_id")},
        )
        create_form = VenueQuickCreateForm()
        return render(request, self.template_name, self._context(choice_form, create_form))

    def post(self, request):
        redirect_response = self.require_wizard_data("show_id", "promoter_id")
        if redirect_response:
            return redirect_response

        if request.POST.get("mode") == "new":
            create_form = VenueQuickCreateForm(request.POST)
            choice_form = GigVenueStepForm(
                tenant=request.tenant, promoter=self.chosen_promoter(self.get_wizard_data())
            )
            if create_form.is_valid():
                venue = create_form.save(commit=False)
                venue.tenant = request.tenant
                venue.save()
                promoter = self.chosen_promoter(self.get_wizard_data())
                if promoter is not None:  # a new venue is linked to the organiser of this date
                    venue.promoters.add(promoter)
                self.update_wizard_data(venue_id=venue.pk)
                return redirect("gigs:wizard-details")
        else:
            choice_form = GigVenueStepForm(
                request.POST,
                tenant=request.tenant,
                promoter=self.chosen_promoter(self.get_wizard_data()),
            )
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
                "event_name": data.get("event_name", ""),
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
                event_name=form.cleaned_data["event_name"],
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
            event_name=data.get("event_name", ""),
        )
        return render(request, self.template_name, context)

    def post(self, request):
        redirect_response = self.require_wizard_data(
            "show_id", "promoter_id", "venue_id", "date", "price"
        )
        if redirect_response:
            return redirect_response

        data = self.get_wizard_data()
        gig = services.create_gig_from_wizard_data(request.tenant, data, user=request.user)
        del request.session[WIZARD_SESSION_KEY]
        # The date page then offers to send the organiser's form, once (DAT-03).
        request.session[OFFER_FORM_SESSION_KEY] = gig.pk
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
        queryset = self.get_filter_form().apply(queryset)
        return services.with_roadmap_sharing(services.with_locks(queryset))

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
        context["upcoming_gigs"] = radar_rules.attach_findings(
            services.attach_progress(
                live.filter(date__gte=today)
                .select_related("promoter", "venue", "tenant", "contract")
                .prefetch_related("confirmations")
                .order_by("date")
            )
        )
        context["past_gigs"] = services.attach_progress(
            live.filter(date__lt=today).order_by("-date")
        )
        context["cancelled_gigs"] = cancelled.order_by("-date")
        context["filter_form"] = self.get_filter_form()
        context["figures"] = bord.figures_for_gigs(self.request.tenant, gigs)
        context["editable_price"] = True
        context["roadmap_shortcut"] = True
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
        figures = bord.figures_for_gigs(self.request.tenant, gigs)
        # The same cards as the list ("Liste"): progress, payments, roadmap shortcut, price.
        gigs = services.attach_progress(services.with_roadmap_sharing(services.with_locks(gigs)))
        previous_month = (month_start - datetime.timedelta(days=1)).replace(day=1)
        next_month = (month_start + datetime.timedelta(days=32)).replace(day=1)
        monday = datetime.date(2024, 1, 1)  # a Monday: gives the localized weekday names
        context.update(
            month_start=month_start,
            weeks=services.build_month_grid(month_start, gigs),
            gigs=gigs,
            figures=figures,
            editable_price=True,
            roadmap_shortcut=True,
            weekdays=[date_format(monday + datetime.timedelta(days=i), "D") for i in range(7)],
            previous_month=previous_month
            if previous_month.year in services.CALENDAR_YEARS
            else None,
            next_month=next_month if next_month.year in services.CALENDAR_YEARS else None,
            is_current_month=month_start == timezone.localdate().replace(day=1),
        )
        return context


class GigCalendarExportView(TenantScopedMixin, View):
    """The upcoming dates of the structure as an .ics file (cancelled ones are left out)."""

    def get(self, request):
        gigs = (
            Gig.objects.filter(tenant=request.tenant, date__gte=timezone.localdate())
            .select_related("show", "venue", "promoter")
            .order_by("date", "pk")
        )
        content = ical.build(
            gigs, lambda gig: request.build_absolute_uri(reverse("gigs:detail", args=[gig.pk]))
        )
        return ical.response(content, "mes-dates.ics")


class GigIcalView(TenantScopedMixin, View):
    """One date as an .ics file."""

    def get(self, request, pk):
        gig = get_object_or_404(
            Gig.objects.select_related("show", "venue", "promoter"), pk=pk, tenant=request.tenant
        )
        content = ical.build(
            [gig], lambda g: request.build_absolute_uri(reverse("gigs:detail", args=[g.pk]))
        )
        return ical.response(content, f"date-{gig.date:%Y-%m-%d}.ics")


class GigDetailView(TenantScopedMixin, DetailView):
    model = Gig
    template_name = "gigs/gig_detail.html"

    def get_queryset(self):
        return super().get_queryset().select_related("show", "promoter", "venue")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["balance"] = finance_services.gig_balance(self.object)
        if self.object.status != Gig.Status.CANCELLED and self.object.date >= timezone.localdate():
            context["radar"] = radar_rules.for_gig(self.object)
        context["progress"] = services.date_progress(self.object)
        context["overall_percent"] = services.overall_progress(context["progress"])
        context["next_step"] = services.next_step(self.object, context["progress"])
        context["timeline"] = services.gig_timeline(self.object)
        context["contacts"] = services.gig_contacts(self.object)
        context["documents"] = services.gig_documents(self.object)
        invitation = addressbook_services.latest_invitation(self.object.promoter)
        context["invitation"] = invitation
        context["tour_request"] = roadmap_tour_requests.latest_request(self.object)
        if invitation and invitation.status == invitation.Status.ACTIVE:
            context["invitation_url"] = self.request.build_absolute_uri(
                addressbook_services.invitation_path(invitation.token)
            )
            context["mail"] = mail.form_mail(self.object, context["invitation_url"])
        # Offered once, right after the date is created, and only if the organiser has not
        # already answered.
        offered = self.request.session.pop(OFFER_FORM_SESSION_KEY, None)
        context["offer_form"] = offered == self.object.pk and (
            invitation is None or invitation.status != invitation.Status.ANSWERED
        )
        context["price_changes"] = list(self.object.price_changes.all())
        context["crew"] = list(self.object.members.all())
        context["team_total"] = Person.objects.filter(tenant=self.request.tenant).count()
        context["team_on_gig"] = sum(1 for member in context["crew"] if member.person_id)
        # "Équipe de la date" (F-88): the cachets are private (owner only).
        context["is_owner"] = is_tenant_owner(self.request.user, self.request.tenant)
        if context["is_owner"]:
            context["crew_rows"] = [
                (member, MemberCachetForm(instance=member, prefix=f"m{member.pk}"))
                for member in context["crew"]
            ]
        context["cast_missing"] = roadmap_services.cast_not_on_gig(self.object)
        context["team_choices"] = roadmap_services.available_team(self.object)
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


class GigPriceView(TenantScopedMixin, View):
    """Quick edit of the price of a gig, from its card in "Mes dates".

    HTMX swaps the price block of the card; without JavaScript the same view serves a page.
    `?vue=affichage` gives back the plain display (the "Annuler" button).
    """

    def _gig(self, request, pk):
        queryset = services.with_locks(Gig.objects.filter(tenant=request.tenant))
        return get_object_or_404(queryset, pk=pk)

    def _block(self, request, gig, form=None, saved=False):
        context = {"gig": gig, "form": form, "saved": saved, "editable_price": True}
        return render(request, "gigs/_price.html", context)

    def _page(self, request, gig, form):
        context = {
            "gig": gig,
            "form": form,
            "blockers": services.price_blockers(gig),
            "price_changes": list(gig.price_changes.all()),
        }
        return render(request, "gigs/gig_price.html", context)

    def get(self, request, pk):
        gig = self._gig(request, pk)
        form = None if gig.price_locked else PriceForm(initial={"price": gig.price})
        if wants_fragment(request):
            if request.GET.get("vue") == "affichage":
                form = None
            return self._block(request, gig, form)
        return self._page(request, gig, form)

    def post(self, request, pk):
        gig = self._gig(request, pk)
        form = PriceForm(request.POST)
        if form.is_valid():
            try:
                services.change_price(
                    gig, form.cleaned_data["price"], request.user, form.cleaned_data["note"]
                )
            except services.CannotChangePrice as error:
                form.add_error("price", error.args[0])
            else:
                if wants_fragment(request):
                    return self._block(request, self._gig(request, pk), saved=True)
                messages.success(request, _("Le prix est enregistré."))
                return redirect("gigs:detail", pk=gig.pk)
        if wants_fragment(request):
            return self._block(request, gig, form)
        return self._page(request, gig, form)


class GigTermsView(TenantScopedMixin, View):
    """Quick edit of the payment terms of the contract (instalment dates, payment method).

    Same mechanics as `GigPriceView`: HTMX swaps the block of the card, a page serves the
    no-JavaScript case, `?vue=affichage` is the "Annuler" button.
    """

    def _gig(self, request, pk):
        queryset = services.with_locks(Gig.objects.filter(tenant=request.tenant))
        return get_object_or_404(queryset, pk=pk)

    def _block(self, request, gig, form=None, saved=False):
        context = {"gig": gig, "form": form, "saved": saved}
        return render(request, "gigs/_terms.html", context)

    def _page(self, request, gig, form):
        return render(request, "gigs/gig_terms.html", {"gig": gig, "form": form})

    def get(self, request, pk):
        gig = self._gig(request, pk)
        form = None if gig.terms_locked else TermsForm(instance=gig)
        if wants_fragment(request):
            if request.GET.get("vue") == "affichage":
                form = None
            return self._block(request, gig, form)
        return self._page(request, gig, form)

    def post(self, request, pk):
        gig = self._gig(request, pk)
        # A copy, not the gig itself: the rules need its date and its current terms.
        probe = Gig(
            pk=gig.pk,
            tenant=gig.tenant,
            date=gig.date,
            deposit_term=gig.deposit_term,
            balance_term=gig.balance_term,
        )
        form = TermsForm(request.POST, instance=probe)
        if form.is_valid():
            try:
                services.update_terms(gig, **form.cleaned_data)
            except services.CannotChangeTerms as error:
                form.add_error(None, error.args[0])
            else:
                if wants_fragment(request):
                    return self._block(request, self._gig(request, pk), saved=True)
                messages.success(request, _("Les échéances sont enregistrées."))
                return redirect("gigs:detail", pk=gig.pk)
        if wants_fragment(request):
            return self._block(request, gig, form)
        return self._page(request, gig, form)


class GigChecklistMixin(TenantScopedMixin):
    """The contracting checklist of a gig (F-83). Any member of the tenant may read and tick."""

    def _gig(self, request, pk):
        return get_object_or_404(Gig.objects.select_related("show"), pk=pk, tenant=request.tenant)

    def _context(self, gig):
        return {
            "gig": gig,
            "sections": checklist.checklist_sections(gig),
            "updated_at": checklist.last_update(gig),
        }


class GigChecklistView(GigChecklistMixin, View):
    """The checklist as a modal (HTMX) or as a page when JavaScript is off."""

    def get(self, request, pk):
        context = self._context(self._gig(request, pk))
        template = (
            "gigs/_checklist_dialog.html" if wants_fragment(request) else "gigs/gig_checklist.html"
        )
        return render(request, template, context)


class GigChecklistItemView(GigChecklistMixin, View):
    """Tick or untick one box; the others are never touched."""

    http_method_names = ["post"]

    def post(self, request, pk):
        gig = self._gig(request, pk)
        key = request.POST.get("item", "")
        try:
            checklist.set_item(gig, key, request.POST.get("value") == "true", request.user)
        except checklist.InvalidChecklistItem:
            return HttpResponseBadRequest()
        if not wants_fragment(request):
            return redirect("gigs:checklist", pk=gig.pk)
        context = self._context(gig)
        item = next(
            i for section in context["sections"] for i in section["items"] if i["key"] == key
        )
        return render(request, "gigs/_checklist_item_reply.html", {**context, "item": item})


class GigChecklistResetView(GigChecklistMixin, View):
    """Untick every box (the confirmation is asked by the page before posting)."""

    http_method_names = ["post"]

    def post(self, request, pk):
        gig = self._gig(request, pk)
        checklist.reset(gig, request.user)
        if not wants_fragment(request):
            return redirect("gigs:checklist", pk=gig.pk)
        return render(request, "gigs/_checklist_body.html", self._context(gig))


class GigTeamAddView(TenantScopedMixin, View):
    """POST only: put people of the structure's team on this date (F-88).

    `person` adds one person; `cast=1` adds the people of the show's cast who are not there yet.
    The details copied to the date are the same as from the roadmap editor.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        gig = get_object_or_404(Gig.objects.select_related("show"), pk=pk, tenant=request.tenant)
        if request.POST.get("cast"):
            people = list(roadmap_services.cast_not_on_gig(gig))
        else:
            person_id = request.POST.get("person", "")
            people = (
                list(Person.objects.filter(pk=person_id, tenant=request.tenant))
                if person_id.isdigit()
                else []
            )
            if not people:
                messages.error(request, _("Choisissez une personne de votre équipe."))
        for person in people:
            try:
                roadmap_services.add_team_member(gig, person)
            except roadmap_services.AlreadyOnTheGig as error:
                messages.error(request, error.args[0])
        if people:
            roadmap_services.bump_version(roadmap_services.get_or_create_roadmap(gig))
            messages.success(request, _("L'équipe de la date est à jour."))
        return redirect(f"{reverse('gigs:detail', args=[gig.pk])}#equipe")


class GigMemberCachetView(TenantScopedMixin, View):
    """POST only, owner only: the cachet (count and gross amount) of one person for this date."""

    http_method_names = ["post"]

    def post(self, request, pk, member_pk):
        if not is_tenant_owner(request.user, request.tenant):
            raise PermissionDenied
        member = get_object_or_404(
            GigMember, pk=member_pk, gig_id=pk, gig__tenant=request.tenant, tenant=request.tenant
        )
        form = MemberCachetForm(request.POST, instance=member, prefix=f"m{member.pk}")
        if form.is_valid():
            form.save()
            messages.success(
                request, _("Le cachet de %(name)s est enregistré.") % {"name": member.name}
            )
        else:
            messages.error(
                request, _("Le cachet n'a pas pu être enregistré : vérifiez les valeurs.")
            )
        return redirect(f"{reverse('gigs:detail', args=[pk])}#equipe")
