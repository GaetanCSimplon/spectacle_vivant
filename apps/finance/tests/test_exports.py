import csv
import datetime
import io

import pytest
from django.urls import reverse

from apps.documents import invoicing
from apps.documents.models import Invoice
from apps.tenants.factories import MembershipFactory

from .. import exports, services
from ..factories import ExpenseFactory
from ..models import Expense, Payment
from .helpers import TENANT_FIELDS, issued_invoice, make_gig

pytestmark = pytest.mark.django_db

CASH = Payment.Method.CASH
PERIOD = {"start": "2026-01-01", "end": "2026-12-31"}


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def tenant(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    return membership.tenant


def _download(client, kind, **params):
    return client.get(reverse("export-csv", args=[kind]), {**PERIOD, **params})


def _table(response):
    """Rows of the CSV as an Excel (French) would read them."""
    content = response.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(content), delimiter=";"))


def _issue_on(invoice, date):
    Invoice.objects.filter(pk=invoice.pk).update(issue_date=date)


# --- format ------------------------------------------------------------------------


def test_the_file_is_utf8_with_bom_and_semicolons(client, tenant):
    ExpenseFactory(gig__tenant=tenant, label="Café", date=datetime.date(2026, 3, 1))

    response = _download(client, "depenses")

    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]
    assert response["Content-Disposition"].endswith('depenses-2026-01-01_2026-12-31.csv"')
    assert response.content.startswith("﻿".encode())
    raw = response.content.decode("utf-8")
    assert raw.splitlines()[0].count(";") == 7
    assert "Café" in raw  # accents survive
    assert raw.endswith("\r\n")


def test_amounts_have_a_decimal_comma_and_exact_cents(client, tenant):
    ExpenseFactory(gig__tenant=tenant, amount="1234.50", date=datetime.date(2026, 3, 1))
    ExpenseFactory(gig__tenant=tenant, amount="0.07", date=datetime.date(2026, 3, 2))

    rows = _table(_download(client, "depenses"))

    assert [row[3] for row in rows[1:]] == ["1234,50", "0,07"]
    assert rows[1][0] == "01/03/2026"


def test_a_text_with_separator_quote_or_newline_stays_in_its_cell(client, tenant):
    label = 'Péage; "A7"\nretour'
    ExpenseFactory(gig__tenant=tenant, label=label, date=datetime.date(2026, 3, 1))

    rows = _table(_download(client, "depenses"))

    assert len(rows) == 2
    assert rows[1][2] == label


@pytest.mark.parametrize("label", ["=1+1", "+33 6", "-2", "@SUM(A1)", "\t=x"])
def test_texts_cannot_run_as_spreadsheet_formulas(client, tenant, label):
    ExpenseFactory(gig__tenant=tenant, label=label, date=datetime.date(2026, 3, 1))

    rows = _table(_download(client, "depenses"))

    assert rows[1][2] == "'" + label


def test_helpers():
    assert exports.text(None) == ""
    assert exports.text("Salle") == "Salle"
    assert exports.amount(5) == "5,00"
    assert exports.amount("-12.3") == "-12,30"
    assert exports.day(None) == ""


# --- period ------------------------------------------------------------------------------


def test_both_ends_of_the_period_are_included(client, tenant):
    for date in ("2025-12-31", "2026-01-01", "2026-12-31", "2027-01-01"):
        ExpenseFactory(gig__tenant=tenant, date=datetime.date.fromisoformat(date))

    rows = _table(_download(client, "depenses"))

    assert [row[0] for row in rows[1:]] == ["01/01/2026", "31/12/2026"]


def test_an_empty_period_gives_a_file_with_only_the_header(client, tenant):
    rows = _table(_download(client, "recettes"))

    assert len(rows) == 1
    assert rows[0][0] == "Date"


@pytest.mark.parametrize(
    "params",
    [
        {"start": "2026-12-31", "end": "2026-01-01"},
        {"start": "", "end": "2026-01-01"},
        {"start": "n'importe quoi", "end": "2026-01-01"},
    ],
)
def test_an_invalid_period_shows_the_page_again(client, tenant, params):
    response = _download(client, "factures", **params)

    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]
    assert "errorlist" in response.content.decode()


def test_the_period_is_required(client, tenant):
    response = client.get(reverse("export-csv", args=["factures"]))

    assert "text/html" in response["Content-Type"]


def test_an_unknown_export_is_404(client, tenant):
    assert _download(client, "tout").status_code == 404


# --- content -----------------------------------------------------------------------------


