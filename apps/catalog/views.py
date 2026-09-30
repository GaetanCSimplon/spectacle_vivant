from django.contrib import messages
from django.db.models import ProtectedError
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.views import SearchListMixin, TenantScopedMixin

from .forms import ShowForm
from .models import Show


class ShowListView(TenantScopedMixin, SearchListMixin, ListView):
    model = Show
    template_name = "catalog/show_list.html"
    results_template_name = "catalog/_show_results.html"
    search_fields = ["title", "group_name"]

    def get_queryset(self):
        return super().get_queryset().order_by("title")


class ShowDetailView(TenantScopedMixin, DetailView):
    model = Show
    template_name = "catalog/show_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gigs"] = self.object.gigs.select_related("show", "promoter", "venue").order_by(
            "-date"
        )
        return context


class ShowCreateView(TenantScopedMixin, CreateView):
    model = Show
    form_class = ShowForm
    template_name = "catalog/show_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le spectacle a été créé."))
        return response


class ShowUpdateView(TenantScopedMixin, UpdateView):
    model = Show
    form_class = ShowForm
    template_name = "catalog/show_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le spectacle a été modifié."))
        return response


class ShowDeleteView(TenantScopedMixin, DeleteView):
    """RG: a show used by at least one gig cannot be deleted (Gig.show is PROTECT)."""

    model = Show
    template_name = "catalog/show_confirm_delete.html"
    success_url = reverse_lazy("catalog:show-list")

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                _("Impossible de supprimer : ce spectacle est utilisé par au moins une date."),
            )
            return redirect("catalog:show-detail", pk=self.object.pk)


class ShowFileView(TenantScopedMixin, DetailView):
    """Download an uploaded file of a show, only for the tenant that owns it.

    Files are never linked by their /media/ URL. They are sent as attachments
    so an uploaded HTML file can never be displayed (and run) in the browser.
    """

    model = Show
    files = {"fiche-technique": "tech_sheet_file", "rider": "rider_file"}

    def get(self, request, *args, **kwargs):
        show = self.get_object()
        field = self.files.get(kwargs["kind"])
        file = getattr(show, field) if field else None
        if not file:
            raise Http404
        return FileResponse(file.open("rb"), as_attachment=True)
