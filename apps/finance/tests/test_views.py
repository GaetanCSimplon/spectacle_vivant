import datetime
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.documents import invoicing
from apps.documents.models import Invoice
from apps.tenants.factories import MembershipFactory

from .. import services
from ..factories import ExpenseFactory
from ..models import Expense, Payment
from .helpers import TENANT_FIELDS, issued_invoice, make_gig

pytestmark = pytest.mark.django_db

D = Decimal
HTMX = {"HTTP_HX_REQUEST": "true"}
TODAY = datetime.date(2026, 10, 3)
PDF = b"%PDF-1.4 test"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def tenant(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    return membership.tenant


@pytest.fixture
def gig(tenant):
    return make_gig(tenant=tenant, price="1000.00")


@pytest.fixture
def invoice(gig):
    return issued_invoice(gig)


def _url(name, gig, *args):
    return reverse(f"finance:{name}", args=[gig.pk, *args])


def _payment_data(amount="400.00", **extra):
    return {"amount": amount, "date": "2026-10-03", "method": "transfer", **extra}


def _expense_data(**extra):
    return {
        "category": "transport",
        "label": "Essence",
        "amount": "40.00",
        "date": "2026-10-03",
        **extra,
    }


def _pdf(name="ticket.pdf", content=PDF):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


# --- page ----------------------------------------------------------------------


def test_the_page_shows_balance_and_payable_invoices(client, gig, invoice):
    response = client.get(_url("page", gig))

    text = response.content.decode()
    assert response.status_code == 200
    assert invoice.number in text
    assert "Enregistrer un paiement" in text


def test_the_page_lists_neither_drafts_nor_credit_notes(client, gig):
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    other = issued_invoice(make_gig(tenant=gig.tenant, price="500.00"))
    invoicing.issue_invoice(invoicing.create_credit_note(other))

    text = client.get(_url("page", gig)).content.decode()

    assert "Enregistrer un paiement" not in text
    assert draft.number == ""


def test_a_settled_invoice_has_no_payment_form(client, gig, invoice):
    services.record_payment(invoice, "1000.00", TODAY, Payment.Method.CASH)

    text = client.get(_url("page", gig)).content.decode()

    assert "Payée" in text
    assert "Enregistrer un paiement" not in text


def test_the_balance_is_shown_in_whole_euros(client, gig, invoice):
    services.record_payment(invoice, "100.60", TODAY, Payment.Method.CASH)

    text = client.get(_url("page", gig)).content.decode()

    assert "101 €" in text  # the summary is rounded...
    assert "100,60" in text  # ...the payment line is exact


def test_the_gig_detail_shows_the_finance_block(client, gig, invoice):
    services.record_payment(invoice, "300.00", TODAY, Payment.Method.CASH)
    ExpenseFactory(gig=gig, amount="50.00")

    text = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert _url("page", gig) in text
    assert "300 €" in text
    assert "250 €" in text  # result


# --- payments ------------------------------------------------------------------


def test_add_a_payment_without_javascript(client, gig, invoice, tenant):
    response = client.post(_url("payment-add", gig, invoice.pk), _payment_data())

    assert response.status_code == 302
    assert response.url == _url("page", gig)
    payment = Payment.objects.get()
    assert (payment.amount, payment.tenant) == (D("400.00"), tenant)


def test_add_a_payment_with_htmx_returns_the_fragment(client, gig, invoice):
    response = client.post(_url("payment-add", gig, invoice.pk), _payment_data(), **HTMX)

    text = response.content.decode()
    assert response.status_code == 200
    assert 'id="finance-body"' in text
    assert "<html" not in text
    assert "Reste 600,00" in text


def test_paying_in_full_shows_paid(client, gig, invoice):
    client.post(_url("payment-add", gig, invoice.pk), _payment_data("1000.00"))

    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID


def test_overpaying_shows_an_error_and_saves_nothing(client, gig, invoice):
    response = client.post(_url("payment-add", gig, invoice.pk), _payment_data("1000.01"), **HTMX)

    assert response.status_code == 200
    assert "dépasse le reste à payer" in response.content.decode()
    assert not Payment.objects.exists()


@pytest.mark.parametrize(
    "data", [{"amount": "0"}, {"amount": "abc"}, {"date": ""}, {"method": "x"}]
)
def test_invalid_payment_data_is_refused(client, gig, invoice, data):
    response = client.post(_url("payment-add", gig, invoice.pk), _payment_data(**data))

    assert response.status_code == 200
    assert "errorlist" in response.content.decode()
    assert not Payment.objects.exists()


def test_a_draft_invoice_cannot_be_paid_through_the_view(client, gig):
    draft = invoicing.create_invoice(gig, Invoice.Kind.FULL)

    response = client.post(_url("payment-add", gig, draft.pk), _payment_data())

    assert response.status_code == 200  # a draft is not on the page: nothing to show an error on
    assert not Payment.objects.exists()


def test_the_form_cannot_choose_tenant_or_invoice(client, gig, invoice, tenant):
    other = issued_invoice(make_gig())

    client.post(
        _url("payment-add", gig, invoice.pk),
        _payment_data(tenant=other.tenant.pk, invoice=other.pk),
    )

    payment = Payment.objects.get()
    assert payment.tenant == tenant
    assert payment.invoice == invoice


def test_edit_a_payment(client, gig, invoice):
    payment = services.record_payment(invoice, "1000.00", TODAY, Payment.Method.CASH)
    form = client.get(_url("payment-edit", gig, payment.pk), **HTMX)
    assert "1000.00" in form.content.decode()

    response = client.post(_url("payment-edit", gig, payment.pk), _payment_data("700.00"))

    assert response.status_code == 302
    payment.refresh_from_db()
    invoice.refresh_from_db()
    assert payment.amount == D("700.00")
    assert invoice.status == Invoice.Status.ISSUED


def test_edit_cannot_overpay(client, gig, invoice):
    services.record_payment(invoice, "600.00", TODAY, Payment.Method.CASH)
    payment = services.record_payment(invoice, "100.00", TODAY, Payment.Method.CASH)

    response = client.post(_url("payment-edit", gig, payment.pk), _payment_data("500.00"))

    assert "dépasse" in response.content.decode()
    payment.refresh_from_db()
    assert payment.amount == D("100.00")


def test_delete_a_payment(client, gig, invoice):
    payment = services.record_payment(invoice, "1000.00", TODAY, Payment.Method.CASH)

    response = client.post(_url("payment-delete", gig, payment.pk), **HTMX)

    assert response.status_code == 200
    assert not Payment.objects.exists()
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.ISSUED


# --- expenses ------------------------------------------------------------------


def test_add_an_expense(client, gig, tenant):
    response = client.post(_url("expense-add", gig), _expense_data())

    assert response.status_code == 302
    expense = Expense.objects.get()
    assert (expense.tenant, expense.gig, expense.amount) == (tenant, gig, D("40.00"))
    assert not expense.receipt_file


def test_add_an_expense_with_a_receipt_and_download_it(client, gig):
    client.post(_url("expense-add", gig), _expense_data(receipt_file=_pdf()))
    expense = Expense.objects.get()

    assert expense.receipt_file.name.startswith("expenses/")
    assert len(expense.receipt_file.name.split("/")[1]) == 32
    response = client.get(_url("expense-receipt", gig, expense.pk))
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == PDF
    assert "attachment" in response["Content-Disposition"]


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("virus.pdf", b"MZ not a pdf"),
        ("note.txt", b"just text"),
        ("page.html", b"<script>alert(1)</script>"),
    ],
)
def test_a_receipt_must_really_be_a_pdf_or_an_image(client, gig, name, content):
    response = client.post(
        _url("expense-add", gig), _expense_data(receipt_file=_pdf(name, content))
    )

    assert response.status_code == 200
    assert "doit être un PDF" in response.content.decode()
    assert not Expense.objects.exists()


