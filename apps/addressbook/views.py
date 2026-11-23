from django.contrib import messages
from django.db.models import ProtectedError
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponsePermanentRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.views import SearchListMixin, TenantScopedMixin, wants_fragment
from apps.gigs.models import Gig

from . import exports, imports, info_views, services
from .forms import (
    ContactFilterForm,
    ContactForm,
    ImportUploadForm,
    PromoterFilterForm,
    PromoterForm,
    VenueForm,
)
from .models import Contact, Promoter, Venue

# The address book is one page, `/contacts/?type=organisateurs|lieux|personnes`.
PROMOTERS_URL = format_lazy("{}?type=organisateurs", reverse_lazy("addressbook:directory"))
VENUES_URL = format_lazy("{}?type=lieux", reverse_lazy("addressbook:directory"))
CONTACTS_URL = format_lazy("{}?type=personnes", reverse_lazy("addressbook:directory"))


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
            self._filter_form = PromoterFilterForm(self.request.GET)
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
        return super().get_queryset().prefetch_related("contacts", "venues")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["attachable_contacts"] = Contact.objects.filter(tenant=self.request.tenant).exclude(
            promoters=self.object
        )
        context["gigs"] = self.object.gigs.select_related("show", "venue").order_by("-date")
        invitation = services.latest_invitation(self.object)
        context["invitation"] = invitation
        if invitation and invitation.status == invitation.Status.ACTIVE:
            context["invitation_url"] = self.request.build_absolute_uri(
                services.invitation_path(invitation.token)
            )
        return context


class PromoterInviteView(TenantScopedMixin, View):
    """POST only: create the link the organiser will use to fill in their details."""

    http_method_names = ["post"]

    def post(self, request, pk):
        promoter = get_object_or_404(Promoter, pk=pk, tenant=request.tenant)
        # Asked from a date of this organiser: the form then goes on to that date's own form,
        # and we come back to that date. Any other value (or a date of another structure or
        # organiser) is ignored.
        gig_id = request.POST.get("gig", "")
        gig = (
            Gig.objects.filter(pk=gig_id, tenant=request.tenant, promoter=promoter).first()
            if gig_id.isdigit()
            else None
        )
        services.create_invitation(promoter, request.user, gig=gig)
        messages.success(request, _("Le lien est prêt : copiez-le et envoyez-le à l'organisateur."))
        if gig is not None:
            if request.POST.get("back") == "detail":
                return redirect("gigs:detail", pk=gig.pk)
            return redirect("documents:contract-complete", gig_id=gig.pk)
        return redirect("addressbook:promoter-detail", pk=promoter.pk)


