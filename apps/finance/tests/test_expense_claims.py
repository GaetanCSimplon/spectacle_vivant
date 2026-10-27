"""Expenses declared by a team member (a secret link, no account), then checked by the owner."""

import datetime
import zipfile
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.tenants import services as tenant_services
from apps.tenants.data_export import build_export_zip
from apps.tenants.factories import MembershipFactory, PersonFactory
from apps.tenants.models import Person

from .. import bord, services
from ..factories import ExpenseClaimFactory
from ..models import Expense, ExpenseClaim
from .helpers import TENANT_FIELDS

pytestmark = pytest.mark.django_db

D = Decimal
TODAY = timezone.localdate()
PDF = b"%PDF-1.4 recu"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _days(n):
    return TODAY + datetime.timedelta(days=n)


def _person_with_space(**fields):
    person = PersonFactory(**fields)
    tenant_services.enable_team_space(person)
    person.refresh_from_db()
    return person


def _on_gig(person, days=2, **gig_fields):
    gig = GigFactory(tenant=person.tenant, date=_days(days), **gig_fields)
    GigMemberFactory(gig=gig, tenant=person.tenant, person=person, name=person.full_name)
    return gig


def _data(gig, **extra):
    return {
        "gig": gig.pk,
        "category": "transport",
        "label": "Essence",
        "amount": "40.00",
        "date": TODAY.isoformat(),
        **extra,
    }


def _url(name, person, *args):
    return reverse(name, args=[person.access_token, *args])


def _receipt(name="ticket.pdf", content=PDF):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


