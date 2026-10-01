from .base import *  # noqa: F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

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
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
