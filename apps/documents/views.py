from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.addressbook import services as addressbook_services
from apps.core.views import TenantScopedMixin, wants_fragment
from apps.gigs.models import Gig

from . import services
from .forms import (
    ContractCompletionForm,
    DocumentFilterForm,
    GigCompletionForm,
    PromoterCompletionForm,
    ShowCompletionForm,
    SignedPdfForm,
    VenueCompletionForm,
)
from .models import Contract, ContractVersion


def requested_template(request, data):
    """The wording picked in the form: None if absent, an error message if not offered."""
    value = data.get("template")
    if not value:
        return None, None
    if value not in dict(services.available_contract_templates()):
        return None, _("Ce modèle de contrat n'existe pas.")
    return value, None


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
        template, error = requested_template(request, request.GET)
        if error:
            messages.error(request, error)
            return redirect("documents:contract-history", gig_id=gig.pk)
        pdf_bytes = services.render_contract_pdf(gig, contract, template)
        return HttpResponse(pdf_bytes, content_type="application/pdf")


class ContractHistoryView(TenantScopedMixin, View):
    """The contract page of a gig: its reference, its versions, and the "generate" button."""

    template_name = "documents/contract_history.html"

    def get(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        contract = Contract.objects.filter(gig=gig, tenant=request.tenant).first()
        versions = contract.versions.select_related("created_by") if contract else []
        signed = bool(contract and contract.status == Contract.Status.SIGNED)
        context = {
            "gig": gig,
            "contract": contract,
            "versions": versions,
            "can_generate": gig.status != Gig.Status.CANCELLED and not signed,
            "can_sign": gig.status == Gig.Status.CONFIRMED
            and bool(contract and contract.latest_version)
            and not signed,
            "can_mark_sent": bool(contract and contract.latest_version) and not signed,
            "can_add_signed_pdf": signed and not contract.signed_pdf,
            "signed_pdf_form": SignedPdfForm(),
            "template_choices": services.available_contract_templates(),
            "current_template": contract.template
            if contract
            else services.DEFAULT_CONTRACT_TEMPLATE,
        }
        return render(request, self.template_name, context)


class ContractSignView(TenantScopedMixin, View):
    """Confirmation page, then freeze the latest version as the signed contract."""

    template_name = "documents/contract_sign.html"

    def load(self, gig_id):
        self.gig = get_object_or_404(Gig, pk=gig_id, tenant=self.request.tenant)
        self.contract = Contract.objects.filter(gig=self.gig, tenant=self.request.tenant).first()

    def render_page(self, form):
        context = {"gig": self.gig, "contract": self.contract, "form": form}
        return render(self.request, self.template_name, context)

    def refuse(self, error):
        messages.error(self.request, error)
        return redirect("documents:contract-history", gig_id=self.gig.pk)

    def get(self, request, gig_id):
        self.load(gig_id)
        if not (self.contract and self.contract.latest_version):
            return self.refuse(_("Générez d'abord le contrat avant de le marquer signé."))
        if self.contract.status == Contract.Status.SIGNED:
            return self.refuse(_("Ce contrat est déjà signé."))
        return self.render_page(SignedPdfForm())

    def post(self, request, gig_id):
        self.load(gig_id)
        form = SignedPdfForm(request.POST, request.FILES)
        if not form.is_valid():
            return (
                self.render_page(form) if self.contract else self.refuse(_("Contrat introuvable."))
            )
        try:
            services.mark_contract_signed(self.gig, form.cleaned_data["signed_pdf"])
        except services.ContractSigningError as error:
            return self.refuse(error.args[0])
        messages.success(
            request,
            _("Le contrat est marqué signé : son PDF est figé."),
            extra_tags="moment-signed",
        )
        return redirect("documents:contract-history", gig_id=self.gig.pk)


class ContractSignedPdfView(TenantScopedMixin, View):
    """Download the scan of the signed contract (GET) or add it afterwards (POST)."""

    def get(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        contract = Contract.objects.filter(gig=gig, tenant=request.tenant).first()
        if not (contract and contract.signed_pdf):
            raise Http404
        return FileResponse(
            contract.signed_pdf.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"{contract.reference}-signe.pdf",
        )

    def post(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        form = SignedPdfForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, " ".join(form.errors["signed_pdf"]))
        elif not form.cleaned_data["signed_pdf"]:
            messages.error(request, _("Choisissez le PDF signé à ajouter."))
        else:
            try:
                services.attach_signed_pdf(gig, form.cleaned_data["signed_pdf"])
            except services.ContractSigningError as error:
                messages.error(request, error.args[0])
            else:
                messages.success(request, _("Le PDF signé est enregistré."))
        return redirect("documents:contract-history", gig_id=gig.pk)


class ContractGenerateView(TenantScopedMixin, View):
    def post(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        template, error = requested_template(request, request.POST)
        if error:
            messages.error(request, error)
            return redirect("documents:contract-history", gig_id=gig.pk)
        try:
            contract = services.generate_contract_pdf(gig, user=request.user, template=template)
        except services.ContractNotAvailable:
            return no_contract_response(request, gig)
        if contract.status == Contract.Status.SIGNED:
            messages.error(request, _("Ce contrat est signé : il ne peut plus être régénéré."))
        else:
            messages.success(request, _("Une nouvelle version du contrat a été générée."))
        return redirect("documents:contract-history", gig_id=gig.pk)


class ContractSentView(TenantScopedMixin, View):
    """POST only: mark the contract as sent to the promoter, or take the mark back."""

    def post(self, request, gig_id, action):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        try:
            if action == "envoye":
                services.mark_contract_sent(gig)
                messages.success(request, _("Le contrat est marqué comme envoyé."))
            else:
                services.unmark_contract_sent(gig)
                messages.success(request, _("La mention « envoyé » est retirée."))
        except services.ContractSigningError as error:
            messages.error(request, error.args[0])
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
    version = (contract.signed_version or contract.latest_version) if contract else None
    if version is None:
        return no_contract_response(request, gig)
    return FileResponse(version.pdf_file.open("rb"), content_type="application/pdf")


class ContractCompleteView(TenantScopedMixin, View):
    """One page to fill in every value the contract needs (the "Compléter le contrat" form)."""

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
        invitation = addressbook_services.latest_invitation(self.gig.promoter)
        context["invitation"] = invitation
        if invitation and invitation.status == invitation.Status.ACTIVE:
            context["invitation_url"] = self.request.build_absolute_uri(
                addressbook_services.invitation_path(invitation.token)
            )
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


class DocumentLibraryView(TenantScopedMixin, View):
    """The "Documents" tab: every issued document of the tenant, with filters."""

    def get(self, request):
        form = DocumentFilterForm(request.GET, tenant=request.tenant)
        context = {
            "filter_form": form,
            "documents": form.documents(),
            "filtered": any(request.GET.get(name) for name in form.fields),
        }
        template = (
            "documents/_library_results.html"
            if wants_fragment(request)
            else "documents/library.html"
        )
        return render(request, template, context)
