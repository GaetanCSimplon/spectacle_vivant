"""Documents the owner puts on a date for the team (F-91): who may open what, and what is checked
on the way in. They are only ever seen from a personal space, never from the shared roadmap link."""

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.roadmaps import documents as docs
from apps.roadmaps.factories import RoadmapFactory
from apps.roadmaps.models import RoadmapDocument
from apps.roadmaps.services import public_context, publish
from apps.tenants import services as tenant_services
from apps.tenants.factories import MembershipFactory, PersonFactory

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4\n%fake but starts like a PDF\n"
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


def _file(content=PDF, name="billet.pdf"):
    return SimpleUploadedFile(name, content)


def _login(client, role="owner"):
    membership = MembershipFactory(role=role)
    client.force_login(membership.user)
    return membership.tenant


def _team_member(gig, **kwargs):
    person = PersonFactory(tenant=gig.tenant, **kwargs)
    tenant_services.enable_team_space(person)
    person.refresh_from_db()
    GigMemberFactory(gig=gig, person=person, name=person.full_name)
    return person


def _add(client, gig, **data):
    data.setdefault("title", "Billet de train")
    data.setdefault("file", _file())
    return client.post(reverse("roadmaps:document-add", args=[gig.pk]), data)


def _doc(roadmap, person=None, title="Billet", content=PDF, kind="application/pdf"):
    return docs.add_document(
        roadmap,
        title=title,
        file=SimpleUploadedFile("f.bin", content),
        kind=kind,
        person=person,
        user=None,
    )


def _team_doc_url(person, gig, document):
    return reverse("team-space-document", args=[person.access_token, gig.pk, document.pk])


# --- adding -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content, name, kind",
    [(PDF, "a.pdf", "application/pdf"), (JPEG, "a.jpg", "image/jpeg"), (PNG, "a.png", "image/png")],
)
def test_a_pdf_a_jpeg_or_a_png_is_accepted(client, content, name, kind):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    response = _add(client, gig, file=_file(content, name))

    assert response.status_code == 302 and response.url.endswith("#documents")
    document = RoadmapDocument.objects.get()
    assert document.content_type == kind and document.tenant == tenant
    assert document.title == "Billet de train" and document.person is None


