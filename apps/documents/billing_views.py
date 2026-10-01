"""Screens for the quotes and invoices of a gig (the money rules are in invoicing.py)."""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.core.views import TenantScopedMixin, wants_fragment
from apps.gigs.models import Gig
from apps.tenants.models import Tenant

from . import invoicing
from .forms import DocumentLineForm
from .models import DocumentLine, Invoice, Quote

DOC_TYPES = {"factures": Invoice, "devis": Quote}
INVOICE_KINDS = {
    "acompte": Invoice.Kind.DEPOSIT,
    "solde": Invoice.Kind.BALANCE,
    "totale": Invoice.Kind.FULL,
}


class BillingView(TenantScopedMixin, View):
    """The "Devis et factures" page of a gig."""

    def get(self, request, gig_id):
        gig = get_object_or_404(Gig, pk=gig_id, tenant=request.tenant)
        invoiced = invoicing.invoiced_excl_tax(gig)
        context = {
            "gig": gig,
            "invoices": Invoice.objects.filter(gig=gig, tenant=request.tenant),
            "quotes": Quote.objects.filter(gig=gig, tenant=request.tenant),
            "invoiced": invoiced,
            "remaining": max(gig.price - invoiced, 0),
        }
        return render(request, "documents/billing.html", context)


class CreateDocumentView(TenantScopedMixin, View):
    """POST only: start a draft invoice (of the given kind) or a draft quote."""

    http_method_names = ["post"]

    def post(self, request, gig_id, kind=None):
        gig = get_object_or_404(
            Gig.objects.select_related("show"), pk=gig_id, tenant=request.tenant
        )
        if kind is None:
            document, doc_type = invoicing.create_quote(gig), "devis"
        else:
            if kind not in INVOICE_KINDS:
                raise Http404
            document = invoicing.create_invoice(gig, INVOICE_KINDS[kind])
            doc_type = "factures"
        return redirect(
            "documents:document-detail", gig_id=gig.pk, doc_type=doc_type, pk=document.pk
        )


class DocumentMixin(TenantScopedMixin):
    """Load the gig and the document of the URL, always inside the current tenant."""

    def load(self, gig_id, doc_type, pk):
        self.doc_type = doc_type
        self.gig = get_object_or_404(
            Gig.objects.select_related("show", "promoter"), pk=gig_id, tenant=self.request.tenant
        )
        self.document = get_object_or_404(
            DOC_TYPES[doc_type], pk=pk, gig=self.gig, tenant=self.request.tenant
        )

    def get_line(self, line_pk):
        parent = "invoice" if self.doc_type == "factures" else "quote"
        return get_object_or_404(
            DocumentLine, pk=line_pk, tenant=self.request.tenant, **{parent: self.document}
        )

    def show_vat(self):
        return self.request.tenant.vat_regime == Tenant.VatRegime.TAXABLE

    def context(self, **extra):
        document = self.document
        is_invoice = isinstance(document, Invoice)
        context = {
            "gig": self.gig,
            "document": document,
            "doc_type": self.doc_type,
            "is_invoice": is_invoice,
            "is_credit_note": is_invoice and document.kind == Invoice.Kind.CREDIT_NOTE,
            "rows": [
                {"line": line, "total": invoicing.line_total(line)} for line in document.lines.all()
            ],
            "show_vat": self.show_vat(),
            "line_form": DocumentLineForm(show_vat=self.show_vat()),
            "editing": None,
        }
        if document.is_draft:
            context["issuer"] = invoicing.build_issuer_snapshot(document.tenant)
            context["customer"] = invoicing.build_customer_snapshot(self.gig.promoter)
            context["missing"] = invoicing.missing_issue_requirements(document)
        else:
            context["issuer"] = document.issuer_snapshot
            context["customer"] = document.customer_snapshot
        if is_invoice:
            context["credit_notes"] = document.credit_notes.all()
            context["can_credit"] = invoicing.creditable_amount(document) > 0
        context.update(extra)
        return context

    def render_page(self, **extra):
        return render(self.request, "documents/document_detail.html", self.context(**extra))

    def render_lines_or_redirect(self, **extra):
        """After an edit: the refreshed lines block for HTMX, the whole page otherwise."""
        if wants_fragment(self.request):
            return render(self.request, "documents/_document_lines.html", self.context(**extra))
        return redirect(
            "documents:document-detail",
            gig_id=self.gig.pk,
            doc_type=self.doc_type,
            pk=self.document.pk,
        )

    def refuse(self, error):
        messages.error(self.request, error)
        return redirect(
            "documents:document-detail",
            gig_id=self.gig.pk,
            doc_type=self.doc_type,
            pk=self.document.pk,
        )