@pytest.fixture
def owner(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    return membership.tenant


# --- declaring ----------------------------------------------------------------------------


def test_the_page_offers_only_my_own_dates_and_no_fee_category(client):
    person = _person_with_space()
    mine = _on_gig(person, show__title="Mon spectacle")
    theirs = _on_gig(PersonFactory(tenant=person.tenant), show__title="Celui d'un collègue")

    page = client.get(_url("team-expenses", person)).content.decode()

    assert "Mon spectacle" in page and "collègue" not in page
    assert f'value="{mine.pk}"' in page and f'value="{theirs.pk}"' not in page
    assert "Cachets" not in page and "Transport" in page


def test_a_member_declares_an_expense_with_a_receipt(client):
    person = _person_with_space()
    gig = _on_gig(person)

    response = client.post(
        _url("team-expenses", person), {**_data(gig), "receipt_file": _receipt()}
    )

    assert response.status_code == 302
    claim = ExpenseClaim.objects.get()
    assert (claim.person, claim.gig, claim.tenant) == (person, gig, person.tenant)
    assert claim.status == ExpenseClaim.Status.PENDING and claim.amount == D("40.00")
    assert claim.receipt_file
    assert not Expense.objects.exists()  # nothing counts until the owner accepts


def test_the_receipt_is_optional(client):
    person = _person_with_space()
    gig = _on_gig(person)

    client.post(_url("team-expenses", person), _data(gig))

    assert not ExpenseClaim.objects.get().receipt_file


@pytest.mark.parametrize(
    "bad",
    [
        {"amount": "0"},
        {"amount": "-5"},
        {"amount": "abc"},
        {"label": ""},
        {"category": "fees"},
        {"category": "nope"},
        {"date": (TODAY + datetime.timedelta(days=3)).isoformat()},
    ],
)
def test_invalid_data_is_refused(client, bad):
    person = _person_with_space()
    gig = _on_gig(person)

    response = client.post(_url("team-expenses", person), _data(gig, **bad))

    assert response.status_code == 422
    assert not ExpenseClaim.objects.exists()


def test_a_date_of_somebody_else_cannot_be_posted(client):
    person = _person_with_space()
    colleague_gig = _on_gig(PersonFactory(tenant=person.tenant))
    foreign_gig = GigFactory(date=_days(1))

    for gig in (colleague_gig, foreign_gig):
        response = client.post(_url("team-expenses", person), _data(gig))
        assert response.status_code == 422
    assert not ExpenseClaim.objects.exists()


def test_a_receipt_must_really_be_a_pdf_or_an_image(client):
    person = _person_with_space()
    gig = _on_gig(person)
    fake = SimpleUploadedFile("virus.pdf", b"MZ not a pdf", content_type="application/pdf")

    response = client.post(_url("team-expenses", person), {**_data(gig), "receipt_file": fake})

    assert response.status_code == 422 and not ExpenseClaim.objects.exists()


def test_a_receipt_over_10_mb_is_refused(client):
    person = _person_with_space()
    gig = _on_gig(person)
    big = SimpleUploadedFile("gros.pdf", PDF + b"0" * (10 * 1024 * 1024), "application/pdf")

    response = client.post(_url("team-expenses", person), {**_data(gig), "receipt_file": big})

    assert response.status_code == 422 and not ExpenseClaim.objects.exists()


def test_too_many_waiting_proposals_are_refused(client):
    person = _person_with_space()
    gig = _on_gig(person)
    for _i in range(services.MAX_PENDING_CLAIMS):
        ExpenseClaimFactory(gig=gig, person=person)

    response = client.post(_url("team-expenses", person), _data(gig))

    assert response.status_code == 422
    assert ExpenseClaim.objects.count() == services.MAX_PENDING_CLAIMS


def test_a_dead_link_cannot_declare_anything(client):
    person = _person_with_space()
    gig = _on_gig(person)
    token = person.access_token
    tenant_services.disable_team_space(person)

    response = client.post(reverse("team-expenses", args=[token]), _data(gig))

    assert response.status_code == 404 and not ExpenseClaim.objects.exists()


def test_the_page_is_kept_out_of_caches_and_keeps_csrf_working(client):
    person = _person_with_space()

    response = client.get(_url("team-expenses", person))

    assert response["Cache-Control"] == "no-store" and "noindex" in response["X-Robots-Tag"]
    assert response["Referrer-Policy"] == "same-origin"  # "no-referrer" would break the CSRF check


# --- my declarations ----------------------------------------------------------------------


def test_my_declarations_show_their_state(client):
    person = _person_with_space()
    gig = _on_gig(person)
    ExpenseClaimFactory(gig=gig, person=person, label="En attente")
    refused = ExpenseClaimFactory(gig=gig, person=person, label="Refusée ici")
    services.refuse_claim(refused)
    accepted = ExpenseClaimFactory(gig=gig, person=person, label="Validée ici")
    services.accept_claim(accepted)

    page = client.get(_url("team-expenses", person)).content.decode()

    assert "En attente de validation" in page and "Refusée" in page
    assert "Validée" in page and "À rembourser" in page


def test_a_reimbursed_claim_says_so(client):
    person = _person_with_space()
    claim = ExpenseClaimFactory(gig=_on_gig(person), person=person)
    expense = services.accept_claim(claim)
    services.set_reimbursed(expense, True)

    page = client.get(_url("team-expenses", person)).content.decode()

    assert "Remboursée le" in page


def test_i_never_see_anyone_elses_declarations(client):
    person = _person_with_space()
    colleague = PersonFactory(tenant=person.tenant)
    ExpenseClaimFactory(gig=_on_gig(colleague), person=colleague, label="Secret du collègue")

    assert "Secret du collègue" not in client.get(_url("team-expenses", person)).content.decode()


def test_i_can_correct_or_withdraw_a_waiting_proposal(client):
    person = _person_with_space()
    gig = _on_gig(person)
    claim = ExpenseClaimFactory(gig=gig, person=person, amount="10.00")
    claim.receipt_file.save("ancien.pdf", SimpleUploadedFile("ancien.pdf", PDF))
    old = claim.receipt_file.path

    client.post(
        _url("team-expense-edit", person, claim.pk),
        {**_data(gig), "amount": "12.50", "receipt_file": _receipt("nouveau.pdf")},
    )
    claim.refresh_from_db()
    assert claim.amount == D("12.50") and claim.receipt_file.name.endswith("nouveau.pdf")
    import os

    assert not os.path.exists(old)

    client.post(_url("team-expense-delete", person, claim.pk))
    assert not ExpenseClaim.objects.exists()


def test_a_decided_proposal_can_no_longer_be_changed(client):
    person = _person_with_space()
    gig = _on_gig(person)
    claim = ExpenseClaimFactory(gig=gig, person=person)
    services.accept_claim(claim)

    for name in ("team-expense-edit", "team-expense-delete"):
        assert client.post(_url(name, person, claim.pk), _data(gig)).status_code == 404
    assert client.get(_url("team-expense-edit", person, claim.pk)).status_code == 404
    assert ExpenseClaim.objects.filter(pk=claim.pk).exists()


def test_i_cannot_touch_the_proposal_of_a_colleague(client):
    person = _person_with_space()
    colleague = PersonFactory(tenant=person.tenant)
    claim = ExpenseClaimFactory(gig=_on_gig(colleague), person=colleague)

    for name in ("team-expense-edit", "team-expense-delete", "team-expense-receipt"):
        assert client.post(_url(name, person, claim.pk), {}).status_code in (404, 405)
    assert client.get(_url("team-expense-edit", person, claim.pk)).status_code == 404
    assert client.get(_url("team-expense-receipt", person, claim.pk)).status_code == 404


def test_i_download_my_own_receipt_only(client):
    person = _person_with_space()
    claim = ExpenseClaimFactory(gig=_on_gig(person), person=person)
    claim.receipt_file.save("ticket.pdf", SimpleUploadedFile("ticket.pdf", PDF))

    response = client.get(_url("team-expense-receipt", person, claim.pk))

    assert response.status_code == 200 and b"".join(response.streaming_content) == PDF
    assert "attachment" in response["Content-Disposition"]


# --- the owner decides --------------------------------------------------------------------


def test_the_owner_sees_the_proposals_on_the_date_and_on_bord(client, owner):
    person = PersonFactory(tenant=owner, first_name="Léa", last_name="Durand")
    gig = GigFactory(tenant=owner, date=_days(1))
    claim = ExpenseClaimFactory(gig=gig, person=person, label="Péage A7", amount="30.00")

    date_page = client.get(reverse("finance:page", args=[gig.pk])).content.decode()
    bord_page = client.get(reverse("tenants:profile")).content.decode()

    assert "Dépenses à valider" in date_page and "Péage A7" in date_page
    assert "Valider (à rembourser)" in date_page and "Refuser" in date_page
    assert "Dépenses à valider" in bord_page and "Léa Durand" in bord_page
    assert reverse("finance:page", args=[gig.pk]) in bord_page
    assert bord.pending_claims(owner)["total"] == D(claim.amount)


def test_a_proposal_counts_nowhere_until_accepted(owner):
    gig = GigFactory(tenant=owner, date=_days(1))
    ExpenseClaimFactory(gig=gig, person=PersonFactory(tenant=owner), amount="30.00")
    start, end = _days(-30), _days(30)

    totals = bord.expenses(owner, bord.Filters(start=start, end=end))

    assert totals["total"] == D("0")
    assert not Expense.objects.exists()


def test_accepting_creates_an_expense_of_the_member_to_reimburse(client, owner):
    person = PersonFactory(tenant=owner)
    gig = GigFactory(tenant=owner, date=_days(1))
    claim = ExpenseClaimFactory(gig=gig, person=person, label="Hôtel", amount="85.00")
    claim.receipt_file.save("recu.pdf", SimpleUploadedFile("recu.pdf", PDF))

    response = client.post(reverse("finance:claim-accept", args=[gig.pk, claim.pk]))

    assert response.status_code == 302
    expense = Expense.objects.get()
    assert (expense.person, expense.gig, expense.amount, expense.label) == (
        person,
        gig,
        D("85.00"),
        "Hôtel",
    )
    assert expense.to_reimburse and expense.reimbursed_on is None
    claim.refresh_from_db()
    assert claim.status == ExpenseClaim.Status.ACCEPTED and claim.expense == expense
    assert claim.decided_at is not None
    # the receipt moved to the expense: it is still there, and only once
    assert expense.receipt_file and not claim.receipt_file
    assert expense.receipt_file.read() == PDF


def test_refusing_keeps_the_claim_but_drops_the_receipt(
    client, owner, django_capture_on_commit_callbacks
):
    gig = GigFactory(tenant=owner, date=_days(1))
    claim = ExpenseClaimFactory(gig=gig, person=PersonFactory(tenant=owner))
    claim.receipt_file.save("recu.pdf", SimpleUploadedFile("recu.pdf", PDF))
    path = claim.receipt_file.path

    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("finance:claim-refuse", args=[gig.pk, claim.pk]))

    claim.refresh_from_db()
    assert claim.status == ExpenseClaim.Status.REFUSED and not claim.receipt_file
    assert not Expense.objects.exists()
    import os

    assert not os.path.exists(path)


