"""Charter v1.3: the gimic in empty states and as the "signed" moment; same icons in both menus."""

import re

import pytest
from django.urls import reverse

from apps.documents.services import generate_contract_pdf
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def test_the_sidebar_and_the_burger_menu_use_the_same_icons(client):
    """NAV-01 (recette n°1): an icon on every link, the same on the desktop column and burger."""
    client.force_login(MembershipFactory().user)

    content = client.get(reverse("home")).content.decode()
    sidebar = content.split("<aside")[1].split("</aside>")[0]
    burger = content.split("<details")[1].split("</details>")[0]

    def icons(html):
        nav = html.split("<nav", 1)[1].split("</nav>", 1)[0]
        return re.findall(r'<svg aria-hidden="true" width="20"[^>]*>(.*?)</svg>', nav, re.S)

    assert len(icons(sidebar)) == len(icons(burger)) == 5  # one per link
    assert icons(sidebar) == icons(burger)
    assert "brand/gimic-creme.svg" not in content


def test_the_empty_list_of_dates_shows_the_navy_gimic_and_one_action(client):
    client.force_login(MembershipFactory().user)

    content = client.get(reverse("gigs:list")).content.decode()

    assert "brand/gimic-nuit.svg" in content and "Aucune date." in content
    assert reverse("gigs:wizard-show") in content


def test_a_list_with_dates_has_no_empty_state(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    GigFactory(tenant=membership.tenant)

    assert "brand/gimic-nuit.svg" not in client.get(reverse("gigs:list")).content.decode()


def test_the_empty_document_library_shows_the_gimic_but_a_filter_without_result_does_not(client):
    client.force_login(MembershipFactory().user)

    empty = client.get(reverse("document-library")).content.decode()

    assert "brand/gimic-nuit.svg" in empty and "Aucun document émis." in empty


def test_signing_a_contract_shows_the_coral_gimic_moment_once(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant, status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)

    response = client.post(reverse("documents:contract-sign", args=[gig.pk]), follow=True)
    content = response.content.decode()

    assert "Contrat signé." in content and content.count("brand/gimic-accent.svg") == 1
    assert "son PDF est figé" in content
    again = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()
    assert "brand/gimic-accent.svg" not in again  # the message is shown once
