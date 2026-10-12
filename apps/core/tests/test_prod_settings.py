"""The production settings, loaded for real with dummy environment values."""

import importlib
import sys

import pytest
from django.test import Client, override_settings

from apps.core.sentry import MASK, scrub_event

PROD_ENV = {
    "S3_BUCKET_NAME": "bucket",
    "S3_ENDPOINT_URL": "https://s3.example.com",
    "S3_REGION_NAME": "fr-par",
    "S3_ACCESS_KEY_ID": "key",
    "S3_SECRET_ACCESS_KEY": "secret",
    "EMAIL_HOST_USER": "smtp-user",
    "EMAIL_HOST_PASSWORD": "smtp-password",
    "DEFAULT_FROM_EMAIL": "BÒRD PRO <contact@example.com>",
}


@pytest.fixture
def load_prod(monkeypatch):
    def load(**extra):
        for key, value in {**PROD_ENV, **extra}.items():
            monkeypatch.setenv(key, value)
        sys.modules.pop("config.settings.prod", None)
        return importlib.import_module("config.settings.prod")

    yield load
    sys.modules.pop("config.settings.prod", None)


def test_the_proxy_header_is_trusted_and_whitenoise_comes_right_after_security(load_prod):
    prod = load_prod()

    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert prod.MIDDLEWARE[:2] == [
        "django.middleware.security.SecurityMiddleware",
        "whitenoise.middleware.WhiteNoiseMiddleware",
    ]
    assert prod.STATIC_ROOT.name == "staticfiles"
    assert "whitenoise" in prod.STORAGES["staticfiles"]["BACKEND"]


def test_loading_prod_settings_does_not_change_the_other_settings(load_prod, settings):
    before = list(settings.MIDDLEWARE)

    load_prod()
    load_prod()

    assert list(settings.MIDDLEWARE) == before
    assert "whitenoise.middleware.WhiteNoiseMiddleware" not in settings.MIDDLEWARE


def test_csrf_trusted_origins_come_from_the_environment(load_prod):
    prod = load_prod(DJANGO_CSRF_TRUSTED_ORIGINS="https://a.example,https://b.example")

    assert prod.CSRF_TRUSTED_ORIGINS == ["https://a.example", "https://b.example"]


def test_https_redirect_does_not_loop_behind_the_proxy(load_prod):
    prod = load_prod()
    with override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=prod.SECURE_PROXY_SSL_HEADER,
        ALLOWED_HOSTS=["testserver"],
    ):
        client = Client()

        plain = client.get("/infos/cgu/")
        behind_proxy = client.get("/infos/cgu/", headers={"x-forwarded-proto": "https"})

    assert plain.status_code == 301
    assert plain.url.startswith("https://")
    assert behind_proxy.status_code == 200


def test_sentry_is_off_without_a_dsn(load_prod):
    assert load_prod().SENTRY_DSN == ""


def test_sentry_is_configured_without_personal_data(load_prod, monkeypatch):
    sentry_sdk = pytest.importorskip("sentry_sdk")
    captured = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: captured.update(kwargs))

    load_prod(SENTRY_DSN="https://key@o0.ingest.de.sentry.io/1")

    assert captured["send_default_pii"] is False
    assert captured["include_local_variables"] is False
    assert captured["before_send"] is scrub_event


TOKEN = "abcDEF123_-xyz"


def test_the_roadmap_token_is_hidden_everywhere_in_an_event():
    event = {
        "request": {"url": f"https://exemple.fr/feuille-de-route/{TOKEN}/pdf/?x=1"},
        "transaction": f"/feuille-de-route/{TOKEN}/",
        "breadcrumbs": [{"data": {"url": f"/feuille-de-route/{TOKEN}/"}}],
        "message": f"GET /feuille-de-route/{TOKEN}/ failed",
    }

    cleaned = scrub_event(event)

    assert TOKEN not in str(cleaned)
    assert cleaned["request"]["url"] == f"https://exemple.fr/feuille-de-route/{MASK}/pdf/?x=1"
    assert cleaned["transaction"] == f"/feuille-de-route/{MASK}/"


def test_other_urls_are_left_alone():
    event = {"request": {"url": "https://exemple.fr/dates/12/"}, "level": "error"}

    assert scrub_event(event) == event


def test_e_mails_go_through_a_tls_smtp_relay_and_links_are_https(load_prod):
    prod = load_prod(DJANGO_SITE_DOMAIN="bord-pro.fr")

    assert prod.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
    assert (prod.EMAIL_HOST, prod.EMAIL_PORT, prod.EMAIL_USE_TLS) == (
        "smtp-relay.brevo.com",
        587,
        True,
    )
    assert prod.EMAIL_HOST_USER == "smtp-user"
    assert prod.DEFAULT_FROM_EMAIL == prod.SERVER_EMAIL == "BÒRD PRO <contact@example.com>"
    assert prod.ACCOUNT_DEFAULT_HTTP_PROTOCOL == "https"
    assert prod.SITE_DOMAIN == "bord-pro.fr"


def test_production_refuses_to_start_without_the_sender_address(load_prod, monkeypatch):
    monkeypatch.delenv("DEFAULT_FROM_EMAIL", raising=False)
    sys.modules.pop("config.settings.prod", None)
    for key, value in PROD_ENV.items():
        if key != "DEFAULT_FROM_EMAIL":
            monkeypatch.setenv(key, value)
    with pytest.raises(Exception, match="DEFAULT_FROM_EMAIL"):
        importlib.import_module("config.settings.prod")


def test_the_organiser_form_token_is_hidden_from_sentry_too():
    token = "AbC123-secret_token_value"
    event = {
        "request": {"url": f"https://exemple.fr/formulaire-organisateur/{token}/?x=1"},
        "transaction": f"/formulaire-organisateur/{token}/",
        "message": f"POST /formulaire-organisateur/{token}/ failed",
    }

    cleaned = scrub_event(event)

    assert token not in str(cleaned)
    assert cleaned["request"]["url"] == f"https://exemple.fr/formulaire-organisateur/{MASK}/?x=1"
