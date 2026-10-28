"""Roadmap editor: one page, sections edited in place (HTMX, with a no-JavaScript fallback)."""

from dataclasses import dataclass

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.core.views import TenantScopedMixin, protect_secret_page, wants_fragment
from apps.gigs.models import Gig, GigMember
from apps.tenants.models import Person

from . import services
from .forms import LodgingForm, MealForm, MemberForm, NotesForm, PlaceContactForm, SlotForm
from .models import Lodging, Meal, PlaceContact, Roadmap, RoadmapSlot


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
                    "add_form": None if editing_pk else forms.get(key) or section.form(),
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
            "share_url": self.request.build_absolute_uri(public_path) if public_path else "",
        }

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
        form = self.section.form(request.POST)
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
        form = self.section.form(instance=item)
        return self.render_body_or_page(forms={section: form}, editing=(section, item.pk))

    def post(self, request, gig_id, section, pk):
        self.load(gig_id, section)
        item = self.get_item(pk)
        form = self.section.form(request.POST, instance=item)
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
    queryset = Roadmap.objects.select_related("gig__show", "gig__venue")
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