def test_a_claim_is_decided_only_once(client, owner):
    gig = GigFactory(tenant=owner, date=_days(1))
    claim = ExpenseClaimFactory(gig=gig, person=PersonFactory(tenant=owner))
    url = reverse("finance:claim-accept", args=[gig.pk, claim.pk])

    client.post(url)
    client.post(url)
    client.post(reverse("finance:claim-refuse", args=[gig.pk, claim.pk]))

    assert Expense.objects.count() == 1
    claim.refresh_from_db()
    assert claim.status == ExpenseClaim.Status.ACCEPTED


def test_the_owner_downloads_the_receipt_of_a_waiting_claim(client, owner):
    gig = GigFactory(tenant=owner, date=_days(1))
    claim = ExpenseClaimFactory(gig=gig, person=PersonFactory(tenant=owner))
    claim.receipt_file.save("recu.pdf", SimpleUploadedFile("recu.pdf", PDF))

    response = client.get(reverse("finance:claim-receipt", args=[gig.pk, claim.pk]))

    assert response.status_code == 200 and b"".join(response.streaming_content) == PDF


def test_another_structure_cannot_decide_or_read(client):
    claim = ExpenseClaimFactory()
    claim.receipt_file.save("recu.pdf", SimpleUploadedFile("recu.pdf", PDF))
    other = MembershipFactory()
    client.force_login(other.user)

    for name in ("finance:claim-accept", "finance:claim-refuse"):
        assert client.post(reverse(name, args=[claim.gig.pk, claim.pk])).status_code == 404
    assert (
        client.get(reverse("finance:claim-receipt", args=[claim.gig.pk, claim.pk])).status_code
        == 404
    )
    claim.refresh_from_db()
    assert claim.is_pending and not Expense.objects.exists()


