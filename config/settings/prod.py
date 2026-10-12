from .base import *  # noqa: F403

DEBUG = False

# Scalingo ends HTTPS at its proxy and forwards plain HTTP: without this header Django
# would see every request as insecure and redirect forever.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

# WhiteNoise serves the collected static files (CSS, JS), right after SecurityMiddleware.
# A new list: inserting in place would also change the list shared with the other settings.
MIDDLEWARE = [  # noqa: F405
    MIDDLEWARE[0],  # noqa: F405
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],  # noqa: F405
]

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# E-mails (confirmation of the address, forgotten password) through an SMTP relay in the EU
# (Brevo). The links in these e-mails use the Site domain and must be https.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp-relay.brevo.com")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")  # noqa: F405
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")  # noqa: F405
SERVER_EMAIL = DEFAULT_FROM_EMAIL
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
SITE_DOMAIN = env("DJANGO_SITE_DOMAIN", default="")  # noqa: F405

# Private S3 bucket (European provider): uploaded and generated files are never public.
# Django itself streams them to the user after checking the tenant.
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("S3_BUCKET_NAME"),  # noqa: F405
            "endpoint_url": env("S3_ENDPOINT_URL"),  # noqa: F405
            "region_name": env("S3_REGION_NAME"),  # noqa: F405
            "access_key": env("S3_ACCESS_KEY_ID"),  # noqa: F405
            "secret_key": env("S3_SECRET_ACCESS_KEY"),  # noqa: F405
            "default_acl": "private",
            "file_overwrite": False,
            "querystring_auth": True,
        },
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Logs: console only (Scalingo collects it). Django's own messages never include form data
# or user details; the roadmap link token is hidden in Sentry (see apps/core/sentry.py).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}

# Error tracking (Sentry, EU): only when a DSN is given, with no personal data (CLAUDE.md 6.3).
SENTRY_DSN = env("SENTRY_DSN", default="")  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk

    from apps.core.sentry import scrub_event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        send_default_pii=False,  # no user e-mail, no IP, no cookies
        include_local_variables=False,  # variables of a crashed page may hold personal data
        before_send=scrub_event,
        before_breadcrumb=scrub_event,
        traces_sample_rate=0,
    )
