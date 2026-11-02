import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.catalog.factories import ShowFactory
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory, TenantFactory
from apps.tenants.models import Tenant

from .. import invoicing
from ..library import DocType, issued_documents
from ..models import Invoice
from ..services import generate_contract_pdf, mark_contract_signed

pytestmark = pytest.mark.django_db

URL = reverse("document-library")
HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _tenant():
    return TenantFactory(
        address="1 rue des Arts, 69001 Lyon",
        siret="12345678900012",
        vat_regime=Tenant.VatRegime.FRANCHISE,
    )


def _gig(tenant, show=None, **fields):
    extra = {"show": show} if show else {}
    gig = GigFactory(
        tenant=tenant,
        price="1000.00",
        promoter__billing_address="3 place de la Mairie, Nîmes",
        **extra,
        **fields,
    )
    gig.refresh_from_db()
    return gig


def _invoice(gig, issued_on=None):
    invoice = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.FULL))
    return _on(invoice, issued_on)


def _quote(gig, issued_on=None):
    return _on(invoicing.issue_quote(invoicing.create_quote(gig)), issued_on)


def _on(document, day):
    """Move the issue date (an issued document is immutable: write around the model)."""
    if day:
        type(document).objects.filter(pk=document.pk).update(issue_date=day)
        document.refresh_from_db()
    return document


def _credit_note(invoice):
    return invoicing.issue_invoice(invoicing.create_credit_note(invoice))


def _signed_contract(tenant, show=None):
    gig = _gig(tenant, show=show, status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)
    return mark_contract_signed(gig)


def _login(client, tenant=None):
    tenant = tenant or _tenant()
    membership = MembershipFactory(tenant=tenant)
    client.force_login(membership.user)
    return tenant


# --- what is listed ---------------------------------------------------------


def test_lists_every_kind_of_issued_document_newest_first():
    tenant = _tenant()
    gig = _gig(tenant)
    invoice = _invoice(gig, datetime.date(2026, 9, 10))
    credit_note = _credit_note(invoice)
    _on(credit_note, datetime.date(2026, 9, 20))
    quote = _quote(gig, datetime.date(2026, 9, 1))
    contract = _signed_contract(tenant)

    rows = issued_documents(tenant)

    assert {row.doc_type for row in rows} == {
        DocType.INVOICE,
        DocType.CREDIT_NOTE,
        DocType.QUOTE,
        DocType.CONTRACT,
    }
    assert [row.date for row in rows] == sorted((row.date for row in rows), reverse=True)
    by_type = {row.doc_type: row for row in rows}
    assert by_type[DocType.INVOICE].number == invoice.number
    assert by_type[DocType.QUOTE].number == quote.number
    assert by_type[DocType.CREDIT_NOTE].amount_incl_tax < 0
    assert by_type[DocType.CONTRACT].number == contract.reference
    assert by_type[DocType.CONTRACT].amount_incl_tax is None


def test_drafts_and_unsigned_contracts_are_left_out():
    tenant = _tenant()
    gig = _gig(tenant, status=Gig.Status.CONFIRMED)
    invoicing.create_invoice(gig, Invoice.Kind.FULL)
    invoicing.create_quote(gig)
    generate_contract_pdf(gig)

    assert issued_documents(tenant) == []


def test_a_paid_invoice_is_still_listed():
    tenant = _tenant()
    invoice = _invoice(_gig(tenant))
    Invoice.objects.filter(pk=invoice.pk).update(status=Invoice.Status.PAID)

    assert [row.number for row in issued_documents(tenant)] == [invoice.number]


def test_download_links_point_to_the_stored_pdfs(client):
    tenant = _login(client)
    invoice = _invoice(_gig(tenant))
    contract = _signed_contract(tenant)

    rows = {row.doc_type: row for row in issued_documents(tenant)}

    assert client.get(rows[DocType.INVOICE].download_url).status_code == 200
    assert rows[DocType.INVOICE].number == invoice.number
    response = client.get(rows[DocType.CONTRACT].download_url)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert contract.signed_version is not None


# --- filters ----------------------------------------------------------------


def test_filter_by_type():
    tenant = _tenant()
    gig = _gig(tenant)
    _invoice(gig)
    _quote(gig)

    rows = issued_documents(tenant, types=[DocType.QUOTE])

    assert [row.doc_type for row in rows] == [DocType.QUOTE]


def test_credit_notes_are_a_type_of_their_own():
    tenant = _tenant()
    invoice = _invoice(_gig(tenant))
    _credit_note(invoice)

    assert [r.doc_type for r in issued_documents(tenant, types=[DocType.INVOICE])] == [
        DocType.INVOICE
    ]
    assert [r.doc_type for r in issued_documents(tenant, types=[DocType.CREDIT_NOTE])] == [
        DocType.CREDIT_NOTE
    ]


