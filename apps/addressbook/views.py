from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.views import SearchListMixin, TenantScopedMixin

from .forms import ContactForm, NewContactForm, PromoterFilterForm, PromoterForm, VenueForm
from .models import Contact, Promoter, Venue


class DetailRedirectMixin:
    """Send a create/update form back to its object's own detail page."""

    detail_url_name = None

    def get_success_url(self):
        return reverse(self.detail_url_name, args=[self.object.pk])


class PromoterListView(TenantScopedMixin, SearchListMixin, ListView):
    model = Promoter
    template_name = "addressbook/promoter_list.html"
    results_template_name = "addressbook/_promoter_results.html"
    search_fields = ["name", "email", "city"]

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = PromoterFilterForm(self.request.GET, tenant=self.request.tenant)
        return self._filter_form

    def get_queryset(self):
        queryset = super().get_queryset().order_by("name")
        return self.get_filter_form().apply(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_filter_form()
        context["filter_form"] = form
        context["filtered"] = bool(context["q"]) or form.is_active
        return context


class PromoterDetailView(TenantScopedMixin, DetailView):
    model = Promoter
    template_name = "addressbook/promoter_detail.html"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("contacts")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gigs"] = self.object.gigs.select_related("show", "venue").order_by("-date")
        return context


class PromoterFormMixin:
    """The promoter form proposes the values this tenant already uses."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs


class PromoterCreateView(PromoterFormMixin, DetailRedirectMixin, TenantScopedMixin, CreateView):
    model = Promoter
    form_class = PromoterForm
    template_name = "addressbook/promoter_form.html"
    detail_url_name = "addressbook:promoter-detail"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("L'organisateur a été créé."))
        return response


class PromoterUpdateView(PromoterFormMixin, DetailRedirectMixin, TenantScopedMixin, UpdateView):
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


class VenueListView(TenantScopedMixin, SearchListMixin, ListView):
    model = Venue
    template_name = "addressbook/venue_list.html"
    results_template_name = "addressbook/_venue_results.html"
    search_fields = ["name", "address", "city", "postal_code"]

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


class ContactListView(TenantScopedMixin, SearchListMixin, ListView):
    model = Contact
    template_name = "addressbook/contact_list.html"
    results_template_name = "addressbook/_contact_results.html"
    search_fields = ["name", "role", "email", "promoter__name", "venue__name"]

    def get_queryset(self):
        return super().get_queryset().select_related("promoter", "venue").order_by("name")


class ContactCreateView(TenantScopedMixin, CreateView):
    """Create a contact from the detail page of its Promoter or Venue.

    The parent comes from the URL and is looked up inside the current tenant,
    so a contact can never be attached to another tenant's organiser or venue.
    """

    model = Contact
    form_class = ContactForm
    template_name = "addressbook/contact_form.html"
    parent_model = None
    parent_kwarg = None
    parent_field = None

    def get_parent(self):
        if not hasattr(self, "_parent"):
            self._parent = get_object_or_404(
                self.parent_model, pk=self.kwargs[self.parent_kwarg], tenant=self.request.tenant
            )
        return self._parent

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Set before validation so Contact.clean() can compare tenants.
        kwargs["instance"] = Contact(
            tenant=self.request.tenant, **{self.parent_field: self.get_parent()}
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent"] = self.get_parent()
        return context

    def get_success_url(self):
        return self.get_parent().get_absolute_url()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le contact a été créé."))
        return response


class ContactQuickCreateView(TenantScopedMixin, CreateView):
    """ "Nouveau contact" from the home page: the form asks which organiser or venue it is for."""

    model = Contact
    form_class = NewContactForm
    template_name = "addressbook/contact_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        # Set before validation so Contact.clean() can compare tenants.
        kwargs["instance"] = Contact(tenant=self.request.tenant)
        return kwargs

    def get_success_url(self):
        return (self.object.promoter or self.object.venue).get_absolute_url()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le contact a été créé."))
        return response


class PromoterContactCreateView(ContactCreateView):
    parent_model = Promoter
    parent_kwarg = "promoter_pk"
    parent_field = "promoter"


class VenueContactCreateView(ContactCreateView):
    parent_model = Venue
    parent_kwarg = "venue_pk"
    parent_field = "venue"


class ContactUpdateView(TenantScopedMixin, UpdateView):
    model = Contact
    form_class = ContactForm
    template_name = "addressbook/contact_form.html"

    def get_queryset(self):
        return super().get_queryset().select_related("promoter", "venue")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent"] = self.object.promoter or self.object.venue
        return context

    def get_success_url(self):
        return (self.object.promoter or self.object.venue).get_absolute_url()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le contact a été modifié."))
        return response


class ContactDeleteView(TenantScopedMixin, DeleteView):
    model = Contact
    template_name = "addressbook/contact_confirm_delete.html"

    def get_queryset(self):
        return super().get_queryset().select_related("promoter", "venue")

    def get_success_url(self):
        return (self.object.promoter or self.object.venue).get_absolute_url()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le contact a été supprimé."))
        return response
