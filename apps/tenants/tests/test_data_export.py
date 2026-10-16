import io
import zipfile

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse

from apps.addressbook.factories import ContactFactory, PromoterFactory, VenueFactory
from apps.catalog.factories import ShowFactory
from apps.finance.factories import ExpenseFactory
from apps.finance.tests.helpers import issued_invoice, make_gig

from ..factories import MembershipFactory

pytestmark = pytest.mark.django_db

URL = reverse("tenants:data-export")


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _download(client):
    response = client.post(URL)
    assert response.status_code == 200
    return zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))


def _everything(zf):
    """All the text of the ZIP (names and contents), to look for leaks."""
    parts = list(zf.namelist())
    parts += [zf.read(n).decode("utf-8", "ignore") for n in zf.namelist()]
    return "\n".join(parts)


def test_export_requires_login(client):
    assert client.get(URL).status_code == 302
    assert client.post(URL).status_code == 302


def test_export_page_is_404_without_a_tenant(client):
    from apps.accounts.factories import UserFactory

    client.force_login(UserFactory())

    # No tenant: onboarding redirect on GET, 404 on POST (nothing to export).
    assert client.get(URL).status_code == 302
    assert client.post(URL).status_code == 404


def test_any_member_can_download(client):
    membership = MembershipFactory(role="member")
    client.force_login(membership.user)

    assert client.get(URL).status_code == 200
    assert client.post(URL)["Content-Disposition"].startswith("attachment")


def test_zip_holds_the_tables_and_the_files(client):
    gig = make_gig(gig_fields={"venue__name": "Salle Éole"})
    tenant = gig.tenant
    invoice = issued_invoice(gig)
    show = gig.show
    show.rider_file.save("rider.pdf", ContentFile(b"%PDF rider"))
    expense = ExpenseFactory(gig=gig, label="Essence")
    expense.receipt_file.save("ticket.pdf", ContentFile(b"%PDF ticket"))
    PromoterFactory(tenant=tenant, name="Festival Vent")
    ContactFactory(
        tenant=tenant, name="Zoé Contact", promoter=None, venue=VenueFactory(tenant=tenant)
    )
    ShowFactory(tenant=tenant, title="Autre spectacle")
    client.force_login(MembershipFactory(tenant=tenant).user)

    zf = _download(client)
    names = zf.namelist()

    for table in ("dates", "spectacles", "organisateurs", "lieux", "contacts", "depenses"):
        assert f"{table}.csv" in names
    assert "LISEZMOI.txt" in names
    everything = _everything(zf)
    for expected in ("Salle Éole", "Festival Vent", "Zoé Contact", "Autre spectacle", "Essence"):
        assert expected in everything
    assert invoice.number in zf.read("factures-et-avoirs.csv").decode("utf-8-sig")
    assert any(n.startswith("fichiers/spectacles/") and n.endswith("rider.pdf") for n in names)
    assert any(n.startswith("fichiers/justificatifs/") for n in names)
    assert any(n.startswith("fichiers/factures/") for n in names)


def test_csv_style_is_excel_friendly_and_formula_safe(client):
    gig = make_gig(price="100.60", gig_fields={"conditions": "=HYPERLINK(1)"})
    client.force_login(MembershipFactory(tenant=gig.tenant).user)

    raw = _download(client).read("dates.csv")

    assert raw.startswith(b"\xef\xbb\xbf")
    content = raw.decode("utf-8-sig")
    assert "100,60" in content
    assert ";'=HYPERLINK(1);" in content


def test_a_missing_file_is_reported_not_fatal(client, settings):
    gig = make_gig()
    expense = ExpenseFactory(gig=gig)
    expense.receipt_file.save("ticket.pdf", ContentFile(b"x"))
    expense.receipt_file.delete(save=False)
    expense.receipt_file.name = "expenses/gone/ticket.pdf"
    expense.save()
    client.force_login(MembershipFactory(tenant=gig.tenant).user)

    zf = _download(client)

    assert "introuvables" in zf.read("LISEZMOI.txt").decode()


def test_zip_never_contains_another_tenants_data(client):
    mine = make_gig(gig_fields={"venue__name": "Ma salle"})
    other = make_gig(
        name="Autre Structure SECRETE",
        gig_fields={
            "venue__name": "Salle SECRETE",
            "show__title": "Spectacle SECRET",
        },
    )
    issued_invoice(other)
    PromoterFactory(tenant=other.tenant, name="Organisateur SECRET")
    other.show.rider_file.save("secret-rider.pdf", ContentFile(b"SECRET"))
    expense = ExpenseFactory(gig=other, label="Dépense SECRETE")
    expense.receipt_file.save("secret-ticket.pdf", ContentFile(b"SECRET"))
    ContactFactory(tenant=other.tenant, name="Contact SECRET")
    client.force_login(MembershipFactory(tenant=mine.tenant).user)

    everything = _everything(_download(client))

    assert "Ma salle" in everything
    assert "SECRET" not in everything


def _csv_rows(zf, name):
    import csv

    content = zf.read(name).decode("utf-8-sig")
    return list(csv.reader(io.StringIO(content), delimiter=";"))


def test_zip_holds_the_contracting_checklists(client):
    from apps.gigs import checklist
    from apps.gigs.factories import GigFactory

    gig = make_gig(gig_fields={"show__title": "Concert A"})
    tenant = gig.tenant
    checklist.set_item(gig, "quote_sent", True, None)
    checklist.set_item(gig, "closed", True, None)
    GigFactory(tenant=tenant)  # no checklist: no row
    foreign = make_gig(gig_fields={"show__title": "Concert Autre"})
    checklist.set_item(foreign, "quote_sent", True, None)
    client.force_login(MembershipFactory(tenant=tenant).user)

    zf = _download(client)
    header, *rows = _csv_rows(zf, "checklists-contractualisation.csv")

    assert header[:3] == ["Date", "Spectacle", "Devis envoyé"]
    assert header[-2:] == ["Date clôturée", "Dernière modification"]
    assert len(header) == 2 + 16 + 1
    assert len(rows) == 1
    row = dict(zip(header, rows[0], strict=True))
    assert row["Spectacle"] == "Concert A"
    assert row["Devis envoyé"] == "oui" and row["Date clôturée"] == "oui"
    assert row["Solde reçu"] == "non"
    assert "Concert Autre" not in _everything(zf)
    assert "checklists de contractualisation" in zf.read("LISEZMOI.txt").decode()
