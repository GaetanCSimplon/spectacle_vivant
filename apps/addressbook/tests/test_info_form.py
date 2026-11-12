"""The form a contact or a team member fills in about themselves (ORG-07)."""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Membership
from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.tenants.factories import MembershipFactory, PersonFactory

from .. import info_requests
from ..factories import ContactFactory
from ..models import InfoInvitation

mark_isolation_tested(InfoInvitation)

pytestmark = pytest.mark.django_db

VALID_SSN = "1 85 05 78 006 084 91"


def _owner(client):
    membership = MembershipFactory(role=Membership.Role.OWNER)
    client.force_login(membership.user)
    return membership.tenant


def _member(client):
    membership = MembershipFactory(role=Membership.Role.MEMBER)
    client.force_login(membership.user)
    return membership.tenant


def _public(invitation):
    return reverse("info-form-public", args=[invitation.token])


def _answered(target, **answer):
    invitation = info_requests.create_invitation(target, None)
    info_requests.submit_response(invitation, answer)
    invitation.refresh_from_db()
    return invitation


# --- the link ---------------------------------------------------------------------------


def test_a_link_is_secret_valid_for_a_week_and_replaces_the_one_waiting():
    contact = ContactFactory()
    first = info_requests.create_invitation(contact, None)
    second = info_requests.create_invitation(contact, None)
    first.refresh_from_db()

    assert len(first.token) >= 43 and first.token != second.token
    assert first.status == InfoInvitation.Status.REVOKED
    assert second.expires_at - second.created_at == pytest.approx(
        datetime.timedelta(days=7), abs=datetime.timedelta(minutes=1)
    )


def test_status_follows_the_life_of_the_link():
    contact = ContactFactory()
    invitation = info_requests.create_invitation(contact, None)
    assert invitation.status == InfoInvitation.Status.ACTIVE
    invitation.expires_at = timezone.now() - datetime.timedelta(minutes=1)
    assert invitation.status == InfoInvitation.Status.EXPIRED
    invitation.completed_at = timezone.now()
    assert invitation.status == InfoInvitation.Status.ANSWERED
    invitation.reviewed_at = timezone.now()
    assert invitation.status == InfoInvitation.Status.REVIEWED


# --- the public form --------------------------------------------------------------------


def test_the_contact_answers_without_an_account_and_the_link_closes(client):
    invitation = info_requests.create_invitation(ContactFactory(), None)

    page = client.get(_public(invitation))
    assert page.status_code == 200 and page["Cache-Control"] == "no-store"
    assert "noindex" in page["X-Robots-Tag"]
    response = client.post(_public(invitation), {"name": "Julie G.", "phone": "0611223344"})

    invitation.refresh_from_db()
    assert response.url == reverse("promoter-form-thanks")
    assert invitation.response == {"name": "Julie G.", "phone": "0611223344"}
    assert client.get(_public(invitation)).status_code == 410
    assert client.post(_public(invitation), {"name": "Autre"}).status_code == 410


def test_an_unknown_link_is_a_404_and_an_empty_answer_is_refused(client):
    invitation = info_requests.create_invitation(ContactFactory(), None)

    assert client.get(reverse("info-form-public", args=["nope"])).status_code == 404
    assert client.post(_public(invitation), {}).status_code == 200
    invitation.refresh_from_db()
    assert invitation.status == InfoInvitation.Status.ACTIVE


def test_the_team_member_form_carries_the_private_fields_and_checks_them(client):
    invitation = info_requests.create_invitation(PersonFactory(), None)

    bad = client.post(_public(invitation), {"social_security_number": "123"})
    assert bad.status_code == 200 and "15 caractères" in bad.content.decode()

    ok = client.post(
        _public(invitation),
        {
            "phone": "0611223344",
            "address": "3 rue des Lilas",
            "postal_code": "69001",
            "city": "Lyon",
            "birth_date": "1985-05-12",
            "social_security_number": VALID_SSN,
            "guso_number": "G123",
        },
    )

    invitation.refresh_from_db()
    assert ok.status_code == 302
    assert invitation.response["social_security_number"] == "185057800608491"
    assert invitation.response["birth_date"] == "1985-05-12"
    assert invitation.response["department"] == "69"


def test_an_implausible_birth_date_is_refused(client):
    invitation = info_requests.create_invitation(PersonFactory(), None)

    response = client.post(_public(invitation), {"birth_date": "1800-01-01"})

    assert response.status_code == 200 and "plausible" in response.content.decode()


# --- sending and reviewing --------------------------------------------------------------


def test_the_user_sends_the_link_from_the_contact_and_gets_the_mail_buttons(client):
    tenant = _owner(client)
    contact = ContactFactory(tenant=tenant, promoter=None, name="Julie", email="j@x.org")

    client.post(reverse("addressbook:contact-info-invite", args=[contact.pk]))
    page = client.get(reverse("addressbook:contact-update", args=[contact.pk])).content.decode()

    assert "mailto:j@x.org" in page and "Copier le message" in page
    assert "Bonjour Julie" in page.replace("%20", " ") or "Bonjour%20Julie" in page