class PromoterInviteRevokeView(TenantScopedMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        promoter = get_object_or_404(Promoter, pk=pk, tenant=request.tenant)
        if services.revoke_invitation(promoter):
            messages.success(request, _("Le lien est annulé : il ne fonctionne plus."))
        return redirect("addressbook:promoter-detail", pk=promoter.pk)


class PromoterAnswerView(TenantScopedMixin, View):
    """Review what the organiser answered, then apply it (or part of it) to their card."""

    template_name = "addressbook/promoter_answer.html"

    def load(self, request, pk):
        self.promoter = get_object_or_404(Promoter, pk=pk, tenant=request.tenant)
        invitation = services.latest_invitation(self.promoter)
        if invitation is None or invitation.status != invitation.Status.ANSWERED:
            return None
        return invitation

    def nothing_to_review(self):
        messages.info(self.request, _("Il n'y a pas de réponse à vérifier."))
        return redirect("addressbook:promoter-detail", pk=self.promoter.pk)

    def get(self, request, pk):
        invitation = self.load(request, pk)
        if invitation is None:
            return self.nothing_to_review()
        return render(
            request,
            self.template_name,
            {
                "promoter": self.promoter,
                "invitation": invitation,
                "rows": services.review_rows(invitation),
                "contacts": services.answer_contacts(invitation),
            },
        )

    def post(self, request, pk):
        invitation = self.load(request, pk)
        if invitation is None:
            return self.nothing_to_review()
        try:
            if "ignore" in request.POST:
                services.ignore_response(invitation)
                messages.success(request, _("La réponse est ignorée : rien n'a été modifié."))
            else:
                indexes = [
                    int(value) for value in request.POST.getlist("contacts") if value.isdigit()
                ]
                chosen = services.apply_response(
                    invitation, request.POST.getlist("fields"), indexes
                )
                messages.success(
                    request,
                    _("Les informations choisies sont enregistrées (%(n)s champ(s) mis à jour).")
                    % {"n": len(chosen)},
                )
        except services.InvitationClosed:
            return self.nothing_to_review()
        return redirect("addressbook:promoter-detail", pk=self.promoter.pk)


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
    success_url = PROMOTERS_URL

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
        return super().get_queryset().prefetch_related("contacts", "promoters")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["attachable_contacts"] = Contact.objects.filter(tenant=self.request.tenant).exclude(
            venues=self.object
        )
        context["gigs"] = self.object.gigs.select_related("show", "promoter").order_by("-date")
        return context


class TenantFormKwargsMixin:
    """The form only offers this structure's own organisers."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs


class VenueCreateView(TenantFormKwargsMixin, DetailRedirectMixin, TenantScopedMixin, CreateView):
    model = Venue
    form_class = VenueForm
    template_name = "addressbook/venue_form.html"
    detail_url_name = "addressbook:venue-detail"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le lieu a été créé."))
        return response


class VenueUpdateView(TenantFormKwargsMixin, DetailRedirectMixin, TenantScopedMixin, UpdateView):
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
    success_url = VENUES_URL

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
    """The address book: every contact, with the organisers and venues it works for."""

    model = Contact
    template_name = "addressbook/contact_list.html"
    results_template_name = "addressbook/_contact_results.html"
    search_fields = ["name", "role", "email", "promoters__name", "venues__name"]

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = ContactFilterForm(self.request.GET)
        return self._filter_form

    def get_queryset(self):
        queryset = (
            super().get_queryset().prefetch_related("promoters__contacts", "venues__contacts")
        )
        return self.get_filter_form().apply(queryset).distinct().order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.get_filter_form()
        form = self.get_filter_form()
        context["filtered"] = bool(context["q"] or (form.is_valid() and form.cleaned_data["link"]))
        context["has_any_contact"] = Contact.objects.filter(tenant=self.request.tenant).exists()
        return context


class ContactFormMixin:
    """The form only offers this structure's own organisers and venues."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs


class ContactQuickCreateView(ContactFormMixin, TenantScopedMixin, CreateView):
    """ "Nouveau contact" from the address book or the home page: a person of the directory,
    with the organisers and venues it works for (none is fine: "Sans rattachement")."""

    model = Contact
    form_class = ContactForm
    template_name = "addressbook/contact_form.html"
    success_url = CONTACTS_URL

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le contact a été créé."))
        return response


class ContactCreateView(ContactQuickCreateView):
    """Create a contact from the page of an organiser or a venue, which is pre-selected.

    The parent comes from the URL and is looked up inside the current tenant. The person can
    still tick other organisers and venues.
    """

    parent_model = None
    parent_kwarg = None
    parent_field = None  # "promoters" or "venues": the field that holds the parent

    def get_parent(self):
        if not hasattr(self, "_parent"):
            self._parent = get_object_or_404(
                self.parent_model, pk=self.kwargs[self.parent_kwarg], tenant=self.request.tenant
            )
        return self._parent

    def get_initial(self):
        return {**super().get_initial(), self.parent_field: [self.get_parent()]}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent"] = self.get_parent()
        return context

    def get_success_url(self):
        return self.get_parent().get_absolute_url()


class PromoterContactCreateView(ContactCreateView):
    parent_model = Promoter
    parent_kwarg = "promoter_pk"
    parent_field = "promoters"


class VenueContactCreateView(ContactCreateView):
    parent_model = Venue
    parent_kwarg = "venue_pk"
    parent_field = "venues"


class ContactUpdateView(ContactFormMixin, TenantScopedMixin, UpdateView):
    model = Contact
    form_class = ContactForm
    template_name = "addressbook/contact_form.html"
    success_url = CONTACTS_URL

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le contact a été modifié."))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(info_views.form_block(self.request, self.object))
        return context


class ContactDeleteView(TenantScopedMixin, DeleteView):
    model = Contact
    template_name = "addressbook/contact_confirm_delete.html"
    success_url = CONTACTS_URL

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Le contact a été supprimé."))
        return response


class PromoterFollowUpView(TenantScopedMixin, View):
    """POST only: change the follow-up (the "statut") of an organiser from the list or its page.

    HTMX gets the menu back (`#follow-up-<id>`); without JavaScript the page is simply reloaded.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        promoter = get_object_or_404(Promoter, pk=pk, tenant=request.tenant)
        value = request.POST.get("follow_up", "")
        if value not in {key for key, _label in Promoter.FollowUp.choices} | {""}:
            return HttpResponseBadRequest()
        promoter.follow_up = value
        promoter.save(update_fields=["follow_up"])
        if wants_fragment(request):
            return render(request, "addressbook/_follow_up_menu.html", {"promoter": promoter})
        messages.success(request, _("Le statut est enregistré."))
        return redirect(request.POST.get("next") or PROMOTERS_URL)


class ContactLinkView(TenantScopedMixin, View):
    """POST only: attach an existing contact of the directory to an organiser or a venue, or
    take it off (the contact itself is never deleted here)."""

    http_method_names = ["post"]
    parent_model = None
    parent_field = None  # "promoters" or "venues": the contact's field that holds the parent
    action = ""  # "attach" or "detach", set in urls.py

    def post(self, request, pk, contact_pk=None):
        parent = get_object_or_404(self.parent_model, pk=pk, tenant=request.tenant)
        if self.action == "attach":
            contact_pk = request.POST.get("contact", "")
            if not contact_pk.isdigit():
                messages.error(request, _("Choisissez un contact dans la liste."))
                return redirect(parent)
        contact = get_object_or_404(Contact, pk=contact_pk, tenant=request.tenant)
        links = getattr(contact, self.parent_field)
        if self.action == "attach":
            links.add(parent)
            messages.success(
                request,
                _("« %(name)s » est rattaché à %(parent)s.")
                % {"name": contact.name, "parent": parent},
            )
        else:
            links.remove(parent)
            messages.success(
                request,
                _("« %(name)s » n'est plus rattaché à %(parent)s (il reste dans l'annuaire).")
                % {"name": contact.name, "parent": parent},
            )
        return redirect(parent)


class PromoterContactLinkView(ContactLinkView):
    parent_model = Promoter
    parent_field = "promoters"


class VenueContactLinkView(ContactLinkView):
    parent_model = Venue
    parent_field = "venues"


class ExportMixin:
    """Send the list a user is looking at (same search and filters) as a CSV file.

    The export views are the list views themselves, so the tenant scope and the filters are the
    ones of the screen: no second copy of that logic.
    """

    export_kind = None

    def get(self, request, *args, **kwargs):
        return exports.csv_response(self.export_kind, self.get_queryset())


class PromoterExportView(ExportMixin, PromoterListView):
    export_kind = "organisateurs"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("contacts")


class VenueExportView(ExportMixin, VenueListView):
    export_kind = "lieux"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("promoters")


class ContactExportView(ExportMixin, ContactListView):
    export_kind = "contacts"


IMPORT_SESSION_KEY = "addressbook_import"
IMPORT_LISTS = {
    "contacts": CONTACTS_URL,
    "lieux": VENUES_URL,
    "organisateurs": PROMOTERS_URL,
}


class ImportView(TenantScopedMixin, View):
    """Steps 1 and 2 of the CSV import: the file, then what it would do (nothing is saved)."""

    def get(self, request):
        kind = request.GET.get("type")
        form = ImportUploadForm(initial={"kind": kind if kind in imports.MODELS else "contacts"})
        return render(request, "addressbook/import.html", {"form": form})

    def post(self, request):
        form = ImportUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "addressbook/import.html", {"form": form})
        kind, upload = form.cleaned_data["kind"], form.cleaned_data["file"]
        try:
            raw_rows, ignored = imports.read_file(upload, kind)
        except imports.ImportFileError as error:
            form.add_error("file", str(error))
            return render(request, "addressbook/import.html", {"form": form})
        rows = imports.analyse(request.tenant, kind, raw_rows)
        # The file is kept in the session (not in the database) until the user confirms.
        request.session[IMPORT_SESSION_KEY] = {"kind": kind, "rows": raw_rows}
        context = {
            "kind": kind,
            "rows": rows,
            "counts": imports.summary(rows),
            "ignored_columns": ignored,
            "problems": [row for row in rows if row.errors or row.warnings],
        }
        return render(request, "addressbook/import_preview.html", context)


class ImportConfirmView(TenantScopedMixin, View):
    """Step 3: do the import the user has just looked at."""

    http_method_names = ["post"]

    def post(self, request):
        saved = request.session.pop(IMPORT_SESSION_KEY, None)
        if not saved or saved.get("kind") not in imports.MODELS:
            messages.error(request, _("Ce fichier n'est plus là : envoyez-le de nouveau."))
            return redirect("addressbook:import")
        update = request.POST.get("duplicates") == "update"
        counts = imports.apply(request.tenant, saved["kind"], saved["rows"], update=update)
        messages.success(
            request,
            _(
                "Import terminé : %(created)s créé(s), %(updated)s mis à jour, "
                "%(ignored)s ignoré(s)."
            )
            % counts,
        )
        return redirect(IMPORT_LISTS[saved["kind"]])


class ImportTemplateView(TenantScopedMixin, View):
    """An empty file with the right columns, to fill in and send back."""

    def get(self, request, kind):
        if kind not in exports.EXPORTS:
            raise Http404
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="modele-{kind}.csv"'
        response.write(exports.BOM + ";".join(exports.EXPORTS[kind][0]) + "\r\n")
        return response


class DirectoryView(View):
    """`/contacts/?type=organisateurs|lieux|personnes`: the three existing lists under one page.

    Each list keeps its own view (tenant scope, search and filters); this one only picks which.
    """

    lists = {
        "organisateurs": PromoterListView,
        "lieux": VenueListView,
        "personnes": ContactListView,
    }

    def get(self, request):
        view = self.lists.get(request.GET.get("type"), PromoterListView)
        return view.as_view()(request)


class DirectoryRedirectView(View):
    """The former list addresses (`/organisateurs/`, `/lieux/`) lead to the directory (301)."""

    kind = None

    def get(self, request):
        params = request.GET.copy()
        params["type"] = self.kind
        return HttpResponsePermanentRedirect(
            f"{reverse('addressbook:directory')}?{params.urlencode()}"
        )
