"""Screens of the user for the form a contact or a team member fills in about themselves
(ORG-07): send the link, cancel it, review the answer."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.accounts.services import is_tenant_owner
from apps.core.views import TenantScopedMixin
from apps.tenants.models import Person

from . import info_requests
from .models import Contact, InfoInvitation


def form_block(request, target):
    """What the "Envoyer un formulaire" block of a contact or a team member needs."""
    prefix = "addressbook:contact" if isinstance(target, Contact) else "tenants:person"
    invitation = info_requests.latest_invitation(target)
    context = {
        "info_target": target,
        "info_invitation": invitation,
        "info_create_url": reverse(f"{prefix}-info-invite", args=[target.pk]),
        "info_revoke_url": reverse(f"{prefix}-info-revoke", args=[target.pk]),
        "info_answer_url": reverse(f"{prefix}-info-answer", args=[target.pk]),
    }
    if invitation and invitation.status == InfoInvitation.Status.ACTIVE:
        link = request.build_absolute_uri(info_requests.public_path(invitation.token))
        context["info_url"] = link
        context["mail"] = info_requests.mail(target, link)
    return context


class InfoTargetMixin(TenantScopedMixin):
    kind = ""  # "contact" or "person", set in urls.py

    def get_target(self, request, pk):
        if self.kind == "person":
            # Private data (birth date, social security number...): the owner only.
            if not is_tenant_owner(request.user, request.tenant):
                raise PermissionDenied
            self.target = get_object_or_404(Person, pk=pk, tenant=request.tenant)
        else:
            self.target = get_object_or_404(Contact, pk=pk, tenant=request.tenant)
        return self.target

    def back(self):
        if self.kind == "person":
            return redirect("tenants:person-detail", pk=self.target.pk)
        return redirect("addressbook:contact-update", pk=self.target.pk)


class InfoInviteView(InfoTargetMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        self.get_target(request, pk)
        info_requests.create_invitation(self.target, request.user)
        messages.success(request, _("Le lien est prêt : envoyez-le à la personne."))
        return self.back()


class InfoRevokeView(InfoTargetMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        self.get_target(request, pk)
        if info_requests.revoke_invitation(self.target):
            messages.success(request, _("Le lien est annulé : il ne fonctionne plus."))
        return self.back()


class InfoAnswerView(InfoTargetMixin, View):
    """Review what was answered, then apply it (or part of it) to the fiche."""

    template_name = "addressbook/info_answer.html"

    def load(self, request, pk):
        self.get_target(request, pk)
        invitation = info_requests.latest_invitation(self.target)
        if invitation is None or invitation.status != InfoInvitation.Status.ANSWERED:
            return None
        return invitation

    def nothing_to_review(self):
        messages.info(self.request, _("Il n'y a pas de réponse à vérifier."))
        return self.back()

    def get(self, request, pk):
        invitation = self.load(request, pk)
        if invitation is None:
            return self.nothing_to_review()
        context = {
            "target": self.target,
            "invitation": invitation,
            "rows": info_requests.review_rows(invitation),
            "back_url": self.back().url,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        invitation = self.load(request, pk)
        if invitation is None:
            return self.nothing_to_review()
        try:
            if "ignore" in request.POST:
                info_requests.ignore_response(invitation)
                messages.success(request, _("La réponse est ignorée : rien n'a été modifié."))
            else:
                chosen = info_requests.apply_response(invitation, request.POST.getlist("fields"))
                messages.success(
                    request,
                    _("Les informations choisies sont enregistrées (%(n)s champ(s) mis à jour).")
                    % {"n": len(chosen)},
                )
        except info_requests.InvitationClosed:
            return self.nothing_to_review()
        return self.back()
