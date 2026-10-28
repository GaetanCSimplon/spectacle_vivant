"""An e-mail that cannot be sent gives a clear message, never an error page (Brevo down)."""

import logging
import smtplib

import pytest
from django.core import mail
from django.core.cache import cache
from django.core.mail.backends.base import BaseEmailBackend
from django.urls import reverse

from apps.accounts.models import SignupInvitation, User

pytestmark = pytest.mark.django_db

ADDRESS = "marie.secrete@example.org"
PASSWORD = "un-mot-de-passe-solide"


class FailingBackend(BaseEmailBackend):
    """Stands for the mail service refusing us (error 535 of an unchecked sender or key)."""

    error = smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    def send_messages(self, email_messages):
        raise self.error


@pytest.fixture(autouse=True)
def _fresh_cache():
    """allauth rate-limits the confirmation e-mail of an address (1 per 3 minutes) in the cache,
    which outlives a test: without this the second test with the same address gets no e-mail."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def broken_mail(settings):
    settings.EMAIL_BACKEND = f"{__name__}.FailingBackend"
    FailingBackend.error = smtplib.SMTPAuthenticationError(535, b"Authentication failed")


def _signup(client):
    return client.post(
        reverse("account_signup"),
        {"email": ADDRESS, "password1": PASSWORD, "password2": PASSWORD},
        follow=True,
    )


def test_signing_up_with_the_mail_service_down_does_not_end_in_an_error_page(client, broken_mail):
    response = _signup(client)

    assert response.status_code == 200
    assert User.objects.filter(email=ADDRESS).exists()  # the account is created
    assert "pas pu envoyer l" in response.content.decode()


def test_the_message_says_what_to_do_next(client, broken_mail):
    page = _signup(client).content.decode()

    assert "réessayez dans quelques minutes" in page and "page Contact" in page


@pytest.mark.parametrize(
    "error",
    [
        smtplib.SMTPAuthenticationError(535, b"bad"),
        smtplib.SMTPServerDisconnected("closed"),
        ConnectionRefusedError("refused"),
        TimeoutError("slow"),
        OSError("network is unreachable"),
    ],
)
def test_every_kind_of_mail_failure_is_handled(client, broken_mail, error):
    FailingBackend.error = error

    assert _signup(client).status_code == 200


def test_the_address_never_reaches_the_logs(client, broken_mail, caplog):
    with caplog.at_level(logging.DEBUG):
        _signup(client)

    assert ADDRESS not in caplog.text and "marie.secrete" not in caplog.text
    assert any("could not be sent" in record.message for record in caplog.records)
    assert "SMTPAuthenticationError" in caplog.text


def test_the_next_sign_in_attempt_sends_the_confirmation_again(client, settings):
    settings.EMAIL_BACKEND = f"{__name__}.FailingBackend"
    FailingBackend.error = smtplib.SMTPAuthenticationError(535, b"bad")
    _signup(client)
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"  # the service is back
    cache.clear()  # allauth sends a confirmation to an address once per 3 minutes: wait them out

    client.post(reverse("account_login"), {"login": ADDRESS, "password": PASSWORD}, follow=True)

    assert len(mail.outbox) == 1 and mail.outbox[0].to == [ADDRESS]


def test_a_working_mail_service_still_sends_normally_and_shows_no_error(client):
    response = client.post(
        reverse("account_signup"),
        {"email": ADDRESS, "password1": PASSWORD, "password2": PASSWORD},
        follow=True,
    )

    assert len(mail.outbox) == 1
    assert "pas pu envoyer" not in response.content.decode()


def test_a_failing_password_reset_mail_is_handled_too(client, settings):
    from apps.tenants.factories import MembershipFactory

    user = MembershipFactory().user
    settings.EMAIL_BACKEND = f"{__name__}.FailingBackend"
    FailingBackend.error = smtplib.SMTPServerDisconnected("closed")

    response = client.post(reverse("account_reset_password"), {"email": user.email}, follow=True)

    assert response.status_code == 200 and "pas pu envoyer" in response.content.decode()


def test_with_the_invitation_list_on_the_failure_is_handled_the_same_way(
    client, broken_mail, settings
):
    settings.SIGNUP_REQUIRES_INVITATION = True
    SignupInvitation.objects.create(email=ADDRESS)

    response = _signup(client)

    assert response.status_code == 200 and "pas pu envoyer" in response.content.decode()
    assert User.objects.filter(email=ADDRESS).exists()


def test_the_page_does_not_contradict_the_error_it_shows(client, broken_mail):
    page = _signup(client).content.decode()

    assert "pas pu envoyer" in page
    assert "Confirmation email sent" not in page and "E-mail de confirmation envoyé" not in page
    assert "Nous vous avons envoyé" not in page  # allauth's own wording is replaced


def test_with_a_working_service_the_usual_confirmation_message_is_still_shown(client):
    page = client.post(
        reverse("account_signup"),
        {"email": ADDRESS, "password1": PASSWORD, "password2": PASSWORD},
        follow=True,
    ).content.decode()

    assert "E-mail de confirmation envoyé" in page or "Confirmation email sent" in page
    assert "Un e-mail de confirmation doit vous parvenir" in page


def test_the_reset_done_page_holds_whether_or_not_the_mail_left(client, settings):
    page = client.get(reverse("account_reset_password_done")).content.decode()

    assert "Nous vous avons envoyé" not in page and "courriers indésirables" in page
