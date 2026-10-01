import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

IBAN_SHAPE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")


def normalize_iban(value):
    """Spaces are only for reading: store the IBAN as capitals without them."""
    return re.sub(r"\s+", "", value or "").upper()


def validate_iban(value):
    """Check the shape and the modulo-97 key, which catches most typing mistakes."""
    iban = normalize_iban(value)
    if not IBAN_SHAPE.match(iban):
        raise ValidationError(_("Cet IBAN n'a pas un format valide."))
    moved = iban[4:] + iban[:4]
    as_number = "".join(str(int(char, 36)) for char in moved)
    if int(as_number) % 97 != 1:
        raise ValidationError(_("Cet IBAN semble contenir une erreur de saisie."))
