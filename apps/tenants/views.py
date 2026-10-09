from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
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
from apps.core.views import SearchListMixin, TenantScopedMixin
from apps.gigs.models import Gig

from .data_export import build_export_zip
from .forms import DeleteTenantForm, OnboardingForm, PersonForm, TenantProfileForm
from .models import Person
from .services import (
    CannotLeave,
    cancel_deletion,
    create_tenant_for_user,
    deletion_date,
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


class TenantProfileView(LoginRequiredMixin, UpdateView):
    """ "Ma structure": the current tenant's own page.

    The object is always `request.tenant` (never read from the URL or the form).
    Only the owner can edit; other members see the same page read-only.
    """

    form_class = TenantProfileForm
    template_name = "tenants/profile.html"
    success_url = reverse_lazy("tenants:profile")

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
        archive = build_export_zip(request.tenant)
        filename = f"export-{timezone.localdate()}.zip"
        return FileResponse(archive, as_attachment=True, filename=filename)


class OwnerRequiredMixin(TenantScopedMixin):
    """Only the tenant's owner may go on (a plain member gets a 403)."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.tenant is not None:
            if not is_tenant_owner(request.user, request.tenant):
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class DeleteTenantView(OwnerRequiredMixin, FormView):
    form_class = DeleteTenantForm
    template_name = "tenants/delete.html"
    success_url = reverse_lazy("tenants:profile")

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
        return redirect("tenants:profile")


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
            return redirect("tenants:profile")
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
        return context


class PersonDetailView(TenantScopedMixin, DetailView):
    model = Person
    template_name = "tenants/person_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gigs"] = (
            Gig.objects.filter(tenant=self.request.tenant, members__person=self.object)
            .select_related("show", "venue")
            .order_by("-date")
        )
        return context


class PersonFormMixin:
    """Proposes the roles and statuses this structure already uses."""

    model = Person
    form_class = PersonForm
    template_name = "tenants/person_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
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
        response = super().form_valid(form)
        messages.success(self.request, _("La fiche est supprimée."))
        return response
