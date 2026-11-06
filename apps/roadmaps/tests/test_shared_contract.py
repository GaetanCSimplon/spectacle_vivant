"""The signed contract shown to the team (F-91, step B): off by default, owner only, personal
space only. The contract holds the price of the cession, so it never reaches the shared link."""

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse

from apps.documents import services as doc_services
from apps.documents.models import Contract
from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.roadmaps import documents as docs
from apps.roadmaps.factories import RoadmapFactory
from apps.roadmaps.services import public_context, publish
from apps.tenants import services as tenant_services
from apps.tenants.factories import MembershipFactory, PersonFactory

pytestmark = pytest.mark.django_db


def _login(client, role="owner"):
    membership = MembershipFactory(role=role)
    client.force_login(membership.user)
    return membership.tenant


def _member(gig):
    person = PersonFactory(tenant=gig.tenant)
    tenant_services.enable_team_space(person)
    person.refresh_from_db()
    GigMemberFactory(gig=gig, person=person, name=person.full_name)
    return person


def _signed_gig(tenant=None, signed_pdf=None, **kwargs):
    kwargs.setdefault("status", "confirmed")  # a contract can only be signed on a confirmed date
    gig = GigFactory(**({"tenant": tenant} if tenant else {}), **kwargs)
    doc_services.generate_contract_pdf(gig)
    doc_services.mark_contract_signed(gig, signed_pdf)
    return gig


def _share(roadmap, on=True):
    roadmap.share_signed_contract = on
    roadmap.save(update_fields=["share_signed_contract"])


def _contract_url(person, gig):
    return reverse("team-space-contract", args=[person.access_token, gig.pk])


def _page(client, person, gig):
    return client.get(
        reverse("team-space-gig", args=[person.access_token, gig.pk])
    ).content.decode()


# --- the artist's side --------------------------------------------------------------------------


def test_the_contract_is_hidden_by_default(client):
    gig = _signed_gig()
    roadmap = RoadmapFactory(gig=gig)
    person = _member(gig)

    assert "Contrat de cession signé" not in _page(client, person, gig)
    assert client.get(_contract_url(person, gig)).status_code == 404
    assert roadmap.share_signed_contract is False


def test_once_shown_the_signed_contract_is_listed_first_and_opens_in_the_browser(client):
    gig = _signed_gig()
    roadmap = RoadmapFactory(gig=gig)
    other = docs.add_document(
        roadmap, title="Plan", file=ContentFile(b"%PDF-1.4 plan", name="p.pdf"),
        kind="application/pdf", person=None, user=None,
    )  # fmt: skip
    person = _member(gig)
    _share(roadmap)

    page = _page(client, person, gig)
    response = client.get(_contract_url(person, gig))

    assert page.index("Contrat de cession signé") < page.index("Plan")
    assert other.title in page
    assert response.status_code == 200 and response["Content-Type"] == "application/pdf"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Cache-Control"] == "no-store"
    assert "noindex" in response["X-Robots-Tag"]
    assert response["Content-Disposition"].startswith("inline")
    assert b"".join(response.streaming_content).startswith(b"%PDF")


def test_the_signed_copy_uploaded_by_the_owner_wins_over_the_frozen_version(client):
    marker = b"%PDF-1.4 COPIE-SIGNEE-PAR-LES-DEUX-PARTIES"
    gig = _signed_gig(signed_pdf=ContentFile(marker, name="signed.pdf"))
    roadmap = RoadmapFactory(gig=gig)
    person = _member(gig)
    _share(roadmap)

    response = client.get(_contract_url(person, gig))

    assert b"".join(response.streaming_content) == marker


def test_without_an_uploaded_copy_the_frozen_version_is_shown(client):
    gig = _signed_gig()
    roadmap = RoadmapFactory(gig=gig)
    person = _member(gig)
    _share(roadmap)
    frozen = Contract.objects.get(gig=gig).signed_version.pdf_file

    response = client.get(_contract_url(person, gig))

    with frozen.open("rb") as handle:
        assert b"".join(response.streaming_content) == handle.read()


def test_a_draft_contract_is_never_shown_even_if_the_switch_is_on(client):
    gig = GigFactory()
    doc_services.generate_contract_pdf(gig)  # generated, not signed
    roadmap = RoadmapFactory(gig=gig)
    person = _member(gig)
    _share(roadmap)

    assert "Contrat de cession signé" not in _page(client, person, gig)
    assert client.get(_contract_url(person, gig)).status_code == 404


def test_turning_it_off_hides_it_at_once(client):
    gig = _signed_gig()
    roadmap = RoadmapFactory(gig=gig)
    person = _member(gig)
    _share(roadmap)
    assert client.get(_contract_url(person, gig)).status_code == 200

    _share(roadmap, on=False)

    assert client.get(_contract_url(person, gig)).status_code == 404
    assert "Contrat de cession signé" not in _page(client, person, gig)


