"""Payments and expenses of a gig: one page, edited in place (HTMX, no-JavaScript fallback)."""

import datetime
import os

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.views import TenantScopedMixin, wants_fragment
from apps.documents.models import Invoice
from apps.gigs.models import Gig

from . import services
from .forms import ExpenseForm, PaymentForm
from .models import Expense, Payment


class FinanceMixin(TenantScopedMixin):
    """Load the gig of the URL (inside the current tenant); every object hangs from it."""

    def load(self, gig_id):
        self.gig = get_object_or_404(
            Gig.objects.select_related("show"), pk=gig_id, tenant=self.request.tenant
        )

    def get_invoice(self, pk):
        return get_object_or_404(Invoice, pk=pk, gig=self.gig, tenant=self.request.tenant)

    def get_payment(self, pk):
        return get_object_or_404(
            Payment.objects.select_related("invoice"),
            pk=pk,
            invoice__gig=self.gig,
            tenant=self.request.tenant,
        )

    def get_expense(self, pk):
        return get_object_or_404(Expense, pk=pk, gig=self.gig, tenant=self.request.tenant)

    def context(self, payment_forms=None, expense_form=None, editing=None, edit_form=None):
        """Bound forms go back to the page after an error; `editing` = ("payment"|"expense", pk)."""
        tenant = self.request.tenant
        payment_forms = payment_forms or {}
        invoices = Invoice.objects.filter(
            gig=self.gig, tenant=tenant, status__in=services.PAYABLE
        ).exclude(kind=Invoice.Kind.CREDIT_NOTE)
        rows = []
        for invoice in invoices.order_by("number"):
            remaining = services.remaining_to_pay(invoice)
            rows.append(
                {
                    "invoice": invoice,
                    "payments": invoice.payments.filter(tenant=tenant),
                    "paid": services.paid_amount(invoice),
                    "remaining": remaining,
                    "form": payment_forms.get(invoice.pk)
                    or (PaymentForm(initial=_payment_initial(remaining)) if remaining else None),
                }
            )
        return {
            "gig": self.gig,
            "balance": services.gig_balance(self.gig),
            "rows": rows,
            "expenses": Expense.objects.filter(gig=self.gig, tenant=tenant),
            "expense_form": expense_form or ExpenseForm(),
            "editing": editing,
            "edit_form": edit_form,
        }

    def render_page(self, **kwargs):
        return render(self.request, "finance/finance.html", self.context(**kwargs))

    def render_body_or_page(self, **kwargs):
        if wants_fragment(self.request):
            return render(self.request, "finance/_body.html", self.context(**kwargs))
        return self.render_page(**kwargs)

    def done(self):
        if wants_fragment(self.request):
            return render(self.request, "finance/_body.html", self.context())
        return redirect("finance:page", gig_id=self.gig.pk)


def _payment_initial(remaining):
    return {"amount": remaining, "date": datetime.date.today(), "method": Payment.Method.TRANSFER}


class FinanceView(FinanceMixin, View):
    def get(self, request, gig_id):
        self.load(gig_id)
        return self.render_page()


# --- payments ----------------------------------------------------------------


class PaymentAddView(FinanceMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id, invoice_pk):
        self.load(gig_id)
        invoice = self.get_invoice(invoice_pk)
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                services.record_payment(invoice, **form.cleaned_data)
            except services.PaymentError as error:
                form.add_error(None, error.args[0])
            else:
                return self.done()
        return self.render_body_or_page(payment_forms={invoice.pk: form})


class PaymentEditView(FinanceMixin, View):
    """GET shows one payment as a form, POST saves it."""

    def get(self, request, gig_id, pk):
        self.load(gig_id)
        payment = self.get_payment(pk)
        form = PaymentForm(instance=payment)
        return self.render_body_or_page(editing=("payment", payment.pk), edit_form=form)

    def post(self, request, gig_id, pk):
        self.load(gig_id)
        payment = self.get_payment(pk)
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                services.update_payment(payment, **form.cleaned_data)
            except services.PaymentError as error:
                form.add_error(None, error.args[0])
            else:
                return self.done()
        return self.render_body_or_page(editing=("payment", payment.pk), edit_form=form)


class PaymentDeleteView(FinanceMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id, pk):
        self.load(gig_id)
        services.delete_payment(self.get_payment(pk))
        return self.done()


# --- expenses ----------------------------------------------------------------


class ExpenseAddView(FinanceMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id):
        self.load(gig_id)
        form = ExpenseForm(request.POST, request.FILES)
        if not form.is_valid():
            return self.render_body_or_page(expense_form=form)
        expense = form.save(commit=False)
        expense.tenant = request.tenant
        expense.gig = self.gig
        services.save_expense(expense)
        return self.done()


class ExpenseEditView(FinanceMixin, View):
    """GET shows one expense as a form, POST saves it."""

    def get(self, request, gig_id, pk):
        self.load(gig_id)
        expense = self.get_expense(pk)
        form = ExpenseForm(instance=expense)
        return self.render_body_or_page(editing=("expense", expense.pk), edit_form=form)

    def post(self, request, gig_id, pk):
        self.load(gig_id)
        expense = self.get_expense(pk)
        previous = expense.receipt_file.name
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if not form.is_valid():
            return self.render_body_or_page(editing=("expense", expense.pk), edit_form=form)
        services.save_expense(form.save(commit=False), previous_receipt=previous)
        return self.done()


class ExpenseDeleteView(FinanceMixin, View):
    http_method_names = ["post"]

    def post(self, request, gig_id, pk):
        self.load(gig_id)
        services.delete_expense(self.get_expense(pk))
        return self.done()


class ExpenseReceiptView(FinanceMixin, View):
    """The receipt is only ever sent by this view, which checks the tenant (no /media/ route)."""

    def get(self, request, gig_id, pk):
        self.load(gig_id)
        expense = self.get_expense(pk)
        if not expense.receipt_file:
            raise Http404
        return FileResponse(
            expense.receipt_file.open("rb"),
            as_attachment=True,
            filename=os.path.basename(expense.receipt_file.name),
        )
