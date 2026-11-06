"""Documents the owner puts on a date for the team (F-91).

Who sees what: a document is for one person or for the whole team of the date, and is seen from
the personal space of those people only (never from the shared roadmap link).
"""

from django.db.models import Q

from .models import RoadmapDocument

MAX_SIZE = 10 * 1024 * 1024
# What a file must start with, judged by its content and not by its name.
SIGNATURES = (
    (b"%PDF-", RoadmapDocument.Kind.PDF),
    (b"\xff\xd8\xff", RoadmapDocument.Kind.JPEG),
    (b"\x89PNG\r\n\x1a\n", RoadmapDocument.Kind.PNG),
)


class TooManyDocuments(Exception):
    """The date already holds `RoadmapDocument.MAX_PER_ROADMAP` documents."""


def kind_of(head):
    """The kind of file a first few bytes announce, or None."""
    for signature, kind in SIGNATURES:
        if head.startswith(signature):
            return kind
    return None


def audience_choices(gig):
    """People of the date who can be the recipient of a document: the ones picked from the team."""
    return [member.person for member in gig.members.select_related("person") if member.person_id]


def visible_to(roadmap, person):
    """The documents of this roadmap a person may open: for the whole team or for them."""
    return roadmap.documents.filter(Q(person=None) | Q(person=person), tenant=roadmap.tenant)


def add_document(roadmap, *, title, file, kind, person, user):
    if roadmap.documents.count() >= RoadmapDocument.MAX_PER_ROADMAP:
        raise TooManyDocuments
    return RoadmapDocument.objects.create(
        tenant=roadmap.tenant,
        roadmap=roadmap,
        title=title,
        file=file,
        content_type=kind,
        person=person,
        created_by=user,
    )
