"""Roadmap editor: one page, sections edited in place (HTMX, with a no-JavaScript fallback)."""

from dataclasses import dataclass

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.accounts.services import is_tenant_owner
from apps.core.views import TenantScopedMixin, protect_secret_page, wants_fragment
from apps.gigs.models import Gig, GigMember
from apps.tenants.models import Person

from . import documents, services, tour_requests
from .forms import (
    DayMixin,
    LodgingForm,
    MealForm,
    MemberForm,
    NotesForm,
    PlaceContactForm,
    RoadmapDocumentForm,
    SlotForm,
)
from .models import Lodging, Meal, PlaceContact, Roadmap, RoadmapDocument, RoadmapSlot


@dataclass(frozen=True)
class Section:
    model: type
    form: type
    title: str
    add_label: str
    item_template: str
    parent: str  # "roadmap" or "gig": the object the items hang from
    with_contacts: bool = False  # items carry their own list of contacts (PlaceContact)


SECTIONS = {
    "creneaux": Section(
        RoadmapSlot,
        SlotForm,
        _("Programme de la journée"),
        _("Ajouter un créneau"),
        "roadmaps/_item_slot.html",
        "roadmap",
    ),
    "hebergements": Section(
        Lodging,
        LodgingForm,
        _("Hébergement"),
        _("Ajouter un hébergement"),
        "roadmaps/_item_lodging.html",
        "roadmap",
        with_contacts=True,
    ),
    "repas": Section(
        Meal,
        MealForm,
        _("Repas"),
        _("Ajouter un repas"),
        "roadmaps/_item_meal.html",
        "roadmap",
        with_contacts=True,
    ),
    "equipe": Section(
        GigMember,
        MemberForm,
        _("Équipe"),
        _("Ajouter une personne"),
        "roadmaps/_item_member.html",
        "gig",
    ),
}


class RoadmapMixin(TenantScopedMixin):
    """Load the gig of the URL (inside the current tenant) and its roadmap."""

    def load(self, gig_id, section_key=None):
        self.gig = get_object_or_404(
            Gig.objects.select_related("show", "venue"), pk=gig_id, tenant=self.request.tenant
        )
        self.roadmap = services.get_or_create_roadmap(self.gig)
        self.section = None
        if section_key is not None:
            self.section = SECTIONS.get(section_key)
            if self.section is None:
                raise Http404
            self.section_key = section_key

    def parent_of(self, section):
        return self.gig if section.parent == "gig" else self.roadmap

    def section_form(self, section, *args, **kwargs):
        """A form of a section; those with a "Jour" field also need the gig to check the day."""
        if issubclass(section.form, DayMixin):
            kwargs["gig"] = self.gig
        return section.form(*args, **kwargs)

    def get_item(self, pk):
        return get_object_or_404(
            self.section.model,
            pk=pk,
            tenant=self.request.tenant,
            **{self.section.parent: self.parent_of(self.section)},
        )

    def context(self, forms=None, editing=None):
        """`forms` maps a section key to a bound form (add form, or edit form when `editing`)."""
        forms = forms or {}
        sections = []
        for key, section in SECTIONS.items():
            parent = self.parent_of(section)
            items = section.model.objects.filter(
                tenant=self.request.tenant, **{section.parent: parent}
            )
            if section.with_contacts:
                items = items.prefetch_related("contacts")
            if hasattr(section.model, "day"):
                items = services.chronological(items, self.gig)
            editing_pk = editing[1] if editing and editing[0] == key else None
            sections.append(
                {
                    "key": key,
                    "title": section.title,
                    "add_label": section.add_label,
                    "item_template": section.item_template,
                    "items": items,
                    "editing_pk": editing_pk,
                    "edit_form": forms.get(key) if editing_pk else None,
                    "add_form": None
                    if editing_pk
                    else forms.get(key) or self.section_form(section),
                    "with_contacts": section.with_contacts,
                }
            )
        public_path = services.public_path(self.roadmap.token) if self.roadmap.is_published else ""
        return {
            "gig": self.gig,
            "roadmap": self.roadmap,
            "sections": sections,
            "notes_form": forms.get("notes") or NotesForm(instance=self.roadmap),
            "team_choices": services.available_team(self.gig),
            "no_map": services.places_without_map(self.gig, self.roadmap),
            **self.tour_request_context(),
            "documents": self.roadmap.documents.select_related("person"),
            "signed_contract": documents.signed_contract(self.gig),
            "is_owner": is_tenant_owner(self.request.user, self.request.tenant),
            "document_form": forms.get("document") or RoadmapDocumentForm(gig=self.gig),
            "share_url": self.request.build_absolute_uri(public_path) if public_path else "",
        }

    def tour_request_context(self):
        """The "Régie de tournée" block: the last link of this date, and its address if active."""
        tour_request = tour_requests.latest_request(self.gig)
        context = {"tour_request": tour_request, "tour_request_url": ""}
        if tour_request and tour_request.status == tour_request.Status.ACTIVE:
            context["tour_request_url"] = self.request.build_absolute_uri(
                reverse("tour-form-public", args=[tour_request.token])
            )
        return context

    def render_page(self, **kwargs):
        return render(self.request, "roadmaps/editor.html", self.context(**kwargs))

    def render_body_or_page(self, **kwargs):
        """After a failed form or a GET: the body block for HTMX, the whole page otherwise."""
        if wants_fragment(self.request):
            return render(self.request, "roadmaps/_body.html", self.context(**kwargs))
        return self.render_page(**kwargs)

    def done(self):
        """After a successful change: version +1 if shared, then the body (HTMX) or a redirect."""
        services.bump_version(self.roadmap)
        if wants_fragment(self.request):
            return render(self.request, "roadmaps/_body.html", self.context())
        return redirect("roadmaps:editor", gig_id=self.gig.pk)


