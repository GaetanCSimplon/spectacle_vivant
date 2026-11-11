from decimal import Decimal

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory
from apps.tenants.models import Tenant

from .. import invoicing
from ..models import DocumentLine, Invoice, Quote

pytestmark = pytest.mark.django_db

D = Decimal
HTMX = {"HTTP_HX_REQUEST": "true"}


def _login(client, **tenant_fields):
    defaults = {
        "address": "1 rue des Arts, 69001 Lyon",
        "siret": "12345678900012",
        "vat_regime": Tenant.VatRegime.FRANCHISE,
    }
    defaults.update(tenant_fields)
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in defaults.items()})
    client.force_login(membership.user)
    return membership.tenant


def _gig(tenant):
    gig = GigFactory(
        tenant=tenant, price="1000.00", promoter__billing_address="3 place de la Mairie, Nîmes"
    )
    gig.refresh_from_db()
    return gig


def _url(name, gig, *args):
    return reverse(f"documents:{name}", args=[gig.pk, *args])


def _draft(gig, kind=Invoice.Kind.FULL):
    return invoicing.create_invoice(gig, kind)


def _issued(gig, kind=Invoice.Kind.FULL):
    return invoicing.issue_invoice(invoicing.create_invoice(gig, kind))


def _detail(gig, document):
    doc_type = "factures" if isinstance(document, Invoice) else "devis"
    return _url("document-detail", gig, doc_type, document.pk)


# --- billing page and creation --------------------------------------------


def test_billing_page_shows_the_amounts_and_the_documents(client):
    tenant = _login(client)
    gig = _gig(tenant)
    _issued(gig, Invoice.Kind.DEPOSIT)

    content = client.get(_url("billing", gig)).content.decode()

    assert "1000.00" in content or "1000,00" in content
    assert "300,00" in content
    assert "700,00" in content
    assert f"F-{invoicing.timezone.localdate().year}-0001" in content


def test_gig_detail_links_to_the_billing_page(client):
    tenant = _login(client)
    gig = _gig(tenant)

    response = client.get(reverse("gigs:detail", args=[gig.pk]))

    assert _url("billing", gig) in response.content.decode()


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("acompte", "300,00"), ("solde", "1000,00"), ("totale", "1000,00")],
)
def test_creating_an_invoice_starts_a_draft_with_the_suggested_line(client, kind, expected):
    tenant = _login(client)
    gig = _gig(tenant)

    response = client.post(_url("invoice-create", gig, kind))

    invoice = Invoice.objects.get(gig=gig)
    assert response.status_code == 302
    assert response.url == _detail(gig, invoice)
    assert invoice.is_draft
    assert expected in client.get(response.url).content.decode()


def test_creating_a_quote(client):
    tenant = _login(client)
    gig = _gig(tenant)

    response = client.post(_url("quote-create", gig))

    quote = Quote.objects.get(gig=gig)
    assert response.url == _detail(gig, quote)
    assert quote.total_excl_tax == D("1000.00")


def test_unknown_invoice_kind_is_404_and_creation_is_post_only(client):
    tenant = _login(client)
    gig = _gig(tenant)

    assert client.post(_url("invoice-create", gig, "bidon")).status_code == 404
    assert client.post(_url("invoice-create", gig, "credit_note")).status_code == 404
    assert client.get(_url("invoice-create", gig, "acompte")).status_code == 405
    assert client.get(_url("quote-create", gig)).status_code == 405
    assert not Invoice.objects.exists()


# --- draft page, lines -----------------------------------------------------


def test_draft_page_lists_what_is_missing_and_hides_the_issue_button(client):
    tenant = _login(client, address="", siret="")
    gig = GigFactory(tenant=tenant, price="100.00")
    invoice = _draft(gig)

    content = client.get(_detail(gig, invoice)).content.decode()

    assert "adresse de votre structure" in content
    assert "adresse de facturation" in content
    assert _url("document-issue", gig, "factures", invoice.pk) not in content


