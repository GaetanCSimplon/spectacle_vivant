"""Name, logo, icons, slogan and e-mail signature of Bòrd Pro (charter, docs/cadrage/13)."""

import re
from pathlib import Path

import pytest
from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site
from django.core import mail
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db

ROOT = Path(__file__).resolve().parents[3]
SLOGAN = "Reprenez le contrôle de votre tournée."
SUBTITLE = "Contacts, dates, contrats, budgets et équipe : tout au même endroit."


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership


def test_the_brand_files_are_shipped():
    for name in (
        "logo-horizontal.png",
        "logo-mark.png",
        "favicon.ico",
        "favicon-16.png",
        "favicon-32.png",
        "favicon-48.png",
        "apple-touch-icon.png",
        "icon-192.png",
        "icon-512.png",
    ):
        assert (ROOT / "static/brand" / name).stat().st_size > 500, name


def test_the_icon_sizes_follow_the_charter():
    from PIL import Image

    for name, size in (
        ("favicon-16.png", 16),
        ("favicon-32.png", 32),
        ("favicon-48.png", 48),
        ("apple-touch-icon.png", 180),
        ("icon-192.png", 192),
        ("icon-512.png", 512),
    ):
        assert Image.open(ROOT / "static/brand" / name).size == (size, size), name
    assert Image.open(ROOT / "static/brand/logo-horizontal.png").width >= 120


def test_the_pages_declare_the_favicons_and_the_logo_has_a_text_alternative(client):
    _login(client)

    content = client.get(reverse("home")).content.decode()

    assert 'rel="icon"' in content and "brand/favicon.ico" in content
    assert 'rel="apple-touch-icon"' in content
    assert 'name="theme-color"' in content
    # The logo is in the left column and in the top bar of a phone: both have the alt text.
    assert content.count('alt="Bòrd Pro"') == 2 and "brand/logo-horizontal.png" in content


def test_logged_out_pages_show_the_logo_and_the_favicons(client):
    content = client.get(reverse("account_login")).content.decode()

    assert 'alt="Bòrd Pro"' in content and "brand/logo-horizontal.png" in content
    assert "brand/favicon-32.png" in content


def test_the_name_is_written_with_its_accent_everywhere_the_user_reads_it(client):
    _login(client)

    for url in (reverse("home"), reverse("legal-terms"), reverse("account_login")):
        content = client.get(url).content.decode()
        assert "BÒRD PRO" not in content
        assert "Bord Pro" not in content


def test_the_sign_in_page_says_your_activity_at_a_glance(client):
    content = client.get(reverse("account_login")).content.decode()

    assert "Votre activité, au clair." in content
    assert SLOGAN not in content


def test_the_sign_up_page_carries_the_slogan_and_the_subtitle(client):
    content = client.get(reverse("account_signup")).content.decode()

    assert SLOGAN in content and SUBTITLE in content


def test_the_home_page_of_a_new_structure_carries_the_slogan(client):
    _login(client)

    content = client.get(reverse("home")).content.decode()

    assert SLOGAN in content
    assert "Créez la première pour commencer" in content


def test_the_confirmation_e_mail_is_signed_with_the_name_and_the_slogan(client):
    Site.objects.update_or_create(pk=1, defaults={"domain": "bordpro.example", "name": "Bòrd Pro"})
    user = MembershipFactory().user
    address = EmailAddress.objects.create(user=user, email=user.email, verified=False, primary=True)

    address.send_confirmation()

    body = mail.outbox[-1].body
    assert "Bòrd Pro — Reprenez le contrôle de votre tournée." in body
    assert "bordpro.example" in body
    assert "Thank you for using" not in body and "Merci d'utiliser" not in body


def test_the_site_name_command_writes_the_new_name():
    source = (ROOT / "apps/core/management/commands/set_site_domain.py").read_text()

    assert '"name": "Bòrd Pro"' in source


def test_no_template_still_spells_the_old_name():
    leftovers = [
        str(path.relative_to(ROOT))
        for path in (ROOT / "templates").rglob("*")
        if path.is_file() and re.search(r"BÒRD PRO|Bord Pro", path.read_text(errors="ignore"))
    ]

    assert leftovers == []