class EditorView(RoadmapMixin, View):
    def get(self, request, gig_id):
        self.load(gig_id)
        return self.render_page()


class NotesView(RoadmapMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id):
        self.load(gig_id)
        form = NotesForm(request.POST, instance=self.roadmap)
        form.save()  # the only field is optional text: always valid
        return self.done()


class ShareView(RoadmapMixin, View):
    """POST only: turn sharing on (new secret link) or off (link dead for good)."""

    http_method_names = ["post"]

    def post(self, request, gig_id, action):
        self.load(gig_id)
        if action == "activer":
            services.publish(self.roadmap)
            messages.success(request, _("Le partage est activé : copiez le lien ci-dessous."))
        else:
            services.revoke(self.roadmap)
            messages.success(request, _("Le partage est arrêté : l'ancien lien ne marche plus."))
        return redirect("roadmaps:editor", gig_id=self.gig.pk)


class ItemAddView(RoadmapMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id, section):
        self.load(gig_id, section)
        form = self.section_form(self.section, request.POST)
        if not form.is_valid():
            return self.render_body_or_page(forms={section: form})
        item = form.save(commit=False)
        item.tenant = request.tenant
        setattr(item, self.section.parent, self.parent_of(self.section))
        item.save()
        return self.done()


class TeamMemberAddView(RoadmapMixin, View):
    """POST only: put a person of the structure's team on this gig."""

    http_method_names = ["post"]

    def post(self, request, gig_id):
        self.load(gig_id)
        try:
            person_pk = int(request.POST.get("person", ""))
        except ValueError:
            raise Http404 from None
        person = get_object_or_404(Person, pk=person_pk, tenant=request.tenant)
        try:
            services.add_team_member(self.gig, person)
        except services.AlreadyOnTheGig as error:
            messages.error(request, error.args[0])
            return redirect("roadmaps:editor", gig_id=self.gig.pk)
        return self.done()


class ItemEditView(RoadmapMixin, View):
    """GET shows one item as a form, POST saves it."""

    def get(self, request, gig_id, section, pk):
        self.load(gig_id, section)
        item = self.get_item(pk)
        form = self.section_form(self.section, instance=item)
        return self.render_body_or_page(forms={section: form}, editing=(section, item.pk))

    def post(self, request, gig_id, section, pk):
        self.load(gig_id, section)
        item = self.get_item(pk)
        form = self.section_form(self.section, request.POST, instance=item)
        if not form.is_valid():
            return self.render_body_or_page(forms={section: form}, editing=(section, item.pk))
        form.save()
        return self.done()


