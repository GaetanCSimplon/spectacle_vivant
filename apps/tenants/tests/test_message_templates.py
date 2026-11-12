"""The e-mails a structure can rewrite (CTR-03): the default text, its own text, isolation."""

import pytest
from django.urls import reverse

from apps.accounts.models import Membership
from apps.addressbook import info_requests
from apps.addressbook.factories import ContactFactory
from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.finance.tests.helpers import TENANT_FIELDS, make_gig
from apps.gigs import mail
from apps.tenants import message_templates as mt
from apps.tenants.data_export import message_templates_rows
from apps.tenants.factories import MembershipFactory, PersonFactory, TenantFactory
from apps.tenants.models import MessageTemplate

mark_isolation_tested(MessageTemplate)

pytestmark = pytest.mark.django_db

URL = "tenants:message-templates"


def _login(client, role=Membership.Role.OWNER):
    membership = MembershipFactory(
        role=role, **{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()}
    )
    client.force_login(membership.user)
    return membership.tenant


def _gig(tenant):
    gig = make_gig(tenant=tenant)
    ContactFactory(tenant=tenant, promoter=gig.promoter, name="Marie Durand", email="m@x.org")
    return gig


def _save(client, kind, subject, body, **extra):
    return client.post(
        reverse(URL), {"kind": kind, "action": "save", "subject": subject, "body": body, **extra}
    )


# --- rendering ----------------------------------------------------------------------------


def test_the_default_text_is_used_until_the_structure_writes_its_own(client):
    tenant = _login(client)
    gig = _gig(tenant)

    result = mail.form_mail(gig, "https://x/abc")

    assert result["body"].startswith("Bonjour Marie Durand,")
    assert "https://x/abc" in result["body"] and "Informations organisateur" in result["subject"]


def test_its_own_text_replaces_the_default_with_the_variables_filled(client):
    tenant = _login(client)
    gig = _gig(tenant)
    MessageTemplate.objects.create(
        tenant=tenant,
        kind="form",
        subject="Fiche – [Titre du spectacle] ([Statut])",
        body="Salut [Contact] !\n\n[Lien]\n\n[Signature]",
    )

    result = mail.form_mail(gig, "https://x/abc")

    assert result["subject"] == f"Fiche – {gig.show.title} (Confirmé)".replace(
        "Confirmé", mail.status_label(gig)
    )
    assert result["body"] == f"Salut Marie Durand !\n\nhttps://x/abc\n\n{tenant.name}"
    assert "subject=Fiche" in result["mailto"]


def test_a_variable_is_replaced_by_text_never_read_again_as_a_variable():
    values = {"Contact": "[Lien]", "Lien": "https://x"}

    assert mt.fill("Bonjour [Contact] [Inconnu]", values) == "Bonjour [Lien] [Inconnu]"


def test_without_a_contact_the_greeting_has_no_stray_space():
    assert mt.fill("Bonjour [Contact],\n\nSuite", {"Contact": ""}) == "Bonjour,\n\nSuite"


def test_the_deposit_sentence_disappears_cleanly_when_there_is_none(client):
    tenant = _login(client)
    gig = _gig(tenant)
    gig.deposit_percent = 0
    gig.save()

    body = mail.contract_mail(gig, "https://x/c")["body"]

    assert "acompte" not in body.lower()
    assert "dès que possible." in body and " \n" not in body


def test_a_long_custom_text_falls_back_to_the_short_default(client):
    tenant = _login(client)
    gig = _gig(tenant)
    MessageTemplate.objects.create(
        tenant=tenant, kind="form", subject="Fiche", body="é" * 1500 + " [Lien]"
    )

    result = mail.form_mail(gig, "https://x/abc")

    assert len(result["mailto"]) <= mail.MAILTO_LIMIT
    assert result["body"].startswith("é") and "Merci%20de%20compl%C3%A9ter" in result["mailto"]


def test_the_reminder_and_the_info_message_use_their_own_text(client):
    tenant = _login(client)
    gig = _gig(tenant)
    MessageTemplate.objects.create(
        tenant=tenant, kind="reminder", subject="Relance", body="Alors [Contact] ? [Date d'envoi]"
    )
    MessageTemplate.objects.create(
        tenant=tenant, kind="info", subject="Infos [Nom du groupe]", body="Hop [Contact] [Lien]"
    )
    person = PersonFactory(tenant=tenant, first_name="Léa", email="l@x.org")

    reminder = mail.reminder_mail(gig, gig.date)
    info = info_requests.mail(person, "https://x/i")

    assert reminder["body"] == f"Alors Marie Durand ? {gig.date.strftime('%d/%m/%Y')}"
    assert info["subject"] == f"Infos {tenant.name}" and info["body"] == "Hop Léa https://x/i"


