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
from .models import Contract, ContractVersion


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


class ContractHistoryView(TenantScopedMixin, View):
    """The contract page of a gig: its reference, its versions, and the "generate" button."""

    template_name = "documents/contract_history.html"

    def get(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        contract = Contract.objects.filter(gig=gig, tenant=request.tenant).first()
        versions = contract.versions.select_related("created_by") if contract else []
        context = {
            "gig": gig,
            "contract": contract,
            "versions": versions,
            "can_generate": gig.status != Gig.Status.CANCELLED
            and not (contract and contract.status == Contract.Status.SIGNED),
        }
        return render(request, self.template_name, context)


class ContractGenerateView(TenantScopedMixin, View):
    def post(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        try:
            contract = services.generate_contract_pdf(gig, user=request.user)
        except services.ContractNotAvailable:
            return no_contract_response(request, gig)
        if contract.status == Contract.Status.SIGNED:
            messages.error(request, _("Ce contrat est signé : il ne peut plus être régénéré."))
        else:
            messages.success(request, _("Une nouvelle version du contrat a été générée."))
        return redirect("documents:contract-history", gig_id=gig.pk)


class ContractDownloadView(TenantScopedMixin, View):
    """Download the latest version, or the one given by its number."""

    def get(self, request, gig_id, number=None):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        versions = ContractVersion.objects.filter(
            contract__gig=gig, tenant=request.tenant
        ).select_related("contract")
        if number is None:
            version = versions.first()
        else:
            version = get_object_or_404(versions, number=number)
        if version is None:
            messages.error(request, _("Aucun contrat n'a encore été généré pour cette date."))
            return redirect("documents:contract-history", gig_id=gig.pk)
        return FileResponse(
            version.pdf_file.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"{version.contract.reference}-v{version.number}.pdf",
        )


def no_contract_response(request, gig):
    messages.error(request, _("Cette date est annulée : aucun contrat n'a été généré."))
    return redirect("gigs:detail", pk=gig.pk)


def stored_contract_response(request, gig, contract):
    version = contract.latest_version if contract else None
    if version is None:
        return no_contract_response(request, gig)
    return FileResponse(version.pdf_file.open("rb"), content_type="application/pdf")


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