class PlaceContactAddView(RoadmapMixin, View):
    """POST only: a contact for one lodging or one meal of this roadmap."""

    http_method_names = ["post"]

    def post(self, request, gig_id, section, pk):
        self.load(gig_id, section)
        if not self.section.with_contacts:
            raise Http404
        place = self.get_item(pk)
        form = PlaceContactForm(request.POST)
        if not form.is_valid():
            messages.error(request, _("Indiquez au moins le nom du contact."))
            return redirect("roadmaps:editor", gig_id=self.gig.pk)
        contact = form.save(commit=False)
        contact.tenant = request.tenant
        setattr(contact, "lodging" if section == "hebergements" else "meal", place)
        contact.save()
        return self.done()


class PlaceContactDeleteView(RoadmapMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id, section, pk, contact_pk):
        self.load(gig_id, section)
        if not self.section.with_contacts:
            raise Http404
        place = self.get_item(pk)
        get_object_or_404(
            PlaceContact,
            pk=contact_pk,
            tenant=request.tenant,
            **{"lodging" if section == "hebergements" else "meal": place},
        ).delete()
        return self.done()


class ItemDeleteView(RoadmapMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id, section, pk):
        self.load(gig_id, section)
        self.get_item(pk).delete()
        return self.done()


class PreviewView(RoadmapMixin, View):
    """The page the reader will see, for the signed-in owner: shown beside the editor in a frame.

    Same content as the public link (built from the same whitelist) but reached by the owner's
    session, so it works before sharing is turned on. Only this site may frame it.
    """

    @method_decorator(xframe_options_sameorigin)
    def get(self, request, gig_id):
        self.load(gig_id)
        context = services.public_context(self.roadmap)
        context["pdf_url"] = reverse("roadmaps:pdf", args=[self.gig.pk])
        context["preview"] = True
        return protect_secret_page(render(request, "roadmaps/public.html", context))


class PdfView(RoadmapMixin, View):
    """The roadmap as a PDF, for the signed-in owner (same content as the public link)."""

    def get(self, request, gig_id):
        self.load(gig_id)
        return pdf_response(self.roadmap)


