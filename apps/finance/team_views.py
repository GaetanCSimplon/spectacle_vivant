"""Expenses declared by a team member from their personal space (a secret link, no account).

The token is the access right: these views only ever touch the claims of the person it belongs
to. A claim stays a proposal until the owner accepts it (see `services.accept_claim`).
"""

import os

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View

from apps.core.views import protect_secret_page
from apps.tenants.public_views import TeamSpaceMixin

from . import services
from .forms import ExpenseClaimForm
from .models import ExpenseClaim


class TeamExpensesMixin(TeamSpaceMixin):
    def claim(self, person, pk):
        return get_object_or_404(ExpenseClaim, pk=pk, person=person, tenant=person.tenant)

    def render_page(self, request, person, token, form, editing=None, status=200):
        claims = ExpenseClaim.objects.filter(person=person, tenant=person.tenant).select_related(
            "gig__show", "expense"
        )
        response = render(
            request,
            "finance/team_expenses.html",
            {
                "person": person,
                "token": token,
                "form": form,
                "editing": editing,
                "claims": claims,
                "back_url": reverse("team-space", args=[token]),
            },
            status=status,
        )
        # A page with a form: "same-origin" still sends no Referer elsewhere but keeps CSRF working.
        return protect_secret_page(response, referrer="same-origin")

    def form(self, person, data=None, files=None, instance=None):
        return ExpenseClaimForm(
            data, files, instance=instance, person=person, today=timezone.localdate()
        )


class TeamExpensesView(TeamExpensesMixin, View):
    def get(self, request, token):
        person = self.person(token)
        return self.render_page(request, person, token, self.form(person))

    def post(self, request, token):
        person = self.person(token)
        form = self.form(person, request.POST, request.FILES)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.tenant, claim.person = person.tenant, person
            try:
                services.submit_claim(claim)
            except services.ClaimError as error:
                form.add_error(None, error.args[0])
            else:
                messages.success(
                    request,
                    _("Votre dépense est envoyée : elle sera vérifiée avant d'être comptée."),
                )
                return redirect("team-expenses", token=token)
        return self.render_page(request, person, token, form, status=422)


class TeamExpenseEditView(TeamExpensesMixin, View):
    """Only a proposal still waiting can be corrected."""

    def get(self, request, token, pk):
        person = self.person(token)
        claim = self.claim(person, pk)
        if not claim.is_pending:
            raise Http404
        return self.render_page(request, person, token, self.form(person, instance=claim), claim)

    def post(self, request, token, pk):
        person = self.person(token)
        claim = self.claim(person, pk)
        if not claim.is_pending:
            raise Http404
        previous = claim.receipt_file.name
        form = self.form(person, request.POST, request.FILES, instance=claim)
        if not form.is_valid():
            return self.render_page(request, person, token, form, claim, status=422)
        services.save_claim(form.save(commit=False), previous_receipt=previous)
        messages.success(request, _("Votre proposition est modifiée."))
        return redirect("team-expenses", token=token)


class TeamExpenseDeleteView(TeamExpensesMixin, View):
    http_method_names = ["post"]

    def post(self, request, token, pk):
        person = self.person(token)
        claim = self.claim(person, pk)
        if not claim.is_pending:
            raise Http404
        services.withdraw_claim(claim)
        messages.success(request, _("Votre proposition est retirée."))
        return redirect("team-expenses", token=token)


class TeamExpenseReceiptView(TeamExpensesMixin, View):
    """The receipt of one of my own pending claims (an accepted one belongs to the owner now)."""

    def get(self, request, token, pk):
        person = self.person(token)
        claim = self.claim(person, pk)
        if not claim.receipt_file:
            raise Http404
        response = FileResponse(
            claim.receipt_file.open("rb"),
            as_attachment=True,
            filename=os.path.basename(claim.receipt_file.name),
        )
        return protect_secret_page(response)
