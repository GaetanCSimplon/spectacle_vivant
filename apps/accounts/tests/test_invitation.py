"""Sign-up on invitation: only the addresses of the invitation list can create an account."""

import html

import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.models import SignupInvitation, User

pytestmark = pytest.mark.django_db

REFUSAL = "L'inscription se fait sur invitation"


@pytest.fixture(autouse=True)
def invitation_required(settings):
    settings.SIGNUP_REQUIRES_INVITATION = True


def _signup(client, email):
    return client.post(
        reverse("account_signup"),
        {
            "email": email,
            "password1": "un-mot-de-passe-solide",
            "password2": "un-mot-de-passe-solide",
        },
    )


def test_an_invited_address_can_sign_up_and_gets_the_confirmation_e_mail(client):
    SignupInvitation.objects.create(email="marie@example.org")

    response = _signup(client, "marie@example.org")

    assert response.status_code == 302
    assert User.objects.filter(email="marie@example.org").exists()
    assert len(mail.outbox) == 1


def test_an_address_that_is_not_invited_is_refused_and_nothing_is_created(client):
    response = _signup(client, "inconnu@example.org")

    assert response.status_code == 200
    assert REFUSAL in html.unescape(response.content.decode())
    assert not User.objects.filter(email="inconnu@example.org").exists()
    assert mail.outbox == []


def test_the_case_of_the_address_does_not_matter(client):
    SignupInvitation.objects.create(email="Marie@Example.ORG")

    assert SignupInvitation.objects.get().email == "marie@example.org"
    assert _signup(client, "MARIE@example.org").status_code == 302


def test_signing_up_marks_the_invitation_as_used(client):
    invitation = SignupInvitation.objects.create(email="marie@example.org", note="Bêta")
    assert invitation.used_at is None

    _signup(client, "marie@example.org")

    invitation.refresh_from_db()
    assert invitation.used_at is not None


def test_an_existing_account_is_refused_with_the_same_message_when_not_invited(client):
    User.objects.create_user(email="deja@example.org", password="x-mot-de-passe-solide")

    response = _signup(client, "deja@example.org")

    assert REFUSAL in html.unescape(
        response.content.decode()
    )  # nothing about existing accounts is revealed


def test_when_the_setting_is_off_everybody_can_sign_up(client, settings):
    settings.SIGNUP_REQUIRES_INVITATION = False

    assert _signup(client, "libre@example.org").status_code == 302


def test_the_password_reset_is_not_restricted_by_the_invitation(client):
    User.objects.create_user(email="ancien@example.org", password="x-mot-de-passe-solide")

    response = client.post(reverse("account_reset_password"), {"email": "ancien@example.org"})

    assert response.status_code == 302
    assert len(mail.outbox) == 1


def test_the_login_page_speaks_of_invitations_and_links_to_the_contact_form(client):
    page = client.get(reverse("account_login")).content.decode()

    assert "ouvert sur invitation" in page
    assert "Demander une invitation" in page and reverse("site-contact") in page
    assert f'href="{reverse("account_signup")}"' in page


def test_the_login_page_goes_back_to_the_plain_wording_when_signup_is_open(client, settings):
    settings.SIGNUP_REQUIRES_INVITATION = False

    page = client.get(reverse("account_login")).content.decode()

    assert "Créer un compte" in page and "sur invitation" not in page


def test_the_production_default_keeps_the_doors_shut():
    """Forgetting the variable must not open the sign-up: the default is True."""
    from pathlib import Path

    base = (Path(__file__).resolve().parents[3] / "config/settings/base.py").read_text()

    assert 'env.bool("SIGNUP_REQUIRES_INVITATION", default=True)' in base
    prod = (Path(__file__).resolve().parents[3] / "config/settings/prod.py").read_text()
    assert "SIGNUP_REQUIRES_INVITATION" not in prod  # prod does not override it


def test_the_invitation_list_is_in_the_admin(admin_client):
    SignupInvitation.objects.create(email="marie@example.org")

    response = admin_client.get(reverse("admin:accounts_signupinvitation_changelist"))

    assert response.status_code == 200 and "marie@example.org" in response.content.decode()