def test_complete_draft_offers_to_issue(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)

    content = client.get(_detail(gig, invoice)).content.decode()

    assert _url("document-issue", gig, "factures", invoice.pk) in content
    assert "Ajouter une ligne" in content


def test_the_vat_field_only_exists_for_a_taxable_tenant(client):
    franchise = _login(client)
    gig = _gig(franchise)
    invoice = _draft(gig)
    assert 'name="vat_rate"' not in client.get(_detail(gig, invoice)).content.decode()

    taxable = _login(client, vat_regime="taxable", vat_rate="20", vat_number="FR1")
    gig = _gig(taxable)
    invoice = _draft(gig)
    assert 'name="vat_rate"' in client.get(_detail(gig, invoice)).content.decode()


def _line_data(**overrides):
    data = {"label": "Transport", "quantity": "2", "unit_price_excl_tax": "40.50"}
    data.update(overrides)
    return data


def test_adding_a_line_with_htmx_returns_the_updated_block(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)

    response = client.post(_url("line-add", gig, "factures", invoice.pk), _line_data(), **HTMX)

    content = response.content.decode()
    assert response.status_code == 200
    assert '<div id="lines"' in content
    assert "<html" not in content
    assert "Transport" in content
    invoice.refresh_from_db()
    assert invoice.total_excl_tax == D("1081.00")
    assert "1081,00" in content


def test_adding_a_line_without_htmx_redirects_to_the_page(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)

    response = client.post(_url("line-add", gig, "factures", invoice.pk), _line_data())

    assert response.status_code == 302
    assert response.url == _detail(gig, invoice)
    assert invoice.lines.count() == 2


@pytest.mark.parametrize(
    "bad",
    [
        {"label": ""},
        {"quantity": "0"},
        {"quantity": "abc"},
        {"unit_price_excl_tax": ""},
        {"unit_price_excl_tax": "1.234"},
    ],
)
def test_an_invalid_line_is_not_added_and_the_form_shows_errors(client, bad):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)

    response = client.post(_url("line-add", gig, "factures", invoice.pk), _line_data(**bad), **HTMX)

    assert response.status_code == 200
    assert "errorlist" in response.content.decode()
    assert invoice.lines.count() == 1


def test_a_franchise_tenant_cannot_force_vat_on_a_line(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)

    client.post(_url("line-add", gig, "factures", invoice.pk), _line_data(vat_rate="20"))

    assert set(invoice.lines.values_list("vat_rate", flat=True)) == {D("0.00")}


def test_editing_a_line(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)
    line = invoice.lines.get()
    url = _url("line-edit", gig, "factures", invoice.pk, line.pk)

    form = client.get(url, **HTMX)
    response = client.post(
        url,
        {
            f"line{line.pk}-label": "Prix négocié",
            f"line{line.pk}-quantity": "1",
            f"line{line.pk}-unit_price_excl_tax": "900.00",
        },
        **HTMX,
    )

    assert f'name="line{line.pk}-label"' in form.content.decode()
    assert response.status_code == 200
    line.refresh_from_db()
    invoice.refresh_from_db()
    assert line.label == "Prix négocié"
    assert invoice.total_excl_tax == D("900.00")


def test_an_invalid_edit_keeps_the_line_and_shows_the_form_again(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)
    line = invoice.lines.get()

    response = client.post(
        _url("line-edit", gig, "factures", invoice.pk, line.pk),
        {
            f"line{line.pk}-label": "",
            f"line{line.pk}-quantity": "1",
            f"line{line.pk}-unit_price_excl_tax": "1",
        },
        **HTMX,
    )

    assert "errorlist" in response.content.decode()
    line.refresh_from_db()
    assert line.unit_price_excl_tax == D("1000.00")


def test_removing_a_line(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)
    line = invoice.lines.get()

    response = client.post(_url("line-remove", gig, "factures", invoice.pk, line.pk), **HTMX)

    assert response.status_code == 200
    assert invoice.lines.count() == 0
    invoice.refresh_from_db()
    assert invoice.total_excl_tax == D("0.00")