def test_filter_by_period_includes_both_bounds():
    tenant = _tenant()
    gig = _gig(tenant)
    before = _invoice(gig, datetime.date(2026, 8, 31))
    first = _quote(gig, datetime.date(2026, 9, 1))
    last = _quote(gig, datetime.date(2026, 9, 30))
    after = _invoice(gig, datetime.date(2026, 10, 1))

    rows = issued_documents(tenant, start=datetime.date(2026, 9, 1), end=datetime.date(2026, 9, 30))

    numbers = {row.number for row in rows}
    assert numbers == {first.number, last.number}
    assert before.number not in numbers and after.number not in numbers


def test_period_applies_to_the_signature_day_of_a_contract():
    tenant = _tenant()
    contract = _signed_contract(tenant)
    signed_day = timezone.localtime(contract.signed_at).date()
    day = datetime.timedelta(days=1)

    assert len(issued_documents(tenant, start=signed_day, end=signed_day)) == 1
    assert issued_documents(tenant, start=signed_day + day) == []
    assert issued_documents(tenant, end=signed_day - day) == []


def test_filter_by_one_or_several_shows():
    tenant = _tenant()
    show_a, show_b, show_c = (ShowFactory(tenant=tenant) for _ in range(3))
    for show in (show_a, show_b, show_c):
        _quote(_gig(tenant, show=show))
    _signed_contract(tenant, show=show_a)

    assert len(issued_documents(tenant, shows=[show_a])) == 2
    assert len(issued_documents(tenant, shows=[show_a, show_b])) == 3
    assert len(issued_documents(tenant)) == 4


# --- page -------------------------------------------------------------------


def test_page_requires_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert "/connexion/" in response["Location"] or "login" in response["Location"]


def test_page_lists_documents_and_shows_the_tab_as_current(client):
    tenant = _login(client)
    invoice = _invoice(_gig(tenant))

    response = client.get(URL)

    assert response.status_code == 200
    assert invoice.number in response.content.decode()
    assert 'aria-current="page"' in response.content.decode()


def test_empty_page_explains_itself(client):
    _login(client)

    response = client.get(URL)

    assert "Aucun document émis" in response.content.decode()


def test_filters_through_the_query_string(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice, quote = _invoice(gig), _quote(gig)

    response = client.get(URL, {"types": [DocType.QUOTE]})

    content = response.content.decode()
    assert quote.number in content and invoice.number not in content


def test_no_result_message_offers_to_reset(client):
    tenant = _login(client)
    _invoice(_gig(tenant))

    response = client.get(URL, {"start": "2000-01-01", "end": "2000-01-31"})

    assert "Aucun document ne correspond" in response.content.decode()


def test_end_before_start_shows_an_error_and_ignores_the_end(client):
    tenant = _login(client)
    invoice = _invoice(_gig(tenant))

    response = client.get(URL, {"start": "2000-01-02", "end": "2000-01-01"})

    content = response.content.decode()
    assert "après la date de début" in content
    assert invoice.number in content


def test_invalid_values_are_ignored(client):
    tenant = _login(client)
    invoice = _invoice(_gig(tenant))

    response = client.get(URL, {"types": ["nope"], "start": "not-a-date", "shows": ["abc"]})

    assert response.status_code == 200
    assert invoice.number in response.content.decode()


def test_htmx_request_gets_only_the_results(client):
    _login(client)

    response = client.get(URL, **HTMX)

    assert "<html" not in response.content.decode()


# --- isolation --------------------------------------------------------------


def test_documents_do_not_mix_between_tenants(client):
    tenant_a, tenant_b = _tenant(), _tenant()
    gig_a = _gig(tenant_a)
    _invoice(gig_a)
    _quote(gig_a)
    _signed_contract(tenant_a)
    gig_b = _gig(tenant_b)
    _invoice(gig_b)

    assert len(issued_documents(tenant_a)) == 3
    assert {row.gig.pk for row in issued_documents(tenant_b)} == {gig_b.pk}
    _login(client, tenant_b)
    response = client.get(URL)
    # Numbers restart for each tenant, so the gigs tell the documents apart.
    assert [row.gig.pk for row in response.context["documents"]] == [gig_b.pk]


def test_another_tenants_show_in_the_filter_is_ignored(client):
    tenant_a, tenant_b = _tenant(), _tenant()
    show_a = ShowFactory(tenant=tenant_a)
    _quote(_gig(tenant_a, show=show_a))
    invoice_b = _invoice(_gig(tenant_b))
    _login(client, tenant_b)

    response = client.get(URL, {"shows": [show_a.pk]})

    content = response.content.decode()
    assert response.context["filter_form"].errors.get("shows")
    # The invalid choice is dropped: B only ever sees their own document.
    assert invoice_b.number in content
    assert len(response.context["documents"]) == 1


def test_other_tenants_download_links_are_not_reachable(client):
    tenant_a, tenant_b = _tenant(), _tenant()
    _invoice(_gig(tenant_a))
    _signed_contract(tenant_a)
    links = [row.download_url for row in issued_documents(tenant_a)]
    _login(client, tenant_b)

    assert all(client.get(link).status_code == 404 for link in links)
