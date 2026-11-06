from urllib.parse import parse_qsl, urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, ProtectedError, Q, Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.accounts.services import is_tenant_owner
from apps.core.views import SearchListMixin, TenantScopedMixin, wants_fragment
from apps.documents.models import Invoice
from apps.finance import bord
from apps.finance.models import Expense
from apps.gigs import services as gig_services
from apps.gigs.models import Gig

from . import social
from .data_export import build_export_zip
from .forms import (
    BordFilterForm,
    DeleteTenantForm,
    OnboardingForm,
    PersonForm,
    TenantProfileForm,
)
from .models import Person
from .services import (
    CannotLeave,
    cancel_deletion,
    create_tenant_for_user,
    deletion_date,
    disable_team_space,
    enable_team_space,
    leave_tenant,
    request_deletion,
)


class OnboardingView(LoginRequiredMixin, FormView):
    """First screen for a brand-new user: creates their Tenant and makes them its owner.

    Redirects to the existing gig wizard afterwards instead of asking for a
    first show/gig here too.
    """

    form_class = OnboardingForm
    template_name = "tenants/onboarding.html"
    success_url = reverse_lazy("gigs:wizard-show")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.tenant is not None:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        create_tenant_for_user(self.request.user, **form.cleaned_data)
        return super().form_valid(form)


class BordView(LoginRequiredMixin, TemplateView):
    """ "Bòrd": the administration page of the tenant, its figures and what needs attention.

    Every member sees it; only the owner gets the buttons that change something.
    """

    template_name = "tenants/bord.html"
    results_template_name = "tenants/_bord_results.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.tenant is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant, today = self.request.tenant, timezone.localdate()
        data = self.request.GET.copy()
        data.setdefault("period", "annee")
        data.setdefault("figure", bord.DEFAULT_FIGURE)
        form = BordFilterForm(data, tenant=tenant)
        context.update(bord.summary(tenant, form.filters(today), today))
        context.update(
            form=form,
            now=timezone.localtime(),
            is_owner=is_tenant_owner(self.request.user, tenant),
            figure_label=bord.FIGURES[context["filters"].figure],
            statuses=bord.STATUSES,
            query_string=self.request.GET.urlencode(),
        )
        return context

    def get_template_names(self):
        if wants_fragment(self.request):
            return [self.results_template_name]
        return super().get_template_names()


class TenantSettingsView(LoginRequiredMixin, UpdateView):
    """ "Informations de la structure": the current tenant's own settings.

    The object is always `request.tenant` (never read from the URL or the form).
    Only the owner can edit; other members see the same page read-only.
    """

    form_class = TenantProfileForm
    template_name = "tenants/settings.html"
    success_url = reverse_lazy("tenants:settings")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.tenant is None:
                raise Http404
            self.is_owner = is_tenant_owner(request.user, request.tenant)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.tenant

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not self.is_owner:
            for field in form.fields.values():
                field.disabled = True
        return form

    def get_context_data(self, **kwargs):
        return super().get_context_data(is_owner=self.is_owner, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.is_owner:
            raise PermissionDenied
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, _("Les informations de votre structure sont enregistrées."))
        return super().form_valid(form)


class DataExportView(TenantScopedMixin, TemplateView):
    """GET explains the export, POST downloads the ZIP of the current tenant's data.

    Open to every member of the tenant (they all see its data anyway).
    """

    template_name = "tenants/data_export.html"

    def post(self, request, *args, **kwargs):
        archive = build_export_zip(
            request.tenant, include_private=is_tenant_owner(request.user, request.tenant)
        )
        filename = f"export-{timezone.localdate()}.zip"
        return FileResponse(archive, as_attachment=True, filename=filename)