class DocumentDetailView(DocumentMixin, View):
    def get(self, request, gig_id, doc_type, pk):
        self.load(gig_id, doc_type, pk)
        return self.render_page()


def _line_values(form):
    data = form.cleaned_data
    return {
        "label": data["label"],
        "quantity": data["quantity"],
        "unit_price_excl_tax": data["unit_price_excl_tax"],
        "vat_rate": data.get("vat_rate"),
    }


class LineAddView(DocumentMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id, doc_type, pk):
        self.load(gig_id, doc_type, pk)
        form = DocumentLineForm(request.POST, show_vat=self.show_vat())
        if not form.is_valid():
            if wants_fragment(request):
                return self.render_lines_or_redirect(line_form=form)
            return self.render_page(line_form=form)
        try:
            invoicing.add_line(self.document, **_line_values(form))
        except invoicing.InvoicingError as error:
            return self.render_lines_or_redirect(error=error.args[0])
        return self.render_lines_or_redirect()


class LineEditView(DocumentMixin, View):
    """GET shows one line as a form, POST saves it."""

    def get(self, request, gig_id, doc_type, pk, line_pk):
        self.load(gig_id, doc_type, pk)
        line = self.get_line(line_pk)
        form = DocumentLineForm.from_line(line, show_vat=self.show_vat())
        extra = {"editing": line.pk, "edit_form": form}
        if wants_fragment(request):
            return render(request, "documents/_document_lines.html", self.context(**extra))
        return self.render_page(**extra)

    def post(self, request, gig_id, doc_type, pk, line_pk):
        self.load(gig_id, doc_type, pk)
        line = self.get_line(line_pk)
        form = DocumentLineForm.from_line(line, request.POST, show_vat=self.show_vat())
        if not form.is_valid():
            extra = {"editing": line.pk, "edit_form": form}
            if wants_fragment(request):
                return render(request, "documents/_document_lines.html", self.context(**extra))
            return self.render_page(**extra)
        try:
            invoicing.update_line(line, **_line_values(form))
        except invoicing.InvoicingError as error:
            return self.render_lines_or_redirect(error=error.args[0])
        return self.render_lines_or_redirect()


class LineRemoveView(DocumentMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id, doc_type, pk, line_pk):
        self.load(gig_id, doc_type, pk)
        line = self.get_line(line_pk)
        try:
            invoicing.remove_line(line)
        except invoicing.InvoicingError as error:
            return self.render_lines_or_redirect(error=error.args[0])
        return self.render_lines_or_redirect()


class DocumentIssueView(DocumentMixin, View):
    """Issuing is final: a confirmation page first, then POST."""

    def get(self, request, gig_id, doc_type, pk):
        self.load(gig_id, doc_type, pk)
        if not self.document.is_draft:
            return self.refuse(_("Ce document est déjà émis."))
        context = self.context()
        if context["missing"] or not context["rows"]:
            return self.refuse(_("Ce document n'est pas prêt à être émis."))
        return render(request, "documents/document_issue.html", context)

    def post(self, request, gig_id, doc_type, pk):
        self.load(gig_id, doc_type, pk)
        issue = invoicing.issue_invoice if doc_type == "factures" else invoicing.issue_quote
        try:
            issue(self.document)
        except invoicing.InvoicingError as error:
            return self.refuse(error.args[0])
        messages.success(
            request,
            _("Le document est émis : il porte le numéro %(number)s.")
            % {"number": self.document.number},
        )
        return redirect(
            "documents:document-detail", gig_id=self.gig.pk, doc_type=doc_type, pk=self.document.pk
        )


class DocumentDeleteView(DocumentMixin, View):
    """Throw a draft away (an issued document can never be deleted)."""

    http_method_names = ["post"]

    def post(self, request, gig_id, doc_type, pk):
        self.load(gig_id, doc_type, pk)
        if not self.document.is_draft:
            return self.refuse(_("Un document émis ne peut pas être supprimé."))
        self.document.delete()
        messages.success(request, _("Le brouillon est supprimé."))
        return redirect("documents:billing", gig_id=self.gig.pk)


class CreditNoteView(DocumentMixin, View):
    """POST only: start a draft credit note from an issued invoice."""

    http_method_names = ["post"]

    def post(self, request, gig_id, pk):
        self.load(gig_id, "factures", pk)
        try:
            note = invoicing.create_credit_note(self.document)
        except invoicing.InvoicingError as error:
            return self.refuse(error.args[0])
        return redirect(
            "documents:document-detail", gig_id=self.gig.pk, doc_type="factures", pk=note.pk
        )