def test_a_claim_of_the_wrong_date_is_not_reachable_through_another_date(client, owner):
    claim = ExpenseClaimFactory(gig=GigFactory(tenant=owner, date=_days(1)))
    other_gig = GigFactory(tenant=owner, date=_days(2))

    response = client.post(reverse("finance:claim-accept", args=[other_gig.pk, claim.pk]))

    assert response.status_code == 404


# --- housekeeping -------------------------------------------------------------------------


def test_a_waiting_receipt_is_in_the_export_of_the_data(owner):
    claim = ExpenseClaimFactory(
        gig=GigFactory(tenant=owner, date=_days(1)), person=PersonFactory(tenant=owner)
    )
    claim.receipt_file.save("recu.pdf", SimpleUploadedFile("recu.pdf", PDF))

    with zipfile.ZipFile(build_export_zip(owner)) as archive:
        names = archive.namelist()
        content = [
            archive.read(name)
            for name in names
            if name.startswith("fichiers/justificatifs-a-valider/")
        ]

    assert content == [PDF]


def test_deleting_a_member_deletes_their_waiting_proposals(owner):
    person = PersonFactory(tenant=owner)
    ExpenseClaimFactory(gig=GigFactory(tenant=owner), person=person)

    person.delete()

    assert not ExpenseClaim.objects.exists() and not Person.objects.filter(pk=person.pk).exists()
