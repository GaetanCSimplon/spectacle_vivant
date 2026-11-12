"""E-mails prepared for the user's own mail software (ORG-06, CTR-08)."""

import datetime
from urllib.parse import parse_qs, unquote, urlparse

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.addressbook import services as addressbook_services
from apps.addressbook.factories import ContactFactory
from apps.documents import services as document_services
from apps.documents.models import Contract, ContractShareLink
from apps.gigs import mail
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _gig(tenant, **kwargs):
    kwargs.setdefault("status", Gig.Status.CONFIRMED)
    return GigFactory(tenant=tenant, date=datetime.date(2030, 7, 14), **kwargs)


def _parts(mailto):
    parsed = urlparse(mailto)
    query = parse_qs(parsed.query)
    return unquote(parsed.path), query["subject"][0], query["body"][0]


def test_the_form_message_fills_the_subject_the_recipient_and_the_link():
    gig = _gig(MembershipFactory().tenant)
    ContactFactory(tenant=gig.tenant, promoter=gig.promoter, name="Marie Durand", email="m@x.org")

    result = mail.form_mail(gig, "https://bord.example/formulaire/abc")

    to, subject, body = _parts(result["mailto"])
    assert to == "m@x.org"
    assert subject == (
        f"{gig.show.title} – {gig.tenant.name} – 14/07/2030 – Confirmé – Informations organisateur"
    )
    assert "Bonjour Marie Durand," in body
    assert "https://bord.example/formulaire/abc" in body
    assert body.endswith(f"Bien cordialement,\n{gig.tenant.name}")


def test_without_a_contact_with_an_email_there_is_no_mailto_but_the_message_remains():
    gig = _gig(MembershipFactory().tenant)
    ContactFactory(tenant=gig.tenant, promoter=gig.promoter, email="")

    result = mail.form_mail(gig, "https://bord.example/f/abc")

    assert result["mailto"] == "" and "https://bord.example/f/abc" in result["body"]


def test_the_status_of_the_subject_follows_the_date():
    tenant = MembershipFactory().tenant
    assert "– Option –" in mail.form_mail(_gig(tenant, status=Gig.Status.OPTION), "x")["subject"]
    assert "– Annulé –" in mail.form_mail(_gig(tenant, status=Gig.Status.CANCELLED), "x")["subject"]
    assert "– Confirmé –" in mail.form_mail(_gig(tenant, status=Gig.Status.SIGNED), "x")["subject"]


def test_a_contact_of_another_structure_is_never_the_recipient():
    gig = _gig(MembershipFactory().tenant)
    ContactFactory(promoter=gig.promoter, tenant=MembershipFactory().tenant, email="x@other.org")

    assert mail.recipient(gig) is None


def test_a_very_long_message_falls_back_to_the_short_text_under_the_limit():
    gig = _gig(MembershipFactory().tenant)
    ContactFactory(tenant=gig.tenant, promoter=gig.promoter, email="m@x.org")

    result = mail.form_mail(gig, "https://bord.example/f/" + "a" * 1200)

    assert len(result["mailto"]) <= mail.MAILTO_LIMIT  # the short text fits...
    assert (
        "Comptez environ 5 minutes" not in _parts(result["mailto"])[2]
    )  # ...because the full one did not
    assert "Comptez environ 5 minutes" in result["body"]  # the copy keeps the full text


def test_the_date_page_offers_the_mail_button_once_the_link_exists(client):
    tenant = _login(client)
    gig = _gig(tenant)
    ContactFactory(tenant=tenant, promoter=gig.promoter, email="m@x.org")
    addressbook_services.create_invitation(gig.promoter, None)

    page = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    assert "Envoyer par e-mail" in page and "mailto:m@x.org" in page
    assert "Copier le message" in page and "Copier le lien" in page


def test_the_complete_contract_page_offers_it_too(client):
    tenant = _login(client)
    gig = _gig(tenant)
    ContactFactory(tenant=tenant, promoter=gig.promoter, email="m@x.org")
    addressbook_services.create_invitation(gig.promoter, None)

    page = client.get(reverse("documents:contract-complete", args=[gig.pk])).content.decode()

    assert "mailto:m@x.org" in page


# --- contract (CTR-08) ------------------------------------------------------------------------


def _contract(tenant):
    gig = _gig(tenant)
    ContactFactory(tenant=tenant, promoter=gig.promoter, name="Marie", email="m@x.org")
    document_services.generate_contract_pdf(gig)
    return gig, Contract.objects.get(gig=gig)


def test_preparing_the_contract_mail_makes_a_link_and_shows_the_message(client):
    tenant = _login(client)
    gig, contract = _contract(tenant)

    response = client.post(reverse("documents:contract-share", args=[gig.pk]))

    assert response.url == reverse("documents:contract-history", args=[gig.pk])
    link = ContractShareLink.objects.get(contract=contract)
    page = client.get(response.url).content.decode()
    assert f"/contrat-partage/{link.token}/" in unquote(page)
    assert "mailto:m@x.org" in page and "Contrat de cession" in unquote(page)


def test_the_page_asks_to_prepare_the_mail_first(client):
    tenant = _login(client)
    gig, _contract_ = _contract(tenant)

    page = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()

    assert "Préparer l&#x27;e-mail" in page or "Préparer l'e-mail" in page
    assert "mailto:" not in page


def test_a_new_version_cancels_the_link_of_the_previous_one(client):
    tenant = _login(client)
    gig, contract = _contract(tenant)
    client.post(reverse("documents:contract-share", args=[gig.pk]))
    document_services.generate_contract_pdf(gig)

    assert document_services.active_share_link(Contract.objects.get(pk=contract.pk)) is None


def test_the_link_downloads_the_sent_version_without_an_account(client):
    gig, contract = _contract(MembershipFactory().tenant)
    link = document_services.create_share_link(contract, None)

    response = client.get(reverse("contract-share-public", args=[link.token]))

    assert response.status_code == 200 and response["Content-Type"] == "application/pdf"
    assert response["Cache-Control"] == "no-store" and "noindex" in response["X-Robots-Tag"]


def test_an_expired_or_cancelled_link_is_closed_and_an_unknown_one_is_a_404(client):
    gig, contract = _contract(MembershipFactory().tenant)
    link = document_services.create_share_link(contract, None)
    link.expires_at = timezone.now() - datetime.timedelta(minutes=1)
    link.save()

    assert client.get(reverse("contract-share-public", args=[link.token])).status_code == 410
    assert client.get(reverse("contract-share-public", args=["nope"])).status_code == 404


def test_a_new_link_cancels_the_previous_one():
    gig, contract = _contract(MembershipFactory().tenant)
    first = document_services.create_share_link(contract, None)
    second = document_services.create_share_link(contract, None)
    first.refresh_from_db()

    assert not first.is_active and second.is_active


def test_the_contract_message_carries_the_link_and_the_deposit():
    gig, contract = _contract(MembershipFactory().tenant)
    gig.deposit_due_on = datetime.date(2030, 6, 1)
    gig.save()

    result = mail.contract_mail(gig, "https://bord.example/contrat-partage/abc")

    assert "https://bord.example/contrat-partage/abc" in result["body"]
    assert "valable 7 jours" in result["body"] and "L'acompte de 30 %" in result["body"]


def test_another_tenant_cannot_prepare_the_mail_of_my_contract(client):
    _login(client)
    gig, _contract_ = _contract(MembershipFactory().tenant)

    response = client.post(reverse("documents:contract-share", args=[gig.pk]))

    assert response.status_code == 404
    assert not ContractShareLink.objects.exists()
