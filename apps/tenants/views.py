from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView, UpdateView

from apps.accounts.services import is_tenant_owner
from apps.core.views import TenantScopedMixin

from .data_export import build_export_zip
from .forms import OnboardingForm, TenantProfileForm
from .services import create_tenant_for_user


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
