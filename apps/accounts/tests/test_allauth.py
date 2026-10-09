import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def _signup(client, email):
    return client.post(
        reverse("account_signup"),
        {
            "email": email,
            "password1": "un-mot-de-passe-solide",
            "password2": "un-mot-de-passe-solide",
        },
    )


def test_login_page_is_reachable(client):
    response = client.get(reverse("account_login"))
    assert response.status_code == 200


def test_signup_creates_user_with_email_as_identifier(client):
    response = _signup(client, "artiste1@example.com")

    assert response.status_code == 302
    user = User.objects.get(email="artiste1@example.com")
    assert not user.is_active or not user.emailaddress_set.get().verified


def test_signup_sends_a_verification_email(client):
    _signup(client, "artiste2@example.com")

    assert len(mail.outbox) == 1
    assert "artiste2@example.com" in mail.outbox[0].to


def test_unverified_user_cannot_log_in(client):
    _signup(client, "artiste3@example.com")

    response = client.post(
        reverse("account_login"),
        {"login": "artiste3@example.com", "password": "un-mot-de-passe-solide"},
    )

    assert response.wsgi_request.user.is_authenticated is False


def test_login_page_has_a_visible_signup_button(client):
    response = client.get(reverse("account_login"))
    html = response.content.decode()
    assert "Créer un compte" in html
    assert f'href="{reverse("account_signup")}"' in html
