"""The personal space of a team member: a secret link, no account (like the shared roadmap).

The token is the access right, so these views have no TenantScopedMixin: they only ever show
what belongs to the person the token was given to, and a dead or unknown token is a 404.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View

from apps.core.views import protect_secret_page
from apps.roadmaps import documents as roadmap_documents
from apps.roadmaps import services as roadmap_services
from apps.roadmaps.models import Roadmap
from apps.roadmaps.views import document_response, file_response, pdf_response

from . import services


class TeamSpaceMixin:
    def person(self, token):
        person = services.person_for_token(token)
        if person is None:
            raise Http404
        return person

    def gig(self, person, gig_id):
        # Only a date of this person: the id of someone else's date is a 404, not a refusal.
        return get_object_or_404(services.team_space_gigs(person), pk=gig_id)


class TeamSpaceView(TeamSpaceMixin, View):
    def get(self, request, token):
        person = self.person(token)
        coming, recent = services.team_space_dates(person, timezone.localdate())
        response = render(
            request,
            "tenants/team_space.html",
            {"person": person, "coming": coming, "recent": recent, "token": token},
        )
        return protect_secret_page(response)


class TeamSpaceGigView(TeamSpaceMixin, View):
    """The roadmap of one of the person's dates, even if the general share link is off."""

    def get(self, request, token, gig_id):
        person = self.person(token)
        gig = self.gig(person, gig_id)
        back_url = reverse("team-space", args=[token])
        roadmap = Roadmap.objects.filter(gig=gig, tenant=person.tenant).first()
        if roadmap is None:  # the owner has not prepared it yet: nothing is created from here
            response = render(
                request,
                "tenants/team_space_no_roadmap.html",
                {"person": person, "gig": gig, "back_url": back_url},
            )
            return protect_secret_page(response)
        context = roadmap_services.public_context(roadmap)
        context["back_url"] = back_url
        context["pdf_url"] = reverse("team-space-pdf", args=[token, gig.pk])
        # Documents are only ever added here, never to the shared public context.
        shared = []
        if roadmap_documents.shared_contract_file(roadmap):
            shared.append(
                {
                    "title": _("Contrat de cession signé"),
                    "kind": "PDF",
                    "url": reverse("team-space-contract", args=[token, gig.pk]),
                }
            )
        context["documents"] = shared + [
            {
                "title": document.title,
                "kind": document.get_content_type_display(),
                "url": reverse("team-space-document", args=[token, gig.pk, document.pk]),
            }
            for document in roadmap_documents.visible_to(roadmap, person)
        ]
        return protect_secret_page(render(request, "roadmaps/public.html", context))


class TeamSpacePdfView(TeamSpaceMixin, View):
    def get(self, request, token, gig_id):
        person = self.person(token)
        gig = self.gig(person, gig_id)
        roadmap = get_object_or_404(Roadmap, gig=gig, tenant=person.tenant)
        return protect_secret_page(pdf_response(roadmap))


class TeamSpaceDocumentView(TeamSpaceMixin, View):
    """A document of one of my dates, meant for me or for the whole team (F-91)."""

    def get(self, request, token, gig_id, pk):
        person = self.person(token)
        gig = self.gig(person, gig_id)
        roadmap = get_object_or_404(Roadmap, gig=gig, tenant=person.tenant)
        document = get_object_or_404(roadmap_documents.visible_to(roadmap, person), pk=pk)
        return protect_secret_page(document_response(document))


class TeamSpaceContractView(TeamSpaceMixin, View):
    """The signed contract of one of my dates, only if the owner chose to show it (F-91)."""

    def get(self, request, token, gig_id):
        person = self.person(token)
        gig = self.gig(person, gig_id)
        roadmap = get_object_or_404(Roadmap, gig=gig, tenant=person.tenant)
        file = roadmap_documents.shared_contract_file(roadmap)
        if not file:
            raise Http404
        return protect_secret_page(
            file_response(file, "application/pdf", _("Contrat de cession signé"), "pdf")
        )
