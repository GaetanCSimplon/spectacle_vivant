"""Charter v1.3: the four volets C/B/S/R, each with its colour AND its name or letter."""

import re
from pathlib import Path

import pytest
from django.urls import reverse

from apps.documents.services import generate_contract_pdf, mark_contract_signed
from apps.gigs import services as gig_services
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig, GigMember
from apps.roadmaps.models import Roadmap
from apps.tenants.factories import MembershipFactory, PersonFactory

pytestmark = pytest.mark.django_db

CSS = (Path(__file__).resolve().parents[3] / "css/source.css").read_text()


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _steps(gig):
    return {step["key"]: step["done"] for step in gig_services.date_progress(gig)}


def test_the_volets_have_the_colours_of_the_charter():
    def block(name):
        return CSS.split(f"  .volet-{name} {{")[1].split("}")[0]

    assert "var(--bord-brand-navy)" in block("contrats") and "var(--bord-surface)" in block(
        "contrats"
    )
    assert "var(--bord-brand-coral)" in block("budget") and "var(--bord-text)" in block("budget")
    assert "var(--bord-brand-ocean)" in block("social") and "var(--bord-surface)" in block("social")
    regie = block("regie")
    assert (
        "var(--bord-context-bg)" in regie and "1.5px solid" in regie
    )  # light blue needs its outline
    assert "dashed" in CSS.split("  .volet-todo {")[1].split("}")[0]


def test_a_new_date_has_no_volet_done():
    gig = GigFactory()

    assert _steps(gig) == {"contrats": False, "budget": False, "social": False, "regie": False}


def test_each_volet_is_done_by_its_own_event():
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)
    mark_contract_signed(gig)
    GigMember.objects.create(tenant=gig.tenant, gig=gig, person=PersonFactory(tenant=gig.tenant))
    Roadmap.objects.create(tenant=gig.tenant, gig=gig, is_published=True, token="t" * 20)

    assert _steps(gig) == {"contrats": True, "budget": False, "social": True, "regie": True}


def test_the_date_page_shows_the_four_letters_with_a_text_for_each(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant)

    content = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()

    for letter in "CBSR":
        assert f'aria-hidden="true">{letter}</span>' in content
    assert "Contrats : à faire" in content and "Régie : à faire" in content
    assert "volet-todo" in content


@pytest.mark.parametrize(
    ("route", "volet", "name"),
    [
        ("documents:contract-history", "contrats", "Contrats"),
        ("documents:billing", "budget", "Budget"),
        ("finance:page", "budget", "Budget"),
        ("roadmaps:editor", "regie", "Régie"),
    ],
)
def test_a_volet_page_carries_its_chip_with_the_name(client, route, volet, name):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant, status=Gig.Status.CONFIRMED)

    content = client.get(reverse(route, args=[gig.pk])).content.decode()

    assert re.search(rf'class="volet-chip volet-{volet}"[^>]*>.*?{name}', content, flags=re.S)
