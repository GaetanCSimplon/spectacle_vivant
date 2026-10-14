"""The press kit link: completed with https://, and no Django 6 deprecation warning."""

import warnings

import pytest
from django.contrib import admin
from django.utils.deprecation import RemovedInDjango60Warning

from ..forms import ShowForm
from ..models import Show

pytestmark = pytest.mark.django_db


def _form(epk_url):
    return ShowForm(
        {
            "title": "Nuits d'été",
            "duration_minutes": "75",
            "default_price": "800",
            "epk_url": epk_url,
        }
    )


def test_a_link_without_scheme_is_completed_with_https():
    form = _form("exemple.fr/epk")

    assert form.is_valid(), form.errors
    assert form.cleaned_data["epk_url"] == "https://exemple.fr/epk"


@pytest.mark.parametrize("link", ["https://exemple.fr/epk", "http://exemple.fr/epk"])
def test_a_link_with_a_scheme_is_kept_as_typed(link):
    form = _form(link)

    assert form.is_valid(), form.errors
    assert form.cleaned_data["epk_url"] == link


def test_the_link_stays_optional_and_must_look_like_a_link():
    assert _form("").is_valid()
    assert not _form("pas un lien").is_valid()


def test_the_show_forms_raise_no_django_6_warning(rf, django_user_model):
    request = rf.get("/")
    request.user = django_user_model.objects.create_superuser(
        email="admin@example.org", password="Mot-de-passe-2026"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", RemovedInDjango60Warning)
        _form("exemple.fr").is_valid()
        admin.site._registry[Show].get_form(request)