def test_line_actions_are_post_only_where_they_change_data(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)
    line = invoice.lines.get()

    assert client.get(_url("line-remove", gig, "factures", invoice.pk, line.pk)).status_code == 405
    assert client.get(_url("line-add", gig, "factures", invoice.pk)).status_code == 405
    assert invoice.lines.count() == 1


def test_an_issued_document_cannot_be_edited_through_the_views(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _issued(gig)
    line = invoice.lines.get()

    client.post(_url("line-add", gig, "factures", invoice.pk), _line_data())
    client.post(_url("line-remove", gig, "factures", invoice.pk, line.pk))
    client.post(
        _url("line-edit", gig, "factures", invoice.pk, line.pk),
        {
            f"line{line.pk}-label": "x",
            f"line{line.pk}-quantity": "1",
            f"line{line.pk}-unit_price_excl_tax": "1",
        },
    )

    assert invoice.lines.get().unit_price_excl_tax == D("1000.00")
    assert invoice.lines.count() == 1


def test_an_issued_page_is_read_only_and_shows_the_frozen_data(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _issued(gig)
    tenant.name = "Nom modifié après coup"
    tenant.save()

    content = client.get(_detail(gig, invoice)).content.decode()

    # The left column shows the live name of the structure; the document itself must not.
    assert "Nom modifié après coup" not in content.split("<main")[1]
    assert "Ajouter une ligne" not in content
    assert "Supprimer le brouillon" not in content
    assert "Émettre" not in content
    assert invoice.number in content


# --- issuing ---------------------------------------------------------------


def test_issue_asks_for_confirmation_then_issues(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)
    url = _url("document-issue", gig, "factures", invoice.pk)

    page = client.get(url)
    response = client.post(url)

    assert "ne pourra plus être modifié" in page.content.decode()
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.ISSUED
    assert invoice.number
    assert response.url == _detail(gig, invoice)


def test_issuing_an_invoice_on_an_option_warns_without_blocking(client):
    tenant = _login(client)
    gig = _gig(tenant)
    gig.status = Gig.Status.OPTION
    gig.save()
    invoice = _draft(gig)
    url = _url("document-issue", gig, "factures", invoice.pk)

    page = client.get(url)
    response = client.post(url, follow=True)

    assert "encore une option" in page.content.decode()
    assert "encore une option" in response.content.decode()
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.ISSUED


def test_a_quote_or_a_confirmed_date_gets_no_option_warning(client):
    tenant = _login(client)
    gig = _gig(tenant)
    gig.status = Gig.Status.CONFIRMED
    gig.save()
    quote_page = client.get(_url("document-issue", gig, "devis", invoicing.create_quote(gig).pk))
    gig.status = Gig.Status.OPTION
    gig.save()
    option_quote_page = client.get(
        _url("document-issue", gig, "devis", invoicing.create_quote(gig).pk)
    )
    gig.status = Gig.Status.CONFIRMED
    gig.save()
    invoice_page = client.get(_url("document-issue", gig, "factures", _draft(gig).pk))

    for page in (quote_page, option_quote_page, invoice_page):
        assert page.status_code == 200
        assert "encore une option" not in page.content.decode()


def test_issuing_twice_does_not_consume_a_second_number(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)
    url = _url("document-issue", gig, "factures", invoice.pk)

    client.post(url)
    client.post(url)

    assert invoicing.DocumentSequence.objects.get(tenant=tenant).last_number == 1


def test_issue_is_refused_when_something_is_missing(client):
    tenant = _login(client, siret="")
    gig = _gig(tenant)
    invoice = _draft(gig)
    url = _url("document-issue", gig, "factures", invoice.pk)

    assert client.get(url).status_code == 302
    response = client.post(url, follow=True)

    assert "SIRET" in response.content.decode()
    invoice.refresh_from_db()
    assert invoice.is_draft


def test_a_quote_can_be_issued(client):
    tenant = _login(client)
    gig = _gig(tenant)
    quote = invoicing.create_quote(gig)

    client.post(_url("document-issue", gig, "devis", quote.pk))

    quote.refresh_from_db()
    assert quote.status == Quote.Status.ISSUED
    assert quote.number.startswith("D-")


# --- delete ----------------------------------------------------------------


def test_a_draft_can_be_deleted(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)

    response = client.post(_url("document-delete", gig, "factures", invoice.pk))

    assert response.url == _url("billing", gig)
    assert not Invoice.objects.exists()
    assert not DocumentLine.objects.exists()


def test_an_issued_document_cannot_be_deleted(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _issued(gig)

    client.post(_url("document-delete", gig, "factures", invoice.pk))
    assert client.get(_url("document-delete", gig, "factures", invoice.pk)).status_code == 405

    assert Invoice.objects.filter(pk=invoice.pk).exists()


# --- credit notes ----------------------------------------------------------


def test_credit_note_button_only_on_an_issued_invoice(client):
    tenant = _login(client)
    gig = _gig(tenant)
    draft = _draft(gig)
    issued = _issued(gig)

    assert "Créer un avoir" not in client.get(_detail(gig, draft)).content.decode()
    assert "Créer un avoir" in client.get(_detail(gig, issued)).content.decode()


def test_creating_then_issuing_a_credit_note_through_the_views(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _issued(gig)

    response = client.post(reverse("documents:credit-note-create", args=[gig.pk, invoice.pk]))
    note = Invoice.objects.get(kind=Invoice.Kind.CREDIT_NOTE)
    client.post(_url("document-issue", gig, "factures", note.pk))

    assert response.url == _detail(gig, note)
    note.refresh_from_db()
    invoice.refresh_from_db()
    assert note.total_incl_tax == D("-1000.00")
    assert invoice.status == Invoice.Status.CANCELLED
    page = client.get(_detail(gig, invoice)).content.decode()
    assert "Créer un avoir" not in page
    assert note.number in page


def test_credit_note_is_refused_for_a_draft_or_a_credit_note(client):
    tenant = _login(client)
    gig = _gig(tenant)
    draft = _draft(gig)

    response = client.post(reverse("documents:credit-note-create", args=[gig.pk, draft.pk]))

    assert response.status_code == 302
    assert not Invoice.objects.filter(kind=Invoice.Kind.CREDIT_NOTE).exists()
    assert (
        client.get(reverse("documents:credit-note-create", args=[gig.pk, draft.pk])).status_code
        == 405
    )


# --- access ----------------------------------------------------------------


def _all_urls(gig, invoice, line):
    base = ("factures", invoice.pk)
    return [
        ("get", _url("billing", gig)),
        ("post", _url("quote-create", gig)),
        ("post", _url("invoice-create", gig, "acompte")),
        ("get", _url("document-detail", gig, *base)),
        ("post", _url("line-add", gig, *base)),
        ("get", _url("line-edit", gig, *base, line.pk)),
        ("post", _url("line-edit", gig, *base, line.pk)),
        ("post", _url("line-remove", gig, *base, line.pk)),
        ("get", _url("document-issue", gig, *base)),
        ("post", _url("document-issue", gig, *base)),
        ("post", _url("document-delete", gig, *base)),
        ("post", reverse("documents:credit-note-create", args=[gig.pk, invoice.pk])),
    ]


def test_every_billing_page_requires_login(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)
    urls = _all_urls(gig, invoice, invoice.lines.get())
    client.logout()

    for method, url in urls:
        response = getattr(client, method)(url)
        assert response.status_code == 302, url
        assert response.url.startswith(reverse("account_login")), url


def test_another_tenant_gets_404_everywhere_and_nothing_changes(client):
    other_gig = _gig(MembershipFactory().tenant)
    invoice = _draft(other_gig)
    line = invoice.lines.get()
    _login(client)

    for method, url in _all_urls(other_gig, invoice, line):
        assert getattr(client, method)(url).status_code == 404, url

    invoice.refresh_from_db()
    assert invoice.is_draft
    assert invoice.lines.count() == 1
    assert Invoice.objects.count() == 1
    assert Quote.objects.count() == 0


def test_a_document_is_not_reachable_through_another_gig_of_the_same_tenant(client):
    tenant = _login(client)
    gig, other_gig = _gig(tenant), _gig(tenant)
    invoice = _draft(gig)

    assert client.get(_detail(other_gig, invoice)).status_code == 404
    line = invoice.lines.get()
    response = client.post(_url("line-remove", other_gig, "factures", invoice.pk, line.pk))
    assert response.status_code == 404
    assert invoice.lines.count() == 1


def test_a_line_of_another_document_is_not_reachable(client):
    tenant = _login(client)
    gig = _gig(tenant)
    first, second = _draft(gig), _draft(gig)
    line = second.lines.get()

    response = client.post(_url("line-remove", gig, "factures", first.pk, line.pk))

    assert response.status_code == 404
    assert second.lines.count() == 1


def test_a_quote_url_does_not_open_an_invoice(client):
    tenant = _login(client)
    gig = _gig(tenant)
    invoice = _draft(gig)

    assert client.get(_url("document-detail", gig, "devis", invoice.pk)).status_code == 404


# --- internal title ---------------------------------------------------------


def _title_url(gig, document):
    doc_type = "factures" if isinstance(document, Invoice) else "devis"
    return _url("document-title", gig, doc_type, document.pk)


def test_a_draft_can_be_named_and_the_name_is_listed(client):
    gig = _gig(_login(client))
    quote = invoicing.create_quote(gig)

    response = client.post(_title_url(gig, quote), {"title": "  Devis   tournée automne "})

    assert response.status_code == 302
    quote.refresh_from_db()
    assert quote.title == "Devis tournée automne"
    assert "Devis tournée automne" in client.get(_url("billing", gig)).content.decode()
    assert "Devis tournée automne" in client.get(_detail(gig, quote)).content.decode()


def test_an_issued_invoice_can_still_be_renamed_but_nothing_else_changes(client):
    gig = _gig(_login(client, siret="12345678900012"))
    invoice = _issued(gig)
    before = Invoice.objects.get(pk=invoice.pk)

    client.post(_title_url(gig, invoice), {"title": "Acompte Mairie"})

    after = Invoice.objects.get(pk=invoice.pk)
    assert after.title == "Acompte Mairie"
    assert (after.number, after.total_incl_tax, after.issuer_snapshot, after.status) == (
        before.number,
        before.total_incl_tax,
        before.issuer_snapshot,
        before.status,
    )


def test_the_title_is_not_printed_on_the_pdf_page(client):
    gig = _gig(_login(client))
    invoice = _issued(gig)
    client.post(_title_url(gig, invoice), {"title": "Nom très interne"})

    html = render_to_string("documents/billing_pdf.html", invoicing.build_pdf_context(invoice))

    assert "Nom très interne" not in html


def test_the_name_can_be_cleared_and_a_too_long_one_is_refused(client):
    gig = _gig(_login(client))
    quote = invoicing.create_quote(gig)
    client.post(_title_url(gig, quote), {"title": "Un nom"})

    client.post(_title_url(gig, quote), {"title": "x" * 101})
    quote.refresh_from_db()
    assert quote.title == "Un nom"

    client.post(_title_url(gig, quote), {"title": ""})
    quote.refresh_from_db()
    assert quote.title == ""


def test_naming_is_post_only_and_needs_login(client):
    gig = _gig(_login(client))
    quote = invoicing.create_quote(gig)
    assert client.get(_title_url(gig, quote)).status_code == 405
    client.logout()
    response = client.post(_title_url(gig, quote), {"title": "x"})
    assert response.url.startswith(reverse("account_login"))
    quote.refresh_from_db()
    assert quote.title == ""


def test_another_tenant_cannot_rename_a_document(client):
    gig = _gig(_login(client))
    quote = invoicing.create_quote(gig)
    _login(client)

    assert client.post(_title_url(gig, quote), {"title": "pirate"}).status_code == 404
    quote.refresh_from_db()
    assert quote.title == ""
