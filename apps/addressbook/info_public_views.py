"""The page a contact or a team member reaches from the link they received (ORG-07).

No account. The secret token gives access to one form: nothing of the structure is shown but
its name. Pages are kept out of caches and search engines, like the organiser's form.
"""

from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View

from apps.core.views import protect_secret_page

from . import info_requests
from .forms import ContactInfoForm, PersonInfoForm
from .models import InfoInvitation

# "no-referrer" would make the browser send `Origin: null` with the form: CSRF check fails.
SAME_ORIGIN = "same-origin"


class PublicInfoFormView(View):
    template_name = "public/info_form.html"

    def get_invitation(self, token):
        invitation = info_requests.find_invitation(token)
        if invitation is None:
            raise Http404  # an unknown token gets the same answer as any unknown page
        return invitation

    def form_class(self, invitation):
        return ContactInfoForm if invitation.contact_id else PersonInfoForm

    def closed(self, request, invitation):
        response = render(
            request, "public/promoter_form_closed.html", {"tenant": invitation.tenant}, status=410
        )
        return protect_secret_page(response, referrer=SAME_ORIGIN)

    def page(self, request, invitation, form):
        context = {
            "form": form,
            "tenant": invitation.tenant,
            "is_person": bool(invitation.person_id),
        }
        return protect_secret_page(render(request, self.template_name, context), SAME_ORIGIN)

    def get(self, request, token):
        invitation = self.get_invitation(token)
        if invitation.status != InfoInvitation.Status.ACTIVE:
            return self.closed(request, invitation)
        return self.page(request, invitation, self.form_class(invitation)())

    def post(self, request, token):
        invitation = self.get_invitation(token)
        if invitation.status != InfoInvitation.Status.ACTIVE:
            return self.closed(request, invitation)
        form = self.form_class(invitation)(request.POST)
        if not form.is_valid():
            return self.page(request, invitation, form)
        try:
            info_requests.submit_response(invitation, form.cleaned_data)
        except info_requests.InvitationClosed:
            return self.closed(request, invitation)
        return protect_secret_page(redirect("promoter-form-thanks"), SAME_ORIGIN)