def test_a_png_and_a_jpeg_are_accepted(client, gig):
    for name, head in [("a.png", b"\x89PNG\r\n\x1a\n0000"), ("b.jpg", b"\xff\xd8\xff\xe0000")]:
        client.post(_url("expense-add", gig), _expense_data(receipt_file=_pdf(name, head)))

    assert Expense.objects.count() == 2


def test_a_receipt_over_10_mb_is_refused(client, gig):
    big = _pdf(content=PDF + b"0" * (10 * 1024 * 1024))

    response = client.post(_url("expense-add", gig), _expense_data(receipt_file=big))

    assert "trop lourd" in response.content.decode()
    assert not Expense.objects.exists()


@pytest.mark.parametrize(
    "data", [{"amount": "0"}, {"amount": "-3"}, {"label": ""}, {"category": "x"}, {"date": ""}]
)
def test_invalid_expense_data_is_refused(client, gig, data):
    response = client.post(_url("expense-add", gig), _expense_data(**data), **HTMX)

    assert response.status_code == 200
    assert "errorlist" in response.content.decode()
    assert not Expense.objects.exists()


def test_edit_an_expense_and_replace_its_receipt(client, gig):
    client.post(_url("expense-add", gig), _expense_data(receipt_file=_pdf()))
    expense = Expense.objects.get()
    old = expense.receipt_file.name
    storage = expense.receipt_file.storage

    client.post(
        _url("expense-edit", gig, expense.pk),
        _expense_data(label="Péage", receipt_file=_pdf("new.pdf")),
    )

    expense.refresh_from_db()
    assert expense.label == "Péage"
    assert expense.receipt_file.name != old
    assert not storage.exists(old)
    assert storage.exists(expense.receipt_file.name)


