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


BIC_SHAPE = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")


def normalize_bic(value):
    return re.sub(r"\s+", "", value or "").upper()


def validate_bic(value):
    if not BIC_SHAPE.match(normalize_bic(value)):
        raise ValidationError(_("Un BIC comporte 8 ou 11 caractères, par exemple AGRIFRPP."))


APE_SHAPE = re.compile(r"^\d{4}[A-Z]$")


def normalize_code_ape(value):
    """Capitals without spaces or dot, so "90.01 z" is stored as 9001Z."""
    return re.sub(r"[\s.]+", "", value or "").upper()


def validate_code_ape(value):
    if not APE_SHAPE.match(normalize_code_ape(value)):
        raise ValidationError(
            _("Un code APE s'écrit avec 4 chiffres et 1 lettre, par exemple 9001Z.")
        )
