from .base import *  # noqa: F403

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

SIGNUP_REQUIRES_INVITATION = False

# No network call from the tests: the ones about geocoding switch it on and fake the answer.
GEOCODING_ENABLED = False

# Same for the company and commune look-ups.
LOOKUPS_ENABLED = False
