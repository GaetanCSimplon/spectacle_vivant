"""The page an organiser reaches from the link they received (F-16). No account needed.

The secret token is the only access right and it gives access to nothing but one form: no
data of the structure is shown, only its name and the name of the organiser. Pages are kept
out of caches and search engines, like the shared roadmap.
"""

from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.core.views import protect_secret_page
from apps.roadmaps import tour_requests

from . import services
from .forms import PromoterPublicForm
from .models import PromoterInvitation

# "no-referrer" would make the browser send `Origin: null` with the form: CSRF check fails.
SAME_ORIGIN = "same-origin"


class PublicPromoterFormView(View):
    template_name = "public/promoter_form.html"

    def get_invitation(self, token):
        invitation = services.find_invitation(token)
        if invitation is None:
            raise Http404  # an unknown token gets the same answer as any unknown page
        return invitation

    def closed(self, request, invitation):
        response = render(
            request, "public/promoter_form_closed.html", {"tenant": invitation.tenant}, status=410
        )
        return protect_secret_page(response, referrer=SAME_ORIGIN)

    def page(self, request, invitation, form):
        context = {
            "form": form,
            "tenant": invitation.tenant,
            "promoter": invitation.promoter,
            "contact_roles": services.CONTACT_ROLES,
            "step": 1 if invitation.gig_id else None,
        }
        return protect_secret_page(render(request, self.template_name, context), SAME_ORIGIN)

    def get(self, request, token):
        invitation = self.get_invitation(token)
        if invitation.status != PromoterInvitation.Status.ACTIVE:
            return self.closed(request, invitation)
        return self.page(request, invitation, PromoterPublicForm())

    def post(self, request, token):
        invitation = self.get_invitation(token)
        if invitation.status != PromoterInvitation.Status.ACTIVE:
            return self.closed(request, invitation)
        form = PromoterPublicForm(request.POST)
        if not form.is_valid():
            return self.page(request, invitation, form)
        try:
            services.submit_response(invitation, form.cleaned_data)
        except services.InvitationClosed:
            return self.closed(request, invitation)
        # Sent from a date: go on to that date's own form (ORG-05), with the same life cycle.
        tour_request = tour_requests.request_for_chain(invitation)
        if tour_request is not None:
            target = reverse("tour-form-public", args=[tour_request.token]) + "?etape=2"
            return protect_secret_page(redirect(target), SAME_ORIGIN)
        return protect_secret_page(redirect("promoter-form-thanks"), SAME_ORIGIN)


class PublicPromoterFormThanksView(View):
    def get(self, request):
        return protect_secret_page(render(request, "public/promoter_form_thanks.html"), SAME_ORIGIN)
