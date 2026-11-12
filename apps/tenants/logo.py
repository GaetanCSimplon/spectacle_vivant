"""The logo of a structure, printed at the top of its quotes, invoices and contracts (STR-07).

Stored privately (an unguessable path, never a public address). Only a PNG or a JPEG of 2 MB at
most is accepted, judged by its content and not by its name: an SVG can carry code, so it is
refused. A quote or an invoice keeps a copy of the logo it was issued with (the issuer data is
frozen at issue, like the legal mentions).
"""

import base64
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.translation import gettext_lazy as _

MAX_SIZE = 2 * 1024 * 1024
SIGNATURES = ((b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"))


def kind_of(head):
    """The image type a first few bytes announce, or None."""
    for signature, kind in SIGNATURES:
        if head.startswith(signature):
            return kind
    return None


def check_upload(file):
    """Raise a ValueError with a message for the user if the file cannot be a logo."""
    if file.size > MAX_SIZE:
        raise ValueError(_("Le logo est trop lourd (2 Mo au maximum)."))
    head = file.read(8)
    file.seek(0)
    if kind_of(head) is None:
        raise ValueError(_("Le logo doit être une image PNG ou JPEG."))


def data_uri(name):
    """The file as a `data:` address for the PDF (no network, no public URL), "" if there is none.

    A file that went missing from the storage gives "" too: a document must never fail to print
    because its logo is gone.
    """
    if not name:
        return ""
    try:
        with default_storage.open(name, "rb") as stored:
            content = stored.read()
    except OSError:
        return ""
    kind = kind_of(content[:8])
    if kind is None:
        return ""
    return f"data:{kind};base64,{base64.b64encode(content).decode('ascii')}"


def snapshot_copy(name):
    """A private copy of the logo for an issued document, and its name ("" without a logo)."""
    if not name:
        return ""
    try:
        with default_storage.open(name, "rb") as stored:
            content = stored.read()
    except OSError:
        return ""
    extension = "png" if kind_of(content[:8]) == "image/png" else "jpg"
    return default_storage.save(
        f"document-logos/{uuid.uuid4().hex}/logo.{extension}", ContentFile(content)
    )
