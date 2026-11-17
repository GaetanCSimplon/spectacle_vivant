from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django.views import View

from apps.addressbook import services as addressbook_services
from apps.core.views import TenantScopedMixin, wants_fragment
from apps.gigs import mail as gig_mail
from apps.gigs.models import Gig
from apps.radar import rules as radar_rules

from . import checks, services
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
        anomalies = checks.to_fix(checks.check_contract(gig, contract))
        pdf_bytes = services.render_contract_pdf(gig, contract, draft_anomalies=anomalies or None)
        return HttpResponse(pdf_bytes, content_type="application/pdf")


class ContractHistoryView(TenantScopedMixin, View):
    """The contract page of a gig: its reference, its versions, and the "generate" button."""

    template_name = "documents/contract_history.html"

    def contract_mail(self, gig, contract):
        link = services.active_share_link(contract)
        if link is None:
            return None
        url = self.request.build_absolute_uri(reverse("contract-share-public", args=[link.token]))
        return gig_mail.contract_mail(gig, url)

    def get(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        contract = Contract.objects.filter(gig=gig, tenant=request.tenant).first()
        versions = contract.versions.select_related("created_by") if contract else []
        signed = bool(contract and contract.status == Contract.Status.SIGNED)
        anomalies = checks.check_contract(gig, contract)
        latest = contract.latest_version if contract else None
        context = {
            "anomalies": anomalies,
            "anomaly_groups": checks.grouped(anomalies),
            "to_fix_count": len(checks.to_fix(anomalies)),
            "confirmable": True,
            # Not sent, not signed, and written from data that has changed since.
            "latest_is_stale": bool(
                latest
                and latest.facts_fingerprint
                and not contract.sent_at
                and not signed
                and latest.facts_fingerprint != checks.facts_fingerprint(gig, contract)
            ),
            "gig": gig,
            "contract": contract,
            "versions": versions,
            "can_generate": gig.status != Gig.Status.CANCELLED and not signed,
            "can_sign": gig.status == Gig.Status.CONFIRMED
            and bool(contract and contract.latest_version)
            and not signed,
            "can_mark_sent": bool(contract and contract.latest_version) and not signed,
            "send_alerts": radar_rules.for_action("contract_send", gig)
            if contract and not contract.sent_at
            else [],
            "mail": self.contract_mail(gig, contract),
            "can_add_signed_pdf": signed and not contract.signed_pdf,
            "signed_pdf_form": SignedPdfForm(),
        }
        return render(request, self.template_name, context)


class ContractShareView(TenantScopedMixin, View):
    """POST only: make the download link the e-mail carries (`mailto:` attaches nothing)."""

    http_method_names = ["post"]

    def post(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        contract = Contract.objects.filter(gig=gig, tenant=request.tenant).first()
        try:
            if contract is None or contract.status == Contract.Status.SIGNED:
                raise services.ContractSigningError(
                    _("Générez d'abord le contrat avant de l'envoyer.")
                )
            services.create_share_link(contract, request.user)
            messages.success(request, _("Le message est prêt : ouvrez votre messagerie."))
        except services.ContractSigningError as error:
            messages.error(request, error.args[0])
        return redirect("documents:contract-history", gig_id=gig.pk)


class ContractSignView(TenantScopedMixin, View):
    """Confirmation page, then freeze the latest version as the signed contract."""

    template_name = "documents/contract_sign.html"

    def load(self, gig_id):
        self.gig = get_object_or_404(Gig, pk=gig_id, tenant=self.request.tenant)
        self.contract = Contract.objects.filter(gig=self.gig, tenant=self.request.tenant).first()

    def render_page(self, form):
        context = {
            "gig": self.gig,
            "contract": self.contract,
            "form": form,
            "alerts": radar_rules.for_action("contract_sign", self.gig),
        }
        # Radar's modal, when the link was followed by htmx; the page otherwise.
        template = (
            "documents/_contract_sign_dialog.html"
            if self.request.htmx and self.request.method == "GET"
            else self.template_name
        )
        return render(self.request, template, context)

    def refuse(self, error):
        messages.error(self.request, error)
        url = reverse("documents:contract-history", args=[self.gig.pk])
        if self.request.htmx:  # the modal must not receive a whole page
            return HttpResponse(headers={"HX-Redirect": url})
        return redirect(url)

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
        contract = Contract.objects.filter(gig=gig, tenant=request.tenant).first()
        signed = contract and contract.status == Contract.Status.SIGNED
        anomalies = checks.to_fix(checks.check_contract(gig, contract))
        if anomalies and not signed and gig.status != Gig.Status.CANCELLED:
            messages.error(
                request,
                ngettext(
                    "Génération impossible : %(n)d élément à compléter.",
                    "Génération impossible : %(n)d éléments à compléter.",
                    len(anomalies),
                )
                % {"n": len(anomalies)},
            )
            return redirect("documents:contract-history", gig_id=gig.pk)
        try:
            contract = services.generate_contract_pdf(gig, user=request.user)
        except services.ContractNotAvailable:
            return no_contract_response(request, gig)
        if contract.status == Contract.Status.SIGNED:
            messages.error(request, _("Ce contrat est signé : il ne peut plus être régénéré."))
        else:
            messages.success(request, _("Une nouvelle version du contrat a été générée."))
        return redirect("documents:contract-history", gig_id=gig.pk)


class ContractConfirmView(TenantScopedMixin, View):
    """POST only: record a confirmation the checks ask for, as the data stands now."""

    def post(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        if checks.confirm(gig, request.POST.get("code", ""), request.user):
            messages.success(request, _("Confirmation enregistrée."))
        else:
            messages.error(request, _("Rien à confirmer ici."))
        return redirect("documents:contract-history", gig_id=gig.pk)


class ContractSentView(TenantScopedMixin, View):
    """Mark the contract as sent to the promoter, or take the mark back (POST). The GET page
    is Radar's pop-up: it lists what is still missing and lets the user go on anyway."""

    def get(self, request, gig_id, action):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        if action != "envoye":  # taking the mark back is a POST; nothing to confirm
            return redirect("documents:contract-history", gig_id=gig.pk)
        context = {"gig": gig, "alerts": radar_rules.for_action("contract_send", gig)}
        template = (
            "documents/_contract_send_dialog.html"
            if request.htmx
            else "documents/contract_send_confirm.html"
        )
        return render(request, template, context)

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
        anomalies = checks.check_contract(self.gig, self.contract)
        context = {
            "gig": self.gig,
            "forms": forms,
            "anomaly_groups": checks.grouped(anomalies),
            "to_fix_count": len(checks.to_fix(anomalies)),
        }
        invitation = addressbook_services.latest_invitation(self.gig.promoter)
        context["invitation"] = invitation
        if invitation and invitation.status == invitation.Status.ACTIVE:
            context["invitation_url"] = self.request.build_absolute_uri(
                addressbook_services.invitation_path(invitation.token)
            )
            context["mail"] = gig_mail.form_mail(self.gig, context["invitation_url"])
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
