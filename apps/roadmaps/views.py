"""Roadmap editor: one page, sections edited in place (HTMX, with a no-JavaScript fallback)."""

from dataclasses import dataclass

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.core.views import TenantScopedMixin, wants_fragment
from apps.gigs.models import Gig, GigMember

from . import services
from .forms import LodgingForm, MealForm, MemberForm, NotesForm, SlotForm
from .models import Lodging, Meal, RoadmapSlot


@dataclass(frozen=True)
class Section:
    model: type
    form: type
    title: str
    add_label: str
    item_template: str
    parent: str  # "roadmap" or "gig": the object the items hang from


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
    ),
    "repas": Section(
        Meal, MealForm, _("Repas"), _("Ajouter un repas"), "roadmaps/_item_meal.html", "roadmap"
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
                }
            )
        public_path = services.public_path(self.roadmap.token) if self.roadmap.is_published else ""
        return {
            "gig": self.gig,
            "roadmap": self.roadmap,
            "sections": sections,
            "notes_form": forms.get("notes") or NotesForm(instance=self.roadmap),
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
        """After a successful change: the refreshed body for HTMX, a redirect otherwise."""
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


class ItemDeleteView(RoadmapMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id, section, pk):
        self.load(gig_id, section)
        self.get_item(pk).delete()
        return self.done()
