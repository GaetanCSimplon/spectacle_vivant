"""
Base Django settings for config project, shared by all environments.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/
"""

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "allauth",
    "allauth.account",
    "django_tailwind_cli",
    "django_htmx",
    "apps.accounts",
    "apps.tenants",
    "apps.core",
    "apps.catalog",
    "apps.addressbook",
    "apps.gigs",
    "apps.documents",
    "apps.roadmaps",
    "apps.finance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.TenantMiddleware",
    "apps.core.middleware.OnboardingRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.tenants.context_processors.pending_deletion",
                "apps.gigs.context_processors.gig_navigation",
                "apps.accounts.context_processors.signup_policy",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

# Public presentation site (the pages a visitor sees before logging in).
CONTACT_EMAIL = env("CONTACT_EMAIL", default="contact@bordpro.fr")
# Messages the contact form may send per hour (a flood stopper, see services.contact_quota_left).
CONTACT_HOURLY_LIMIT = env.int("CONTACT_HOURLY_LIMIT", default=20)
# Search engines are kept out until the content and the legal pages are ready.
SITE_INDEXABLE = env.bool("SITE_INDEXABLE", default=False)

# Map preview of a roadmap: an address is turned into a point once, when it is saved
# (apps/core/geocoding.py, Nominatim from OpenStreetMap). Off, the pages simply have no map.
GEOCODING_ENABLED = env.bool("GEOCODING_ENABLED", default=True)
GEOCODING_URL = "https://nominatim.openstreetmap.org/search"
GEOCODING_USER_AGENT = "BordPro/1.0 (contact@bordpro.fr)"

# django-allauth: login by e-mail only, no username field
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_ADAPTER = "apps.accounts.adapter.AccountAdapter"
ACCOUNT_LOGIN_METHODS = {"email"}
# A password reset for an address without an account sends nothing: allauth's default e-mail to
# such an address says "you can sign up with the link below", but sign-up is on invitation only
# (and the same page is shown either way, so nothing tells whether an address has an account).
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_FORMS = {"signup": "apps.accounts.forms.InvitedSignupForm"}
# Sign-up only for the addresses of the invitation list (admin). On by default, so that
# forgetting the variable in production keeps the doors shut; off in dev and tests.
SIGNUP_REQUIRES_INVITATION = env.bool("SIGNUP_REQUIRES_INVITATION", default=True)

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# What a visitor sees when the security check of a form fails.
CSRF_FAILURE_VIEW = "apps.core.views.csrf_failure"

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "fr"

TIME_ZONE = "Europe/Paris"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # filled by collectstatic, served by WhiteNoise in prod

# django-tailwind-cli: custom source (outside STATICFILES_DIRS, see its docs) so we can
# define our own button/form/card styles instead of the plain "@import tailwindcss" default.
TAILWIND_CLI_SRC_CSS = "css/source.css"

# Media files (uploaded/generated documents) — local disk in dev, private European
# S3 bucket in production (see prod.py). They are never served by a /media/ URL:
# only views that check the tenant send them.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Look-ups that save typing (recette n°1, ORG-01 and ORG-02): two free public APIs of the French
# State, no account and no key. Only what the user typed in the search box leaves the server.
LOOKUPS_ENABLED = env.bool("LOOKUPS_ENABLED", default=True)
COMPANY_SEARCH_URL = "https://recherche-entreprises.api.gouv.fr/search"
COMMUNES_URL = "https://geo.api.gouv.fr/communes"
