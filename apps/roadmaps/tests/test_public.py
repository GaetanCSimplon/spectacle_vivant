import datetime
import html as html_lib
import re

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.addressbook.factories import ContactFactory
from apps.documents.models import Contract
from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.tenants.factories import MembershipFactory

from ..factories import LodgingFactory, MealFactory, RoadmapFactory, RoadmapSlotFactory
from ..services import public_context, publish, revoke

pytestmark = pytest.mark.django_db

SECRETS = [
    "7777.77",  # price
    "CONDITIONS-SECRETES",
    "FACTURATION-SECRETE",  # promoter billing address
    "ORGANISATEUR-SECRET",  # promoter name
    "secret.perso@example.com",  # e-mails
    "C-2026-",  # contract reference
]


def _build_gig():
    gig = GigFactory(
        price="7777.77",
        conditions="CONDITIONS-SECRETES",
        promoter__name="ORGANISATEUR-SECRET",
        promoter__billing_address="FACTURATION-SECRETE",
        show__title="Mon Spectacle",
        show__group_name="Les Groupies",
        venue__name="Salle Polyvalente",
        venue__address="12 rue des Lilas 69000 Lyon",
        venue__phone="04 78 00 00 00",
        venue__access_info="Parking derrière",
        crew_headcount=5,
    )
    Contract.objects.create(gig=gig, tenant=gig.tenant, reference="C-2026-001")
    ContactFactory(
        promoter=None,
        venue=gig.venue,
        tenant=gig.tenant,
        name="Régisseuse Rita",
        role="Technique",
        phone="06 11 22 33 44",
        email="secret.perso@example.com",
    )
    GigMemberFactory(
        gig=gig,
        name="Léa Chanteuse",
        role="Chant",
        phone="+33 6 99 88 77 66",
        email="secret.perso@example.com",
    )
    roadmap = RoadmapFactory(gig=gig, notes="Parking à droite")
    RoadmapSlotFactory(roadmap=roadmap, time=datetime.time(17, 0), label="Balances")
    LodgingFactory(roadmap=roadmap, name="Hôtel du Lac", address="3 quai du Lac")
    MealFactory(roadmap=roadmap, place="Brasserie", time=datetime.time(19, 0))
    publish(roadmap)
    return roadmap


@pytest.fixture
def roadmap():
    return _build_gig()


def _url(roadmap, name="roadmap-public"):
    return reverse(name, args=[roadmap.token])


def _text(html):
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL)
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", html)).split())


# --- access --------------------------------------------------------------------


def test_the_link_works_without_an_account(client, roadmap):
    response = client.get(_url(roadmap))

    assert response.status_code == 200
    text = response.content.decode()
    for expected in [
        "Mon Spectacle", "Les Groupies", "Salle Polyvalente", "12 rue des Lilas",
        "Parking derrière", "17:00", "Balances", "Hôtel du Lac", "Brasserie", "5 personnes",
        "Parking à droite", "Léa Chanteuse", "Régisseuse Rita",
    ]:  # fmt: skip
        assert expected in text


def test_the_page_has_call_and_route_buttons(client, roadmap):
    text = client.get(_url(roadmap)).content.decode()

    assert 'href="tel:0478000000"' in text
    assert 'href="tel:+33699887766"' in text
    assert "openstreetmap.org/search?query=12%20rue%20des%20Lilas" in text
    assert "google" not in text.lower()


def test_unknown_token_is_404(client, roadmap):
    assert client.get(reverse("roadmap-public", args=["nimportequoi"])).status_code == 404
    assert client.get(reverse("roadmap-public-pdf", args=["nimportequoi"])).status_code == 404


def test_a_modified_token_does_not_open_anything(client, roadmap):
    other = RoadmapFactory()
    publish(other)

    for token in (roadmap.token[:-1], roadmap.token + "a", roadmap.token.swapcase()):
        assert client.get(reverse("roadmap-public", args=[token])).status_code == 404


def test_revoked_link_is_404(client, roadmap):
    url, pdf_url = _url(roadmap), _url(roadmap, "roadmap-public-pdf")
    revoke(roadmap)

    assert client.get(url).status_code == 404
    assert client.get(pdf_url).status_code == 404


def test_old_link_stays_dead_after_stop_then_reactivate(client, roadmap):
    old_url = _url(roadmap)
    revoke(roadmap)
    publish(roadmap)

    assert client.get(old_url).status_code == 404
    assert client.get(_url(roadmap)).status_code == 200


def test_not_published_with_a_token_is_404(client, roadmap):
    roadmap.is_published = False
    roadmap.save()

    assert client.get(_url(roadmap)).status_code == 404


def test_an_empty_token_never_matches(client, roadmap):
    revoke(roadmap)

    assert client.get("/feuille-de-route//").status_code == 404


def test_signed_in_user_without_structure_can_open_the_link(client, roadmap):
    from apps.accounts.factories import UserFactory

    client.force_login(UserFactory())

    assert client.get(_url(roadmap)).status_code == 200


def test_another_tenants_user_sees_the_same_public_page_only(client, roadmap):
    client.force_login(MembershipFactory().user)

    response = client.get(_url(roadmap))

    assert response.status_code == 200
    assert "7777.77" not in response.content.decode()


# --- headers -------------------------------------------------------------------


@pytest.mark.parametrize("name", ["roadmap-public", "roadmap-public-pdf"])
def test_protective_headers(client, roadmap, name):
    response = client.get(_url(roadmap, name))

    assert response["Cache-Control"] == "no-store"
    assert "noindex" in response["X-Robots-Tag"]
    assert response["Referrer-Policy"] == "no-referrer"


# --- no leaks -------------------------------------------------------------------


def test_no_sensitive_data_in_the_public_html(client, roadmap):
    # Even with an issued invoice and a quote around, nothing of it shows.
    text = client.get(_url(roadmap)).content.decode()

    for secret in SECRETS:
        assert secret not in text, secret
    for word in ("Confirmée", "Signée", "Option", "Annulée", "€"):
        assert word not in _text(text), word


def test_no_sensitive_data_in_the_pdf_content(roadmap):
    html = render_to_string("roadmaps/roadmap_pdf.html", public_context(roadmap))

    for secret in SECRETS:
        assert secret not in html, secret
    assert "Salle Polyvalente" in html
    assert "Léa Chanteuse" in html


def test_public_context_is_a_whitelist(roadmap):
    assert set(public_context(roadmap)) == {
        "show_title", "group_name", "date", "venue", "crew_headcount", "slots", "lodgings",
        "meals", "notes", "members", "venue_contacts",
    }  # fmt: skip
    assert set(public_context(roadmap)["venue"]) == {
        "name", "address", "access_info", "phone", "tel",
    }  # fmt: skip


def test_the_public_pdf_is_a_real_pdf(client, roadmap):
    response = client.get(_url(roadmap, "roadmap-public-pdf"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


# --- the owner's PDF --------------------------------------------------------------


def test_owner_gets_the_pdf_even_when_sharing_is_off(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant)
    RoadmapFactory(gig=gig)

    response = client.get(reverse("roadmaps:pdf", args=[gig.pk]))

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_owner_pdf_needs_login_and_the_right_tenant(client):
    gig = GigFactory()
    url = reverse("roadmaps:pdf", args=[gig.pk])

    assert client.get(url).status_code == 302
    client.force_login(MembershipFactory().user)
    assert client.get(url).status_code == 404
