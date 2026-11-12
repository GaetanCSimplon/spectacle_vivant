"""Documents the owner puts on a date for the team (F-91).

Who sees what: a document is for one person or for the whole team of the date, and is seen from
the personal space of those people only (never from the shared roadmap link).
"""

from django.db.models import Q

from apps.documents.models import Contract

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


def add_document(roadmap, *, title, file, kind, person, user, slot=None):
    if roadmap.documents.count() >= RoadmapDocument.MAX_PER_ROADMAP:
        raise TooManyDocuments
    return RoadmapDocument.objects.create(
        tenant=roadmap.tenant,
        roadmap=roadmap,
        title=title,
        file=file,
        content_type=kind,
        person=person,
        slot=slot,
        created_by=user,
    )


def signed_contract(gig):
    """The signed contract of a date, or None (a draft is never shown to anybody)."""
    return Contract.objects.filter(
        gig=gig, tenant=gig.tenant, status=Contract.Status.SIGNED
    ).first()


def shared_contract_file(roadmap):
    """The file of the signed contract if the owner chose to show it to the team, else None.

    The signed copy the owner uploaded wins; otherwise the version frozen at the signature.
    """
    if not roadmap.share_signed_contract:
        return None
    contract = signed_contract(roadmap.gig)
    if contract is None:
        return None
    if contract.signed_pdf:
        return contract.signed_pdf
    if contract.signed_version_id:
        return contract.signed_version.pdf_file
    return None
