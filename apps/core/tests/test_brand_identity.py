"""Name, logo, icons, slogan and e-mail signature of Bòrd Pro (docs/marque/charte-graphique.md)."""

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
SLOGAN = "Prenez le contrôle de votre tournée."
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


def test_the_sign_in_page_carries_the_slogan_without_the_subtitle(client):
    content = client.get(reverse("account_login")).content.decode()

    assert SLOGAN in content
    assert SUBTITLE not in content
    assert "Votre activité, au clair." not in content


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
    assert "Bòrd Pro — Prenez le contrôle de votre tournée." in body
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


@pytest.mark.parametrize(
    ("url", "target"),
    [
        ("/favicon.ico", "brand/favicon.ico"),
        ("/apple-touch-icon.png", "brand/apple-touch-icon.png"),
    ],
)
def test_the_default_icon_addresses_lead_to_the_brand_icon_without_a_login(client, url, target):
    response = client.get(url)

    assert response.status_code == 302
    assert response.url.endswith(target)


def test_the_icon_is_the_monogram_without_the_name():
    """The favicon is the square monogram: its ratio is about 1, the logo's is about 2.1."""
    from PIL import Image

    favicon = Image.open(ROOT / "static/brand/favicon-48.png")
    logo = Image.open(ROOT / "static/brand/logo-horizontal.png")

    assert favicon.width == favicon.height
    assert logo.width / logo.height > 2


def test_the_server_error_page_declares_the_icon_too():
    page = (ROOT / "templates/500.html").read_text()

    assert 'rel="icon"' in page and "/static/brand/favicon.ico" in page


LEGAL_MENTION = (
    "Bòrd Pro facilite la préparation et le suivi administratif ; il ne remplace pas les "
    "obligations légales ni un conseil juridique, social ou comptable personnalisé."
)


def test_the_terms_of_use_carry_the_charter_mention(client):
    content = client.get(reverse("legal-terms")).content.decode()

    assert " ".join(content.split()).count(LEGAL_MENTION) == 1


def test_the_contract_and_billing_screens_carry_the_mention(client):
    from apps.documents import invoicing
    from apps.documents.models import Invoice
    from apps.finance.tests.helpers import TENANT_FIELDS, make_gig

    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    gig = make_gig(tenant=membership.tenant)
    invoice = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    quote = invoicing.create_quote(gig)

    urls = [
        reverse("documents:contract-history", args=[gig.pk]),
        reverse("documents:contract-complete", args=[gig.pk]),
        reverse("documents:billing", args=[gig.pk]),
        reverse("documents:document-detail", args=[gig.pk, "factures", invoice.pk]),
        reverse("documents:document-detail", args=[gig.pk, "devis", quote.pk]),
    ]
    for url in urls:
        content = " ".join(client.get(url).content.decode().split())
        assert LEGAL_MENTION in content, url


def test_the_mention_is_not_repeated_on_the_other_screens(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    for name in ("home", "gigs:list", "tenants:profile"):
        content = " ".join(client.get(reverse(name)).content.decode().split())
        assert LEGAL_MENTION not in content
