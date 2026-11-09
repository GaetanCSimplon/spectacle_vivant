"""The contact form of the presentation site: e-mailed to the team, never stored."""

import smtplib

import pytest
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

pytestmark = pytest.mark.django_db

VALID = {
    "name": "Camille Martin",
    "email": "camille@example.org",
    "message": "Bonjour, je voudrais essayer Bòrd Pro pour notre compagnie.",
    "website": "",
}


@pytest.fixture(autouse=True)
def _fresh_cache(settings):
    settings.CONTACT_EMAIL = "contact@bordpro.example"
    settings.DEFAULT_FROM_EMAIL = "Bòrd Pro <contact@bordpro.example>"
    cache.clear()
    yield
    cache.clear()


def _post(client, **changes):
    return client.post(reverse("site-contact"), {**VALID, **changes})


def test_the_form_is_shown_to_a_visitor(client):
    content = client.get(reverse("site-contact")).content.decode()

    assert '<form method="post"' in content
    for field in ("name", "email", "message"):
        assert f'name="{field}"' in content


def test_a_valid_message_is_e_mailed_to_the_team(client):
    response = _post(client)

    assert response.status_code == 302
    assert response.url == reverse("site-contact-thanks")
    (sent,) = mail.outbox
    assert sent.to == ["contact@bordpro.example"]
    assert sent.reply_to == ["camille@example.org"]
    assert "Camille Martin" in sent.body and "essayer Bòrd Pro" in sent.body


def test_the_sender_is_our_address_not_the_visitors(client):
    _post(client)

    assert mail.outbox[0].from_email == "Bòrd Pro <contact@bordpro.example>"


def test_the_thanks_page_opens_without_an_account(client):
    assert client.get(reverse("site-contact-thanks")).status_code == 200


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("email", "pas-une-adresse"),
        ("email", ""),
        ("message", ""),
        ("message", "court"),
        ("message", "x" * 3001),
        ("name", "n" * 101),
    ],
)
def test_an_invalid_form_sends_nothing_and_shows_the_errors(client, field, value):
    response = _post(client, **{field: value})

    assert response.status_code == 200
    assert response.context["form"].errors.get(field)
    assert mail.outbox == []


def test_a_robot_that_fills_the_trap_gets_a_thank_you_but_nothing_is_sent(client):
    response = _post(client, website="http://spam.example")

    assert response.status_code == 302
    assert response.url == reverse("site-contact-thanks")
    assert mail.outbox == []


def test_the_trap_is_hidden_from_people_and_screen_readers(client):
    content = client.get(reverse("site-contact")).content.decode()

    assert 'name="website"' in content
    assert 'aria-hidden="true"' in content and 'tabindex="-1"' in content


def test_a_line_break_in_the_name_cannot_inject_a_header(client):
    _post(client, name="Camille\r\nBcc: victime@example.org")

    (sent,) = mail.outbox
    assert sent.bcc == []
    assert "Bcc: victime" not in sent.message().as_string().split("\n\n")[0]


def test_the_flood_stopper_refuses_after_the_hourly_limit(client, settings):
    settings.CONTACT_HOURLY_LIMIT = 2

    for _ in range(2):
        assert _post(client).status_code == 302
    response = _post(client)

    assert response.status_code == 200
    assert "contact@bordpro.example" in response.content.decode()
    assert len(mail.outbox) == 2


def test_a_mail_server_failure_shows_a_message_not_a_500(client, monkeypatch):
    def boom(self, *args, **kwargs):
        raise smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    monkeypatch.setattr("django.core.mail.message.EmailMessage.send", boom)

    response = _post(client)

    assert response.status_code == 200
    content = response.content.decode()
    assert "n&#x27;a pas pu partir" in content or "n'a pas pu partir" in content
    assert "contact@bordpro.example" in content
    assert "Camille" in content  # what was typed is kept


def test_the_failure_log_holds_no_personal_data(client, monkeypatch, caplog):
    def boom(self, *args, **kwargs):
        raise OSError("down")

    monkeypatch.setattr("django.core.mail.message.EmailMessage.send", boom)

    _post(client)

    assert "camille@example.org" not in caplog.text
    assert "essayer Bòrd Pro" not in caplog.text


def test_the_page_has_one_main_action_and_the_privacy_notice(client):
    content = client.get(reverse("site-contact")).content.decode()

    assert content.count("v-btn--main") == 1
    assert "n'est pas enregistré" in content or "n&#x27;est pas enregistré" in content
