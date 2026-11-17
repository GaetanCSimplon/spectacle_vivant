import io

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from pypdf import PdfReader

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

from .. import checks
from ..annexes import MAX_ANNEX_BYTES
from ..factories import make_contract_ready
from ..models import Contract
from ..services import ContractAnnexError, generate_contract_pdf, render_contract_pdf

pytestmark = pytest.mark.django_db


def _pdf_bytes(pages=1):
    from weasyprint import HTML

    html = "".join(f"<p style='page-break-after: always'>Page {n}</p>" for n in range(pages))
    return HTML(string=html).write_pdf()


def _pages(version):
    return len(PdfReader(io.BytesIO(version.pdf_file.read())).pages)


def _gig_with_tech_pdf(pages=2):
    gig = GigFactory()
    gig.show.tech_sheet_file.save("fiche.pdf", ContentFile(_pdf_bytes(pages)))
    return gig


def test_the_single_pdf_holds_the_contract_then_both_annexes():
    gig = _gig_with_tech_pdf(pages=2)
    own_pages = len(PdfReader(io.BytesIO(_pdf_bytes(2))).pages)

    version = generate_contract_pdf(gig).latest_version

    tech, welcome = version.annexes_snapshot
    assert [tech["key"], welcome["key"]] == ["tech_sheet", "welcome_sheet"]
    assert tech["pages"] == own_pages
    assert _pages(version) > tech["pages"] + welcome["pages"]


def test_each_annex_gets_a_title_a_date_and_a_hash():
    gig = _gig_with_tech_pdf()

    tech, welcome = generate_contract_pdf(gig).latest_version.annexes_snapshot

    assert tech["title"].startswith("Fiche technique")
    assert welcome["title"].startswith("Fiche d'accueil")
    assert len(tech["sha256"]) == 64 and tech["date"]


def test_the_hash_changes_when_the_technical_sheet_changes():
    gig = _gig_with_tech_pdf(pages=1)
    first = generate_contract_pdf(gig).latest_version.annexes_snapshot[0]["sha256"]

    gig.show.tech_sheet_file.save("autre.pdf", ContentFile(_pdf_bytes(3)))
    second = generate_contract_pdf(gig).latest_version.annexes_snapshot[0]["sha256"]

    assert first != second


def test_a_text_only_technical_sheet_becomes_an_annex_page():
    gig = GigFactory(show__tech_sheet_text="Scène 6 x 4 m")

    tech = generate_contract_pdf(gig).latest_version.annexes_snapshot[0]

    assert tech["pages"] == 1


def test_the_preview_without_technical_sheet_says_it_is_not_attached():
    gig = GigFactory()

    pdf, annexes = render_contract_pdf(gig)

    assert pdf.startswith(b"%PDF")
    assert annexes["tech_sheet"]["pages"] == 1


def test_the_final_generation_is_blocked_without_technical_sheet(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant)
    make_contract_ready(gig)
    gig.show.tech_sheet_text = ""
    gig.show.save()

    codes = [a.code for a in checks.check_contract(gig)]
    response = client.post(reverse("documents:contract-generate", args=[gig.pk]))

    assert "ANNEXE_FICHE_TECHNIQUE_MANQUANTE" in codes
    assert response.status_code == 302
    assert not Contract.objects.get(gig=gig).versions.exists()


def test_an_unreadable_technical_sheet_stops_the_generation_and_creates_nothing():
    gig = GigFactory()
    gig.show.tech_sheet_file.save("fiche.pdf", ContentFile(b"not a pdf"))

    with pytest.raises(ContractAnnexError):
        generate_contract_pdf(gig)

    assert not Contract.objects.exists()


def test_a_technical_sheet_over_the_limit_is_refused():
    gig = GigFactory()
    gig.show.tech_sheet_file.save("gros.pdf", ContentFile(b"%PDF" + b"0" * MAX_ANNEX_BYTES))

    with pytest.raises(ContractAnnexError):
        generate_contract_pdf(gig)


def test_the_generate_view_shows_the_annex_error(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant)
    make_contract_ready(gig)
    gig.show.tech_sheet_file.save("fiche.pdf", ContentFile(b"not a pdf"))

    response = client.post(reverse("documents:contract-generate", args=[gig.pk]), follow=True)

    assert "PDF lisible" in response.content.decode()


def test_the_article_10_names_the_annexes_with_their_version_date():
    from django.template.loader import render_to_string

    from ..services import build_annexes, build_contract_context

    gig = GigFactory(show__tech_sheet_text="x")
    descriptions, _pdfs = build_annexes(gig)

    html = render_to_string(
        "documents/contracts/contract.html", build_contract_context(gig, annexes=descriptions)
    )

    assert descriptions["tech_sheet"]["title"] in html
    assert f"version du {descriptions['welcome_sheet']['date']}" in html


def test_the_welcome_sheet_says_when_nothing_is_covered_and_what_is_to_be_set():
    from django.template.loader import render_to_string

    gig = GigFactory(get_in_time=None, meals="", lodging="")

    html = render_to_string(
        "documents/contracts/welcome_sheet.html",
        {
            "gig": gig,
            "show": gig.show,
            "venue": gig.venue,
            "promoter": gig.promoter,
            "tenant": gig.tenant,
            "transport_text": "",
        },
    )

    assert html.count("Aucune prise en charge convenue à ce jour") == 3
    assert "À préciser" in html


def test_a_signed_contract_keeps_its_frozen_pdf_with_the_annexes():
    gig = _gig_with_tech_pdf()
    contract = generate_contract_pdf(gig)
    frozen = contract.latest_version.pdf_file.read()
    Contract.objects.filter(pk=contract.pk).update(status=Contract.Status.SIGNED)
    gig.show.tech_sheet_file.save("nouvelle.pdf", ContentFile(_pdf_bytes(5)))

    contract = generate_contract_pdf(gig)

    assert contract.versions.count() == 1
    assert contract.latest_version.pdf_file.read() == frozen


def test_another_tenant_cannot_download_a_version_with_annexes(client):
    gig = _gig_with_tech_pdf()
    generate_contract_pdf(gig)
    client.force_login(MembershipFactory().user)

    response = client.get(reverse("documents:contract-download", args=[gig.pk]))

    assert response.status_code == 404