def test_invoices_export(client, tenant):
    gig = make_gig(tenant=tenant, price="1000.00", gig_fields={"show__title": "Mon Show"})
    invoice = issued_invoice(gig, Invoice.Kind.DEPOSIT)
    _issue_on(invoice, datetime.date(2026, 5, 4))
    services.record_payment(invoice, "100.00", datetime.date(2026, 5, 10), CASH)
    draft = invoicing.create_invoice(make_gig(tenant=tenant), Invoice.Kind.FULL)

    rows = _table(_download(client, "factures"))

    assert len(rows) == 2  # the draft has no number nor issue date
    row = dict(zip(rows[0], rows[1], strict=True))
    assert row["Numéro"] == invoice.number
    assert row["Type"] == "Acompte"
    assert row["Statut"] == "Émise"
    assert row["Date d'émission"] == "04/05/2026"
    assert row["Spectacle"] == "Mon Show"
    assert row["Client"] == "Mairie de Nîmes"
    assert (row["Total HT"], row["TVA"], row["Total TTC"]) == ("300,00", "0,00", "300,00")
    assert (row["Encaissé"], row["Reste à payer"]) == ("100,00", "200,00")
    assert draft.number == ""


def test_credit_notes_are_exported_as_negative_amounts(client, tenant):
    gig = make_gig(tenant=tenant, price="1000.00")
    invoice = issued_invoice(gig)
    note = invoicing.issue_invoice(invoicing.create_credit_note(invoice))
    for document in (invoice, note):
        _issue_on(document, datetime.date(2026, 6, 1))

    rows = _table(_download(client, "factures"))
    by_number = {row[0]: dict(zip(rows[0], row, strict=True)) for row in rows[1:]}

    assert by_number[note.number]["Total TTC"] == "-1000,00"
    assert by_number[note.number]["Type"] == "Avoir"
    assert by_number[note.number]["Reste à payer"] == "0,00"
    assert by_number[invoice.number]["Statut"] == "Annulée par avoir"
    assert by_number[invoice.number]["Reste à payer"] == "0,00"


def test_the_client_name_is_the_frozen_one(client, tenant):
    gig = make_gig(tenant=tenant)
    invoice = issued_invoice(gig)
    _issue_on(invoice, datetime.date(2026, 5, 4))
    gig.promoter.name = "Nouveau nom"
    gig.promoter.save()

    rows = _table(_download(client, "factures"))

    assert rows[1][7] == "Mairie de Nîmes"


def test_payments_export(client, tenant):
    gig = make_gig(tenant=tenant, price="1000.00", gig_fields={"show__title": "Mon Show"})
    invoice = issued_invoice(gig)
    services.record_payment(invoice, "250.40", datetime.date(2026, 7, 14), Payment.Method.CHEQUE)
    services.record_payment(invoice, "10.00", datetime.date(2025, 7, 14), CASH)

    rows = _table(_download(client, "recettes"))

    assert len(rows) == 2
    row = dict(zip(rows[0], rows[1], strict=True))
    assert row["Date"] == "14/07/2026"
    assert row["Mode"] == "Chèque"
    assert row["Montant"] == "250,40"
    assert row["Facture"] == invoice.number
    assert row["Client"] == "Mairie de Nîmes"
    assert row["Spectacle"] == "Mon Show"


def test_expenses_export_says_whether_there_is_a_receipt(client, tenant):
    ExpenseFactory(
        gig__tenant=tenant,
        category=Expense.Category.FEES,
        date=datetime.date(2026, 2, 1),
        receipt_file="expenses/abc/ticket.pdf",
    )
    ExpenseFactory(gig__tenant=tenant, date=datetime.date(2026, 2, 2))

    rows = _table(_download(client, "depenses"))

    assert [row[6] for row in rows[1:]] == ["oui", "non"]
    assert rows[1][1] == "Cachets"
    assert "ticket.pdf" not in "".join(rows[1])  # the stored path is never exported


# --- login and isolation -----------------------------------------------------------------


@pytest.mark.parametrize("kind", ["factures", "recettes", "depenses"])
def test_login_is_required(client, kind):
    response = _download(client, kind)

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_the_page_requires_login_and_loads(client, tenant):
    assert client.get(reverse("export")).status_code == 200
    client.logout()
    assert client.get(reverse("export")).status_code == 302


def test_the_page_proposes_the_current_year(client, tenant):
    text = client.get(reverse("export")).content.decode()
    year = datetime.date.today().year

    assert f'value="{year}-01-01"' in text
    assert f'value="{year}-12-31"' in text
    assert reverse("export-csv", args=["factures"]) in text


def test_exports_never_contain_another_tenants_data(client, tenant):
    mine = make_gig(tenant=tenant)
    other = make_gig(gig_fields={"show__title": "Secret d'un autre"})
    other_invoice = issued_invoice(other)
    _issue_on(other_invoice, datetime.date(2026, 5, 4))
    services.record_payment(other_invoice, "10.00", datetime.date(2026, 5, 5), CASH)
    ExpenseFactory(gig=other, label="Dépense secrète", date=datetime.date(2026, 5, 6))
    own = issued_invoice(mine)
    _issue_on(own, datetime.date(2026, 5, 4))

    for kind in ("factures", "recettes", "depenses"):
        content = _download(client, kind).content.decode("utf-8-sig")
        assert "Secret" not in content
        assert "secrète" not in content
        assert other_invoice.number not in content or other_invoice.number == own.number

    assert len(_table(_download(client, "factures"))) == 2
    assert len(_table(_download(client, "recettes"))) == 1
    assert len(_table(_download(client, "depenses"))) == 1
