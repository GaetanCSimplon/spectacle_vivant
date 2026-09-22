from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.views import View
from django.views.generic import TemplateView

from .services import render_pdf


class TenantScopedMixin(LoginRequiredMixin):
    """Restrict a generic view to objects of the current organization.

    Requires `request.organization` (set by OrganizationMiddleware). Views
    using this mixin must never let the organization be chosen by the
    client: it is always taken from the request.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.organization is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(organization=self.request.organization)

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        return super().form_valid(form)


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.request.organization
        return context


class HelloPdfView(LoginRequiredMixin, View):
    """Disposable view: validates that WeasyPrint works end to end.

    To be removed once a real PDF (e.g. generate_contract_pdf) exists.
    """

    def get(self, request, *args, **kwargs):
        pdf = render_pdf("core/hello_pdf.html")
        return HttpResponse(pdf, content_type="application/pdf")
