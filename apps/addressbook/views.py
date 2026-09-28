from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.views import TenantScopedMixin

from .forms import PromoterForm, VenueForm
from .models import Promoter, Venue


class DetailRedirectMixin:
    """Send a create/update form back to its object's own detail page."""

    detail_url_name = None

    def get_success_url(self):
        return reverse(self.detail_url_name, args=[self.object.pk])


class PromoterListView(TenantScopedMixin, ListView):
    model = Promoter
    template_name = "addressbook/promoter_list.html"

    def get_queryset(self):
        return super().get_queryset().order_by("name")


class PromoterDetailView(TenantScopedMixin, DetailView):
    model = Promoter
    template_name = "addressbook/promoter_detail.html"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("contacts")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gigs"] = self.object.gigs.select_related("show", "venue").order_by("-date")
        return context


class PromoterCreateView(DetailRedirectMixin, TenantScopedMixin, CreateView):
    model = Promoter
    form_class = PromoterForm
    template_name = "addressbook/promoter_form.html"
    detail_url_name = "addressbook:promoter-detail"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("L'organisateur a été créé."))
        return response


class PromoterUpdateView(DetailRedirectMixin, TenantScopedMixin, UpdateView):
    model = Promoter
    form_class = PromoterForm
    template_name = "addressbook/promoter_form.html"
    detail_url_name = "addressbook:promoter-detail"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("L'organisateur a été modifié."))
        return response


class PromoterDeleteView(TenantScopedMixin, DeleteView):
    """RG: an organiser used by at least one gig cannot be deleted (Gig.promoter is PROTECT)."""

    model = Promoter
    template_name = "addressbook/promoter_confirm_delete.html"
    success_url = reverse_lazy("addressbook:promoter-list")

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                _("Impossible de supprimer : cet organisateur est utilisé par au moins une date."),
            )
            return redirect("addressbook:promoter-detail", pk=self.object.pk)


class VenueListView(TenantScopedMixin, ListView):
    model = Venue
    template_name = "addressbook/venue_list.html"

    def get_queryset(self):
        return super().get_queryset().order_by("name")


class VenueDetailView(TenantScopedMixin, DetailView):
    model = Venue
    template_name = "addressbook/venue_detail.html"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("contacts")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gigs"] = self.object.gigs.select_related("show", "promoter").order_by("-date")
        return context


class VenueCreateView(DetailRedirectMixin, TenantScopedMixin, CreateView):
    model = Venue
    form_class = VenueForm
    template_name = "addressbook/venue_form.html"
    detail_url_name = "addressbook:venue-detail"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le lieu a été créé."))
        return response


class VenueUpdateView(DetailRedirectMixin, TenantScopedMixin, UpdateView):
    model = Venue
    form_class = VenueForm
    template_name = "addressbook/venue_form.html"
    detail_url_name = "addressbook:venue-detail"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le lieu a été modifié."))
        return response


class VenueDeleteView(TenantScopedMixin, DeleteView):
    """RG: a venue used by at least one gig cannot be deleted (Gig.venue is PROTECT)."""

    model = Venue
    template_name = "addressbook/venue_confirm_delete.html"
    success_url = reverse_lazy("addressbook:venue-list")

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                _("Impossible de supprimer : ce lieu est utilisé par au moins une date."),
            )
            return redirect("addressbook:venue-detail", pk=self.object.pk)
