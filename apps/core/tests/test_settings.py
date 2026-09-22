from django.conf import settings


def test_settings_load_with_french_locale():
    assert settings.LANGUAGE_CODE == "fr"
    assert settings.TIME_ZONE == "Europe/Paris"


def test_custom_user_model_is_configured():
    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_secret_key_is_not_hardcoded_default():
    assert settings.SECRET_KEY
    assert "django-insecure" not in settings.SECRET_KEY