# --- the page -----------------------------------------------------------------------------


def test_the_owner_saves_and_resets_a_text(client):
    tenant = _login(client)

    response = _save(client, "contract", "Mon objet", "Texte pour [Contact] [Lien]")
    saved = MessageTemplate.objects.get(tenant=tenant, kind="contract")
    client.post(reverse(URL), {"kind": "contract", "action": "reset"})

    assert response.status_code == 302 and saved.subject == "Mon objet"
    assert not MessageTemplate.objects.filter(tenant=tenant).exists()


def test_saving_again_replaces_the_text_without_a_second_row(client):
    tenant = _login(client)

    _save(client, "form", "Un", "Un [Lien]")
    _save(client, "form", "Deux", "Deux [Lien]")

    assert MessageTemplate.objects.filter(tenant=tenant).get().subject == "Deux"


def test_an_unknown_variable_is_refused_with_the_list_of_the_good_ones(client):
    tenant = _login(client)

    response = _save(client, "reminder", "Objet", "Bonjour [Prénom] [Lien]")

    page = response.content.decode()
    assert response.status_code == 200 and "Variable inconnue" in page and "[Prénom]" in page
    assert "[Date d&#x27;envoi]" in page or "[Date d'envoi]" in page
    assert not MessageTemplate.objects.filter(tenant=tenant).exists()


def test_a_variable_of_another_message_is_refused(client):
    _login(client)

    response = _save(client, "info", "Objet", "Acompte : [Acompte]")  # not an info variable

    assert "Variable inconnue" in response.content.decode()


def test_empty_or_too_long_texts_are_refused(client):
    tenant = _login(client)

    assert _save(client, "form", "", "x").status_code == 200
    assert _save(client, "form", "x", "y" * 2001).status_code == 200
    assert _save(client, "form", "x" * 201, "y").status_code == 200
    assert not MessageTemplate.objects.filter(tenant=tenant).exists()


def test_an_unknown_kind_is_a_404(client):
    _login(client)

    assert _save(client, "other", "a", "b").status_code == 404


def test_a_member_reads_the_page_but_cannot_change_a_text(client):
    tenant = _login(client, Membership.Role.MEMBER)

    page = client.get(reverse(URL))
    response = _save(client, "form", "Objet", "Texte [Lien]")

    assert page.status_code == 200 and "Seul le propriétaire" in page.content.decode()
    assert response.status_code == 403
    assert not MessageTemplate.objects.filter(tenant=tenant).exists()


def test_the_page_requires_a_login(client):
    assert client.get(reverse(URL)).status_code == 302


def test_the_page_shows_the_preview_and_the_settings_link(client):
    _login(client)

    page = client.get(reverse(URL)).content.decode()

    assert "Aperçu" in page and "Marie Durand" in page
    assert reverse(URL) in client.get(reverse("tenants:settings")).content.decode()


# --- isolation ----------------------------------------------------------------------------


def test_another_structure_never_sees_nor_changes_my_texts(client):
    mine = TenantFactory(**TENANT_FIELDS)
    MessageTemplate.objects.create(tenant=mine, kind="form", subject="Secret", body="Secret [Lien]")
    other = _login(client)

    page = client.get(reverse(URL)).content.decode()
    client.post(reverse(URL), {"kind": "form", "action": "reset"})
    _save(client, "form", "Autre", "Autre [Lien]")

    assert "Secret" not in page
    assert MessageTemplate.objects.get(tenant=mine, kind="form").subject == "Secret"
    assert MessageTemplate.objects.get(tenant=other, kind="form").subject == "Autre"
    gig = _gig(other)
    assert "Secret" not in mail.form_mail(gig, "x")["body"]


def test_the_texts_are_in_the_data_export(client):
    tenant = _login(client)
    MessageTemplate.objects.create(tenant=tenant, kind="form", subject="Mon objet", body="Corps")
    MessageTemplate.objects.create(tenant=TenantFactory(), kind="form", subject="Autre", body="x")

    _header, rows = message_templates_rows(tenant)

    assert [r[1] for r in rows] == ["Mon objet"]
