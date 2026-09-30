from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.views import View
from django.views.generic import TemplateView

from .services import render_pdf


class TenantScopedMixin(LoginRequiredMixin):
    """Restrict a generic view to objects of the current tenant.

    Requires `request.tenant` (set by TenantMiddleware). Views
    using this mixin must never let the tenant be chosen by the
    client: it is always taken from the request.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.tenant is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(tenant=self.request.tenant)

    def form_valid(self, form):
        # DeleteView's form has no `instance` (nothing to set the tenant on).
        if hasattr(form, "instance"):
            form.instance.tenant = self.request.tenant
        return super().form_valid(form)


class SearchListMixin:
    """Filter a ListView with `?q=` (case-insensitive, on `search_fields`).

    A live-search request (HTMX) gets only the results fragment
    (`results_template_name`); a normal request gets the whole page.
    Put it after TenantScopedMixin: the search only narrows an already
    tenant-scoped queryset.
    """

    search_fields = ()
    results_template_name = None

    def get_search_query(self):
        return self.request.GET.get("q", "").strip()

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.get_search_query()
        if query:
            condition = Q()
            for field in self.search_fields:
                condition |= Q(**{f"{field}__icontains": query})
            queryset = queryset.filter(condition)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.get_search_query()
        return context

    def get_template_names(self):
        # A boosted link is a full page navigation, not a live-search request.
        htmx = self.request.htmx
        if htmx and not htmx.boosted and self.results_template_name:
            return [self.results_template_name]
        return super().get_template_names()


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tenant"] = self.request.tenant
        return context


class HelloPdfView(LoginRequiredMixin, View):
    """Disposable view: validates that WeasyPrint works end to end.

    To be removed once a real PDF (e.g. generate_contract_pdf) exists.
    """

    def get(self, request, *args, **kwargs):
        pdf = render_pdf("core/hello_pdf.html")
        return HttpResponse(pdf, content_type="application/pdf")