def test_applying_a_contact_answer_writes_only_the_ticked_fields_and_forgets_the_rest(client):
    tenant = _owner(client)
    contact = ContactFactory(tenant=tenant, promoter=None, name="Julie", phone="")
    _answered(contact, name="Julie Garnier", phone="0611223344")

    response = client.post(
        reverse("addressbook:contact-info-answer", args=[contact.pk]), {"fields": ["phone"]}
    )

    contact.refresh_from_db()
    invitation = info_requests.latest_invitation(contact)
    assert response.status_code == 302
    assert contact.phone == "0611223344" and contact.name == "Julie"
    assert invitation.status == InfoInvitation.Status.REVIEWED and invitation.response == {}


def test_ignoring_an_answer_changes_nothing(client):
    tenant = _owner(client)
    contact = ContactFactory(tenant=tenant, promoter=None, name="Julie")
    _answered(contact, name="Autre")

    client.post(reverse("addressbook:contact-info-answer", args=[contact.pk]), {"ignore": "1"})

    contact.refresh_from_db()
    assert contact.name == "Julie"
    assert info_requests.latest_invitation(contact).response == {}


def test_applying_a_team_member_answer_sets_the_private_fields(client):
    tenant = _owner(client)
    person = PersonFactory(tenant=tenant)
    _answered(
        person,
        birth_date="1985-05-12",
        social_security_number="185057800608491",
        guso_number="G123",
    )

    client.post(
        reverse("tenants:person-info-answer", args=[person.pk]),
        {"fields": ["birth_date", "social_security_number", "guso_number"]},
    )

    person.refresh_from_db()
    assert person.birth_date == datetime.date(1985, 5, 12)
    assert person.social_security_number == "185057800608491"
    assert person.guso_number == "G123"


def test_the_review_screen_shows_what_the_fiche_has_now(client):
    tenant = _owner(client)
    person = PersonFactory(tenant=tenant, guso_number="OLD1")
    _answered(person, guso_number="NEW2")

    page = client.get(reverse("tenants:person-info-answer", args=[person.pk])).content.decode()

    assert "NEW2" in page and "OLD1" in page


def test_a_double_application_is_refused(client):
    tenant = _owner(client)
    contact = ContactFactory(tenant=tenant, promoter=None)
    invitation = _answered(contact, phone="0611223344")
    info_requests.apply_response(invitation, ["phone"])

    with pytest.raises(info_requests.InvitationClosed):
        info_requests.apply_response(invitation, ["phone"])


# --- who can do what --------------------------------------------------------------------


def test_a_member_who_is_not_the_owner_cannot_touch_the_team_member_form(client):
    tenant = _member(client)
    person = PersonFactory(tenant=tenant)
    _answered(person, guso_number="G1")

    for name in ("person-info-invite", "person-info-revoke", "person-info-answer"):
        url = reverse(f"tenants:{name}", args=[person.pk])
        assert client.post(url).status_code == 403
    assert client.get(reverse("tenants:person-info-answer", args=[person.pk])).status_code == 403
    assert (
        "Informations à faire compléter"
        not in client.get(reverse("tenants:person-detail", args=[person.pk])).content.decode()
    )


def test_another_structure_cannot_reach_my_contact_or_my_team_member(client):
    _owner(client)
    contact = ContactFactory()
    person = PersonFactory()
    _answered(contact, phone="0611223344")

    for url in (
        reverse("addressbook:contact-info-invite", args=[contact.pk]),
        reverse("addressbook:contact-info-revoke", args=[contact.pk]),
        reverse("addressbook:contact-info-answer", args=[contact.pk]),
        reverse("tenants:person-info-invite", args=[person.pk]),
        reverse("tenants:person-info-answer", args=[person.pk]),
    ):
        assert client.post(url).status_code == 404
    assert InfoInvitation.objects.filter(contact=contact, reviewed_at=None).exists()


def test_a_link_is_for_one_target_only():
    from django.db import IntegrityError, transaction

    with pytest.raises(IntegrityError), transaction.atomic():
        InfoInvitation.objects.create(
            tenant=ContactFactory().tenant,
            token="x",
            expires_at=timezone.now(),
        )


def test_an_invitation_never_applies_to_a_field_it_does_not_carry():
    contact = ContactFactory(tenant=MembershipFactory().tenant, promoter=None, name="Julie")
    invitation = _answered(contact, name="Julie G.")
    invitation.response = {"name": "Julie G.", "social_security_number": "185057800608491"}
    invitation.save()

    chosen = info_requests.apply_response(invitation, ["name", "social_security_number"])

    assert chosen == ["name"]
