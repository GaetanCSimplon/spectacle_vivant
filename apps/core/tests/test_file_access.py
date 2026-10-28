"""Every stored file (rider, tech sheet, receipt, contract, invoice) is only ever sent by a view
that asks for a login and checks the structure; nothing is served from /media/."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.catalog.factories import ShowFactory
from apps.documents.factories import ContractFactory
from apps.finance.factories import ExpenseFactory
from apps.finance.tests.helpers import issued_invoice
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4 test"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _file(name="doc.pdf"):
    return SimpleUploadedFile(name, PDF)


def _show():
    return ShowFactory(rider_file=_file("rider.pdf"))


def _expense():
    expense = ExpenseFactory()
    expense.receipt_file.save("ticket.pdf", _file("ticket.pdf"))
    return expense


def _signed_contract():
    contract = ContractFactory()
    contract.signed_pdf.save("signe.pdf", _file("signe.pdf"))
    return contract


def _invoice():
    document = issued_invoice()
    document.refresh_from_db()
    return document


# (label, builds the object, builds the URL of the file for that object)
CASES = [
    ("rider", _show, lambda o: reverse("catalog:show-file", args=[o.pk, "rider"])),
    (
        "receipt",
        _expense,
        lambda o: reverse("finance:expense-receipt", args=[o.gig_id, o.pk]),
    ),
    (
        "signed contract",
        _signed_contract,
        lambda o: reverse("documents:contract-signed-pdf", args=[o.gig_id]),
    ),
    (
        "invoice",
        _invoice,
        lambda o: reverse("documents:document-pdf", args=[o.gig_id, "factures", o.pk]),
    ),
]
IDS = [case[0] for case in CASES]


@pytest.mark.parametrize(("label", "build", "url"), CASES, ids=IDS)
def test_a_file_asks_for_a_login(client, label, build, url):
    response = client.get(url(build()))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


@pytest.mark.parametrize(("label", "build", "url"), CASES, ids=IDS)
def test_another_structure_gets_a_404_and_never_the_file(client, label, build, url):
    target = url(build())
    client.force_login(MembershipFactory().user)

    response = client.get(target)

    assert response.status_code == 404


@pytest.mark.parametrize(("label", "build", "url"), CASES, ids=IDS)
def test_the_owner_gets_the_file_as_an_attachment(client, label, build, url):
    obj = build()
    client.force_login(MembershipFactory(tenant=obj.tenant).user)

    response = client.get(url(obj))

    assert response.status_code == 200, label
    assert "attachment" in response["Content-Disposition"]
    assert response["X-Content-Type-Options"] == "nosniff"


def test_nothing_is_served_from_the_media_url(client):
    expense = _expense()
    client.force_login(MembershipFactory(tenant=expense.tenant).user)

    response = client.get(f"/media/{expense.receipt_file.name}")

    assert response.status_code == 404