class OwnerRequiredMixin(TenantScopedMixin):
    """Only the tenant's owner may go on (a plain member gets a 403)."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.tenant is not None:
            if not is_tenant_owner(request.user, request.tenant):
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class BordStatusView(OwnerRequiredMixin, View):
    """Cancel or restore a date from the Bòrd table (owner only, POST only)."""

    http_method_names = ["post"]

    def post(self, request, pk):
        gig = get_object_or_404(Gig, pk=pk, tenant=request.tenant)
        try:
            if request.POST.get("action") == "reactivate":
                gig_services.reactivate_gig(gig)
                messages.success(request, _("La date est rétablie."))
            else:
                gig_services.change_status(gig, Gig.Status.CANCELLED)
                if (
                    Invoice.objects.filter(
                        tenant=request.tenant, gig=gig, status=Invoice.Status.ISSUED
                    )
                    .exclude(kind=Invoice.Kind.CREDIT_NOTE)
                    .exists()
                ):
                    messages.warning(
                        request,
                        _(
                            "La date est annulée, mais des factures émises restent à solder : "
                            "créez un avoir si elle n'aura pas lieu."
                        ),
                    )
                else:
                    messages.success(request, _("La date est annulée."))
        except gig_services.InvalidTransition as error:
            messages.error(request, error.args[0])
        # Back to the same filters: keep only well-formed key=value pairs of the query string.
        pairs = parse_qsl(request.POST.get("qs", ""), keep_blank_values=False)
        url = reverse("tenants:profile")
        return redirect(f"{url}?{urlencode(pairs)}" if pairs else url)


class DeleteTenantView(OwnerRequiredMixin, FormView):
    form_class = DeleteTenantForm
    template_name = "tenants/delete.html"
    success_url = reverse_lazy("tenants:settings")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return {**kwargs, "user": self.request.user, "tenant": self.request.tenant}

    def form_valid(self, form):
        request_deletion(self.request.tenant)
        messages.success(
            self.request,
            _("La suppression est demandée. Vous pouvez l'annuler jusqu'au %(date)s.")
            % {"date": deletion_date(self.request.tenant).strftime("%d/%m/%Y")},
        )
        return super().form_valid(form)


class CancelDeletionView(OwnerRequiredMixin, View):
    def post(self, request):
        cancel_deletion(request.tenant)
        messages.success(request, _("La suppression est annulée."))
        return redirect("tenants:settings")


class LeaveTenantView(TenantScopedMixin, TemplateView):
    template_name = "tenants/leave.html"

    def post(self, request, *args, **kwargs):
        try:
            leave_tenant(request.user, request.tenant)
        except CannotLeave:
            messages.error(
                request,
                _("Vous êtes le seul propriétaire : supprimez la structure pour la quitter."),
            )
            return redirect("tenants:settings")
        messages.success(request, _("Vous avez quitté la structure."))
        return redirect("home")


class PersonListView(TenantScopedMixin, SearchListMixin, ListView):
    model = Person
    template_name = "tenants/person_list.html"
    results_template_name = "tenants/_person_results.html"
    search_fields = ["first_name", "last_name", "role", "status", "email"]

    def get_queryset(self):
        # How many live dates of this year each person is on (cancelled ones do not count).
        year = timezone.localdate().year
        counted = Q(participations__gig__date__year=year) & ~Q(
            participations__gig__status=Gig.Status.CANCELLED
        )
        return (
            super()
            .get_queryset()
            .annotate(year_gigs=Count("participations__gig", filter=counted, distinct=True))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["year"] = timezone.localdate().year
        context["is_owner"] = is_tenant_owner(self.request.user, self.request.tenant)
        return context


class PersonDetailView(TenantScopedMixin, DetailView):
    model = Person
    template_name = "tenants/person_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_owner"] = is_tenant_owner(self.request.user, self.request.tenant)
        if context["is_owner"] and self.object.access_token:
            context["space_url"] = self.request.build_absolute_uri(
                reverse("team-space", args=[self.object.access_token])
            )
        context["gigs"] = (
            Gig.objects.filter(tenant=self.request.tenant, members__person=self.object)
            .select_related("show", "venue")
            .order_by("-date")
        )
        expenses = Expense.objects.filter(tenant=self.request.tenant, person=self.object)
        context["expenses"] = expenses.select_related("gig__show").order_by("-date", "-id")
        context["owed"] = expenses.filter(reimbursed_on__isnull=True).aggregate(
            total=Sum("amount")
        )["total"]
        if context["is_owner"]:
            context["social_rows"] = social.social_rows(
                self.request.tenant, person=self.object, newest_first=True
            )
        return context


class PersonAccessView(TenantScopedMixin, View):
    """Owner only, POST only: create or revoke the personal link of a team member."""

    http_method_names = ["post"]
    action = ""  # "enable" or "revoke", set in urls.py

    def post(self, request, pk):
        if not is_tenant_owner(request.user, request.tenant):
            raise PermissionDenied
        person = get_object_or_404(Person, pk=pk, tenant=request.tenant)
        if self.action == "enable":
            enable_team_space(person)
            messages.success(request, _("Le lien personnel est créé : copiez-le ci-dessous."))
        else:
            disable_team_space(person)
            messages.success(request, _("Le lien est révoqué : il ne marche plus."))
        return redirect("tenants:person-detail", pk=person.pk)


class PersonFormMixin:
    """Proposes the roles and statuses this structure already uses."""

    model = Person
    form_class = PersonForm
    template_name = "tenants/person_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        kwargs["is_owner"] = is_tenant_owner(self.request.user, self.request.tenant)
        return kwargs

    def get_success_url(self):
        return reverse("tenants:person-detail", args=[self.object.pk])


class PersonCreateView(PersonFormMixin, TenantScopedMixin, CreateView):
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("La personne a été ajoutée à votre équipe."))
        return response


class PersonUpdateView(PersonFormMixin, TenantScopedMixin, UpdateView):
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("La fiche a été modifiée."))
        return response


class PersonDeleteView(TenantScopedMixin, DeleteView):
    model = Person
    template_name = "tenants/person_confirm_delete.html"
    success_url = reverse_lazy("tenants:person-list")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            # Their expenses must keep saying who advanced the money.
            messages.error(
                self.request,
                _("Impossible de supprimer : des dépenses sont enregistrées à son nom."),
            )
            return redirect("tenants:person-detail", pk=self.object.pk)
        messages.success(self.request, _("La fiche est supprimée."))
        return response


@method_decorator(never_cache, name="dispatch")
class SocialView(OwnerRequiredMixin, TemplateView):
    """The "Social" tab (owner only): the people of the team on the dates of a month, with their
    cachets, ready to be handed to whoever does the payroll (F-93)."""

    template_name = "tenants/social.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        first = social.parse_month(self.request.GET.get("mois"), timezone.localdate())
        start, end = social.month_bounds(first)
        tenant = self.request.tenant
        context.update(
            is_owner=True,
            month=first,
            previous_month=social.shift_month(first, -1),
            next_month=social.shift_month(first, 1),
            rows=social.social_rows(tenant, start, end),
            employer_missing=social.employer_missing(tenant),
        )
        return context


@method_decorator(never_cache, name="dispatch")
class SocialExportView(OwnerRequiredMixin, View):
    """The same month as a CSV file (owner only)."""

    def get(self, request):
        first = social.parse_month(request.GET.get("mois"), timezone.localdate())
        start, end = social.month_bounds(first)
        return social.csv_response(request.tenant, start, end)