def test_only_the_people_of_the_date_with_a_live_link_can_open_it(client):
    gig = _signed_gig()
    roadmap = RoadmapFactory(gig=gig)
    on_the_date = _member(gig)
    elsewhere = PersonFactory(tenant=gig.tenant)
    tenant_services.enable_team_space(elsewhere)
    elsewhere.refresh_from_db()
    stranger = PersonFactory()
    tenant_services.enable_team_space(stranger)
    stranger.refresh_from_db()
    _share(roadmap)

    assert client.get(_contract_url(on_the_date, gig)).status_code == 200
    assert client.get(_contract_url(elsewhere, gig)).status_code == 404
    assert client.get(_contract_url(stranger, gig)).status_code == 404
    assert client.get(reverse("team-space-contract", args=["nope", gig.pk])).status_code == 404
    old_url = _contract_url(on_the_date, gig)
    tenant_services.disable_team_space(on_the_date)
    assert client.get(old_url).status_code == 404


def test_a_cancelled_date_shows_no_contract(client):
    gig = _signed_gig()
    roadmap = RoadmapFactory(gig=gig)
    person = _member(gig)
    _share(roadmap)
    gig.status = "cancelled"
    gig.save(update_fields=["status"])

    assert client.get(_contract_url(person, gig)).status_code == 404


def test_the_shared_link_and_its_pdf_never_show_the_contract(client):
    gig = _signed_gig(price="7777.77")
    roadmap = RoadmapFactory(gig=gig)
    publish(roadmap)
    _share(roadmap)
    contract_url_fragment = "/contrat/"

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()

    assert "Contrat de cession signé" not in page and contract_url_fragment not in page
    assert "7777" not in page
    assert "share_signed_contract" not in public_context(roadmap)
    assert "documents" not in public_context(roadmap)


# --- the owner's side ---------------------------------------------------------------------------


def _toggle(client, gig, share):
    return client.post(reverse("roadmaps:contract-share", args=[gig.pk]), {"share": share})


def test_the_owner_shows_then_hides_the_contract(client):
    tenant = _login(client)
    gig = _signed_gig(tenant=tenant)
    roadmap = RoadmapFactory(gig=gig)

    response = _toggle(client, gig, "1")
    roadmap.refresh_from_db()

    assert response.status_code == 302 and response.url.endswith("#documents")
    assert roadmap.share_signed_contract is True
    page = client.get(reverse("roadmaps:editor", args=[gig.pk])).content.decode()
    assert "visible des personnes de la date" in page and "Ne plus montrer" in page

    _toggle(client, gig, "0")
    roadmap.refresh_from_db()
    assert roadmap.share_signed_contract is False


def test_the_editor_warns_about_the_price_and_offers_the_switch_only_once_signed(client):
    tenant = _login(client)
    signed = _signed_gig(tenant=tenant)
    draft = GigFactory(tenant=tenant)

    page = client.get(reverse("roadmaps:editor", args=[signed.pk])).content.decode()
    other = client.get(reverse("roadmaps:editor", args=[draft.pk])).content.decode()

    assert "Montrer le contrat signé à l'équipe" in page
    assert "contient le prix de la cession" in page
    assert "Pas encore de contrat signé" in other
    assert "Montrer le contrat signé" not in other


def test_a_draft_cannot_be_switched_on(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    roadmap = RoadmapFactory(gig=gig)

    _toggle(client, gig, "1")

    roadmap.refresh_from_db()
    assert roadmap.share_signed_contract is False


def test_a_plain_member_cannot_decide_and_does_not_see_the_button(client):
    tenant = _login(client, role="member")
    gig = _signed_gig(tenant=tenant)
    roadmap = RoadmapFactory(gig=gig)

    assert _toggle(client, gig, "1").status_code == 403
    roadmap.refresh_from_db()
    assert roadmap.share_signed_contract is False
    page = client.get(reverse("roadmaps:editor", args=[gig.pk])).content.decode()
    assert "Montrer le contrat signé à l'équipe" not in page
    assert "Seul le propriétaire" in page


def test_the_switch_only_accepts_post_and_not_for_a_foreign_date(client):
    tenant = _login(client)
    gig = _signed_gig(tenant=tenant)
    foreign = _signed_gig()
    foreign_roadmap = RoadmapFactory(gig=foreign)

    assert client.get(reverse("roadmaps:contract-share", args=[gig.pk])).status_code == 405
    assert _toggle(client, foreign, "1").status_code == 404
    foreign_roadmap.refresh_from_db()
    assert foreign_roadmap.share_signed_contract is False


def test_a_visitor_is_sent_to_login(client):
    gig = _signed_gig()

    response = _toggle(client, gig, "1")

    assert response.status_code == 302 and "login" in response.url