def test_editing_without_a_new_file_keeps_the_receipt(client, gig):
    client.post(_url("expense-add", gig), _expense_data(receipt_file=_pdf()))
    expense = Expense.objects.get()
    name = expense.receipt_file.name

    client.post(_url("expense-edit", gig, expense.pk), _expense_data(label="Gazole"))

    expense.refresh_from_db()
    assert expense.receipt_file.name == name
    assert expense.label == "Gazole"


def test_delete_an_expense_removes_its_receipt_file(client, gig):
    client.post(_url("expense-add", gig), _expense_data(receipt_file=_pdf()))
    expense = Expense.objects.get()
    name, storage = expense.receipt_file.name, expense.receipt_file.storage

    response = client.post(_url("expense-delete", gig, expense.pk), **HTMX)

    assert response.status_code == 200
    assert not Expense.objects.exists()
    assert not storage.exists(name)


def test_receipt_of_an_expense_without_file_is_404(client, gig):
    expense = ExpenseFactory(gig=gig)

    assert client.get(_url("expense-receipt", gig, expense.pk)).status_code == 404


def test_the_form_cannot_choose_the_gig_or_tenant_of_an_expense(client, gig, tenant):
    other = make_gig()

    client.post(_url("expense-add", gig), _expense_data(gig=other.pk, tenant=other.tenant.pk))

    expense = Expense.objects.get()
    assert (expense.gig, expense.tenant) == (gig, tenant)


# --- login and isolation -----------------------------------------------------


def _routes(gig, invoice, payment, expense):
    return [
        ("get", _url("page", gig)),
        ("post", _url("payment-add", gig, invoice.pk)),
        ("get", _url("payment-edit", gig, payment.pk)),
        ("post", _url("payment-edit", gig, payment.pk)),
        ("post", _url("payment-delete", gig, payment.pk)),
        ("post", _url("expense-add", gig)),
        ("get", _url("expense-edit", gig, expense.pk)),
        ("post", _url("expense-edit", gig, expense.pk)),
        ("post", _url("expense-delete", gig, expense.pk)),
        ("get", _url("expense-receipt", gig, expense.pk)),
    ]


def _foreign():
    gig = make_gig()
    invoice = issued_invoice(gig)
    payment = services.record_payment(invoice, "10.00", TODAY, Payment.Method.CASH)
    expense = ExpenseFactory(gig=gig, receipt_file=_pdf())
    return gig, invoice, payment, expense


def test_login_is_required_everywhere(client):
    for method, url in _routes(*_foreign()):
        response = getattr(client, method)(url)
        assert response.status_code == 302, url
        assert "/accounts/login/" in response.url, url


def test_another_tenant_gets_404_on_every_route(client, tenant):
    gig, invoice, payment, expense = _foreign()

    for method, url in _routes(gig, invoice, payment, expense):
        assert getattr(client, method)(url, _payment_data()).status_code == 404, url

    assert Payment.objects.count() == 1
    assert Expense.objects.count() == 1
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.ISSUED


def test_an_object_is_only_reachable_through_its_own_gig(client, tenant, gig):
    other_gig = make_gig(tenant=tenant)
    other_invoice = issued_invoice(other_gig)
    payment = services.record_payment(other_invoice, "10.00", TODAY, Payment.Method.CASH)
    expense = ExpenseFactory(gig=other_gig)

    assert (
        client.post(_url("payment-add", gig, other_invoice.pk), _payment_data()).status_code == 404
    )
    assert client.get(_url("payment-edit", gig, payment.pk)).status_code == 404
    assert client.post(_url("payment-delete", gig, payment.pk)).status_code == 404
    assert client.get(_url("expense-edit", gig, expense.pk)).status_code == 404
    assert client.post(_url("expense-delete", gig, expense.pk)).status_code == 404
    assert client.get(_url("expense-receipt", gig, expense.pk)).status_code == 404
    assert Payment.objects.count() == 1
    assert Expense.objects.count() == 1


def test_the_page_never_shows_another_tenants_money(client, gig):
    _foreign()

    text = client.get(_url("page", gig)).content.decode()

    assert "Essence" not in text
    assert "10.00" not in text


def test_get_on_post_only_routes_is_405(client, gig, invoice):
    payment = services.record_payment(invoice, "10.00", TODAY, Payment.Method.CASH)
    expense = ExpenseFactory(gig=gig)

    assert client.get(_url("payment-add", gig, invoice.pk)).status_code == 405
    assert client.get(_url("payment-delete", gig, payment.pk)).status_code == 405
    assert client.get(_url("expense-add", gig)).status_code == 405
    assert client.get(_url("expense-delete", gig, expense.pk)).status_code == 405