def pdf_response(roadmap):
    response = HttpResponse(services.render_roadmap_pdf(roadmap), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="feuille-de-route-{roadmap.gig.date}.pdf"'
    return response


def _shared_roadmap(token):
    """A roadmap reached by its secret link; unknown token or sharing off = 404 (same answer)."""
    queryset = Roadmap.objects.select_related("gig__show", "gig__venue", "gig__promoter")
    return get_object_or_404(queryset, token=token, is_published=True)


class PublicRoadmapView(View):
    """No account needed, so no TenantScopedMixin: the token alone gives access."""

    def get(self, request, token):
        roadmap = _shared_roadmap(token)
        context = services.public_context(roadmap)
        context["pdf_url"] = reverse("roadmap-public-pdf", args=[token])
        return protect_secret_page(render(request, "roadmaps/public.html", context))


class PublicRoadmapPdfView(View):
    def get(self, request, token):
        return protect_secret_page(pdf_response(_shared_roadmap(token)))


class TourRequestCreateView(RoadmapMixin, View):
    """POST only: make the "Régie de tournée" link to send to the organiser (F-90)."""

    http_method_names = ["post"]

    def post(self, request, gig_id):
        self.load(gig_id)
        tour_requests.create_request(self.gig, request.user)
        messages.success(request, _("Le lien est prêt : copiez-le et envoyez-le à l'organisateur."))
        return redirect("roadmaps:editor", gig_id=self.gig.pk)


class TourRequestRevokeView(RoadmapMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id):
        self.load(gig_id)
        if tour_requests.revoke_request(self.gig):
            messages.success(request, _("Le lien est annulé : il ne fonctionne plus."))
        return redirect("roadmaps:editor", gig_id=self.gig.pk)


class TourRequestReviewView(RoadmapMixin, View):
    """Review what the organiser answered, then apply the chosen groups (or none) to the date."""

    template_name = "roadmaps/tour_review.html"

    def answered(self):
        tour_request = tour_requests.latest_request(self.gig)
        if tour_request is None or tour_request.status != tour_request.Status.ANSWERED:
            return None
        return tour_request

    def nothing_to_review(self):
        messages.info(self.request, _("Il n'y a pas de réponse à vérifier."))
        return redirect("roadmaps:editor", gig_id=self.gig.pk)

    def get(self, request, gig_id):
        self.load(gig_id)
        tour_request = self.answered()
        if tour_request is None:
            return self.nothing_to_review()
        context = {
            "gig": self.gig,
            "groups": tour_requests.review_groups(tour_request),
            "answered_on": tour_request.completed_at,
        }
        return render(request, self.template_name, context)

    def post(self, request, gig_id):
        self.load(gig_id)
        tour_request = self.answered()
        if tour_request is None:
            return self.nothing_to_review()
        try:
            if "ignore" in request.POST:
                tour_requests.ignore_response(tour_request)
                messages.success(request, _("La réponse est écartée : rien n'a été modifié."))
            else:
                chosen = request.POST.getlist("groups")
                if not chosen:
                    messages.error(request, _("Cochez au moins un élément, ou écartez la réponse."))
                    return redirect("roadmaps:tour-request-review", gig_id=self.gig.pk)
                applied = tour_requests.apply_response(tour_request, chosen)
                messages.success(
                    request,
                    _("La feuille de route est à jour (%(n)s élément(s) appliqué(s)).")
                    % {"n": len(applied)},
                )
        except tour_requests.RequestClosed:
            return self.nothing_to_review()
        return redirect("roadmaps:editor", gig_id=self.gig.pk)


class DocumentAddView(RoadmapMixin, View):
    """POST only: put a file on this date for the team (F-91)."""

    http_method_names = ["post"]

    def post(self, request, gig_id):
        self.load(gig_id)
        form = RoadmapDocumentForm(request.POST, request.FILES, gig=self.gig)
        if not form.is_valid():
            return self.render_page(forms={"document": form})
        try:
            documents.add_document(
                self.roadmap,
                title=form.cleaned_data["title"],
                file=form.cleaned_data["file"],
                kind=form.kind,
                person=form.cleaned_data["person"],
                user=request.user,
                slot=form.cleaned_data["slot"],
            )
        except documents.TooManyDocuments:
            messages.error(
                request,
                _("Cette date porte déjà %(n)s documents : supprimez-en un avant d'en ajouter.")
                % {"n": RoadmapDocument.MAX_PER_ROADMAP},
            )
            return redirect("roadmaps:editor", gig_id=self.gig.pk)
        messages.success(request, _("Le document est ajouté."))
        return redirect(f"{reverse('roadmaps:editor', args=[self.gig.pk])}#documents")


class DocumentFileView(RoadmapMixin, View):
    """The owner's own copy of a document, to check what the team will see."""

    def get(self, request, gig_id, pk):
        self.load(gig_id)
        document = get_object_or_404(
            RoadmapDocument, pk=pk, roadmap=self.roadmap, tenant=request.tenant
        )
        return document_response(document)


class DocumentDeleteView(RoadmapMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id, pk):
        self.load(gig_id)
        document = get_object_or_404(
            RoadmapDocument, pk=pk, roadmap=self.roadmap, tenant=request.tenant
        )
        document.delete()
        messages.success(request, _("Le document est supprimé."))
        return redirect(f"{reverse('roadmaps:editor', args=[self.gig.pk])}#documents")


def file_response(file, content_type, title, extension):
    """A stored file shown in the browser (handy on a phone), typed by what we checked at upload.

    `nosniff` stops the browser from guessing another type; the name offered is built from the
    title, never from what was uploaded.
    """
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip()
    response = FileResponse(
        file.open("rb"),
        content_type=content_type,
        as_attachment=False,
        filename=f"{safe_title or 'document'}.{extension}",
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "no-store"
    return response


def document_response(document):
    return file_response(document.file, document.content_type, document.title, document.extension)


class ContractShareView(RoadmapMixin, View):
    """POST only, owner only: show the signed contract to the team, or stop showing it (F-91).

    The contract holds the price of the cession: a plain member cannot decide to show it.
    """

    http_method_names = ["post"]

    def post(self, request, gig_id):
        self.load(gig_id)
        if not is_tenant_owner(request.user, request.tenant):
            raise PermissionDenied
        share = request.POST.get("share") == "1"
        if share and documents.signed_contract(self.gig) is None:
            messages.error(request, _("Le contrat n'est pas encore signé : rien à montrer."))
        else:
            self.roadmap.share_signed_contract = share
            self.roadmap.save(update_fields=["share_signed_contract"])
            messages.success(
                request,
                _("Le contrat signé est visible de l'équipe.")
                if share
                else _("Le contrat signé n'est plus visible de l'équipe."),
            )
        return redirect(f"{reverse('roadmaps:editor', args=[self.gig.pk])}#documents")
