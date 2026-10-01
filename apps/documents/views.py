from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.core.views import TenantScopedMixin
from apps.gigs.models import Gig

from . import services
from .forms import (
    ContractCompletionForm,
    GigCompletionForm,
    PromoterCompletionForm,
    ShowCompletionForm,
    VenueCompletionForm,
)
from .models import Contract


class ContractPreviewView(TenantScopedMixin, View):
    """Show the contract as it would be generated now, without storing anything.

    A signed or cancelled gig shows its stored PDF instead of a fresh rendering.
    """

    def get(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        contract = Contract.objects.filter(gig=gig, tenant=request.tenant).first()
        frozen = contract and contract.status == Contract.Status.SIGNED
        if frozen or gig.status == Gig.Status.CANCELLED:
            return stored_contract_response(request, gig, contract)
        pdf_bytes = services.render_contract_pdf(gig, contract)
        return HttpResponse(pdf_bytes, content_type="application/pdf")


class ContractDownloadView(TenantScopedMixin, View):
    def get(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        try:
            contract = services.generate_contract_pdf(gig)
        except services.ContractNotAvailable:
            return no_contract_response(request, gig)
        return FileResponse(
            contract.pdf_file.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"contrat-{gig.pk}.pdf",
        )


def no_contract_response(request, gig):
    messages.error(request, _("Cette date est annulée : aucun contrat n'a été généré."))
    return redirect("gigs:detail", pk=gig.pk)


def stored_contract_response(request, gig, contract):
    if not (contract and contract.pdf_file):
        return no_contract_response(request, gig)
    return FileResponse(contract.pdf_file.open("rb"), content_type="application/pdf")


class ContractCompleteView(TenantScopedMixin, View):
    """One page to fill in every value the contract needs (the "Compléter la date" form)."""

    template_name = "documents/contract_complete.html"

    def load(self, gig_id):
        tenant = self.request.tenant
        self.gig = get_object_or_404(
            Gig.objects.select_related("show", "venue", "promoter"), pk=gig_id, tenant=tenant
        )
        self.contract = Contract.objects.filter(gig=self.gig, tenant=tenant).first() or Contract(
            gig=self.gig, tenant=tenant
        )

    def is_frozen(self):
        return self.contract.status == Contract.Status.SIGNED

    def build_forms(self, data=None):
        return {
            "gig": GigCompletionForm(data, instance=self.gig, prefix="gig"),
            "show": ShowCompletionForm(data, instance=self.gig.show, prefix="show"),
            "venue": VenueCompletionForm(data, instance=self.gig.venue, prefix="venue"),
            "promoter": PromoterCompletionForm(data, instance=self.gig.promoter, prefix="promoter"),
            "contract": ContractCompletionForm(data, instance=self.contract, prefix="contract"),
        }

    def render_page(self, forms):
        context = {"gig": self.gig, "forms": forms}
        return render(self.request, self.template_name, context)

    def frozen_response(self):
        messages.error(
            self.request,
            _("Ce contrat est signé : ses informations ne peuvent plus être modifiées."),
        )
        return redirect("gigs:detail", pk=self.gig.pk)

    def get(self, request, gig_id):
        self.load(gig_id)
        if self.is_frozen():
            return self.frozen_response()
        return self.render_page(self.build_forms())

    def post(self, request, gig_id):
        self.load(gig_id)
        if self.is_frozen():
            return self.frozen_response()

        forms = self.build_forms(request.POST)
        if not all([form.is_valid() for form in forms.values()]):
            messages.error(request, _("Certains champs sont à corriger."))
            return self.render_page(forms)

        with transaction.atomic():
            for form in forms.values():
                form.save()
        messages.success(request, _("Les informations ont bien été enregistrées."))
        return redirect("gigs:detail", pk=self.gig.pk)