def test_the_kind_comes_from_the_content_never_from_the_name(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    _add(client, gig, file=_file(PNG, "faux.pdf"))
    refused = _add(client, gig, file=_file(b"<script>alert(1)</script>", "page.pdf"))

    assert RoadmapDocument.objects.get().content_type == "image/png"
    assert refused.status_code == 200  # the form is shown again with its error
    assert "doit être un PDF, un JPEG ou un PNG" in refused.content.decode()


@pytest.mark.parametrize(
    "content", [b"", b"just text", b"MZ\x90\x00 an executable", b"GIF89a....", b"<svg></svg>"]
)
def test_anything_else_is_refused(client, content):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    _add(client, gig, file=_file(content, "x.pdf"))

    assert not RoadmapDocument.objects.exists()


def test_a_file_over_ten_megabytes_is_refused(client, monkeypatch):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    monkeypatch.setattr(docs, "MAX_SIZE", 10)

    response = _add(client, gig, file=_file(PDF + b"0" * 50))

    assert not RoadmapDocument.objects.exists()
    assert "trop lourd" in response.content.decode()


def test_a_title_is_required(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    _add(client, gig, title="   ")
    _add(client, gig, title="")

    assert not RoadmapDocument.objects.exists()


def test_the_recipient_must_be_a_person_of_this_date(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    on_the_date = _team_member(gig)
    elsewhere = PersonFactory(tenant=tenant)  # in the team, but not on this date
    stranger = PersonFactory()  # another structure

    assert _add(client, gig, person=on_the_date.pk).status_code == 302
    for person in (elsewhere, stranger):
        assert _add(client, gig, person=person.pk).status_code == 200
    assert RoadmapDocument.objects.get().person == on_the_date


def test_a_date_holds_a_limited_number_of_documents(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    roadmap = RoadmapFactory(gig=gig)
    for n in range(RoadmapDocument.MAX_PER_ROADMAP):
        _doc(roadmap, title=f"d{n}")

    response = _add(client, gig)

    assert response.status_code == 302
    assert roadmap.documents.count() == RoadmapDocument.MAX_PER_ROADMAP


def test_only_post_adds_and_only_post_deletes(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    document = _doc(RoadmapFactory(gig=gig))

    assert client.get(reverse("roadmaps:document-add", args=[gig.pk])).status_code == 405
    assert (
        client.get(reverse("roadmaps:document-delete", args=[gig.pk, document.pk])).status_code
        == 405
    )


# --- the owner's side ---------------------------------------------------------------------------


def test_the_editor_lists_the_documents_and_who_they_are_for(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    roadmap = RoadmapFactory(gig=gig)
    person = _team_member(gig, first_name="Léa", last_name="Chanteuse")
    _doc(roadmap, title="Plan de salle")
    _doc(roadmap, person=person, title="Billet de Léa")
    nolink = PersonFactory(tenant=tenant)
    GigMemberFactory(gig=gig, person=nolink, name=nolink.full_name)
    _doc(roadmap, person=nolink, title="Billet sans espace")

    page = client.get(reverse("roadmaps:editor", args=[gig.pk])).content.decode()

    assert "Plan de salle" in page and "Pour toute l'équipe de la date" in page
    assert "Pour Léa Chanteuse seulement" in page
    assert "cette personne ne peut pas le voir" in page
    assert "jamais avec le lien de partage" in page


def test_the_owner_opens_a_document_inline_with_a_safe_type(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    document = _doc(
        RoadmapFactory(gig=gig), title='Billet "Paris"/../x', content=PNG, kind="image/png"
    )

    response = client.get(reverse("roadmaps:document-file", args=[gig.pk, document.pk]))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Cache-Control"] == "no-store"
    disposition = response["Content-Disposition"]
    assert disposition.startswith("inline") and ".png" in disposition
    assert ".." not in disposition and "/" not in disposition.split("filename=")[1]
    assert b"".join(response.streaming_content) == PNG


def test_deleting_removes_the_row_and_the_stored_file(client, django_capture_on_commit_callbacks):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant)
    document = _doc(RoadmapFactory(gig=gig))
    name, storage = document.file.name, document.file.storage
    assert storage.exists(name)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("roadmaps:document-delete", args=[gig.pk, document.pk]))

    assert not RoadmapDocument.objects.exists()
    assert not storage.exists(name)


def test_deleting_a_person_takes_their_documents_and_files_with_them(
    django_capture_on_commit_callbacks,
):
    gig = GigFactory()
    person = _team_member(gig)
    document = _doc(RoadmapFactory(gig=gig), person=person)
    name, storage = document.file.name, document.file.storage

    with django_capture_on_commit_callbacks(execute=True):
        person.delete()

    assert not RoadmapDocument.objects.exists()  # never turned into a document for everybody
    assert not storage.exists(name)


@pytest.mark.parametrize("name", ["document-add", "document-file", "document-delete"])
def test_another_structure_gets_a_404_on_the_owner_routes(client, name):
    _login(client)
    foreign = GigFactory()
    document = _doc(RoadmapFactory(gig=foreign))
    args = [foreign.pk] if name == "document-add" else [foreign.pk, document.pk]

    url = reverse(f"roadmaps:{name}", args=args)
    response = client.get(url) if name == "document-file" else client.post(url)

    assert response.status_code == 404
    assert RoadmapDocument.objects.count() == 1


def test_a_document_of_another_date_is_not_reachable_through_this_one(client):
    tenant = _login(client)
    gig, other_gig = GigFactory(tenant=tenant), GigFactory(tenant=tenant)
    document = _doc(RoadmapFactory(gig=other_gig))

    assert (
        client.get(reverse("roadmaps:document-file", args=[gig.pk, document.pk])).status_code == 404
    )
    assert (
        client.post(reverse("roadmaps:document-delete", args=[gig.pk, document.pk])).status_code
        == 404
    )


# --- the team member's side ---------------------------------------------------------------------


def test_a_person_sees_the_documents_for_the_whole_team_and_their_own(client):
    gig = GigFactory(date=datetime.date.today() + datetime.timedelta(days=3))
    roadmap = RoadmapFactory(gig=gig)
    lea, max_ = _team_member(gig, first_name="Léa"), _team_member(gig, first_name="Max")
    _doc(roadmap, title="Plan de salle")
    _doc(roadmap, person=lea, title="Billet de Léa")
    _doc(roadmap, person=max_, title="Billet de Max")

    page = client.get(reverse("team-space-gig", args=[lea.access_token, gig.pk])).content.decode()

    assert "Plan de salle" in page and "Billet de Léa" in page
    assert "Billet de Max" not in page
    assert "Mes documents" in page


def test_a_person_opens_their_documents_but_not_the_ones_of_somebody_else(client):
    gig = GigFactory()
    roadmap = RoadmapFactory(gig=gig)
    lea, max_ = _team_member(gig), _team_member(gig)
    shared = _doc(roadmap, title="Commun", content=JPEG, kind="image/jpeg")
    private = _doc(roadmap, person=max_, title="Privé de Max")

    ok = client.get(_team_doc_url(lea, gig, shared))
    refused = client.get(_team_doc_url(lea, gig, private))

    assert ok.status_code == 200 and ok["Content-Type"] == "image/jpeg"
    assert ok["Cache-Control"] == "no-store"
    assert "noindex" in ok["X-Robots-Tag"]
    assert ok["X-Content-Type-Options"] == "nosniff"
    assert refused.status_code == 404
    assert client.get(_team_doc_url(max_, gig, private)).status_code == 200


def test_a_document_of_a_date_the_person_is_not_on_is_a_404(client):
    gig, other_gig = GigFactory(), None
    other_gig = GigFactory(tenant=gig.tenant)
    lea = _team_member(gig)
    foreign_doc = _doc(RoadmapFactory(gig=other_gig), title="Autre date")

    url = reverse("team-space-document", args=[lea.access_token, other_gig.pk, foreign_doc.pk])
    wrong_gig = reverse("team-space-document", args=[lea.access_token, gig.pk, foreign_doc.pk])

    assert client.get(url).status_code == 404
    assert client.get(wrong_gig).status_code == 404


def test_a_cancelled_date_gives_no_document(client):
    gig = GigFactory(status="cancelled")
    lea = _team_member(gig)
    document = _doc(RoadmapFactory(gig=gig))

    assert client.get(_team_doc_url(lea, gig, document)).status_code == 404


def test_a_dead_or_unknown_token_opens_nothing(client):
    gig = GigFactory()
    lea = _team_member(gig)
    document = _doc(RoadmapFactory(gig=gig))
    url = _team_doc_url(lea, gig, document)
    tenant_services.disable_team_space(lea)

    assert client.get(url).status_code == 404
    assert (
        client.get(reverse("team-space-document", args=["nope", gig.pk, document.pk])).status_code
        == 404
    )


def test_a_person_of_another_structure_cannot_open_my_document(client):
    gig = GigFactory()
    document = _doc(RoadmapFactory(gig=gig))
    stranger = PersonFactory()
    tenant_services.enable_team_space(stranger)
    stranger.refresh_from_db()

    url = reverse("team-space-document", args=[stranger.access_token, gig.pk, document.pk])

    assert client.get(url).status_code == 404


def test_an_unknown_document_is_a_404(client):
    gig = GigFactory()
    lea = _team_member(gig)
    RoadmapFactory(gig=gig)

    assert (
        client.get(
            reverse("team-space-document", args=[lea.access_token, gig.pk, 9999])
        ).status_code
        == 404
    )


# --- never on the shared link -------------------------------------------------------------------


def test_the_shared_roadmap_link_and_its_pdf_never_show_a_document(client):
    gig = GigFactory()
    roadmap = RoadmapFactory(gig=gig)
    publish(roadmap)
    _doc(roadmap, title="TITRE-SECRET-DU-BILLET")

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()

    assert "TITRE-SECRET-DU-BILLET" not in page and "Mes documents" not in page
    assert "documents" not in public_context(roadmap)
    assert (
        b"TITRE-SECRET-DU-BILLET"
        not in client.get(reverse("roadmap-public-pdf", args=[roadmap.token])).content
    )
