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


SOCIAL_SECURITY_SHAPE = re.compile(r"^[1-478]\d{4}(\d{2}|2A|2B)\d{6}\d{2}$")


def normalize_social_security_number(value):
    """Spaces are only for reading: store the 15 characters, capitals, without them."""
    return re.sub(r"\s+", "", value or "").upper()


def format_social_security_number(value):
    """`185057800608491` -> `1 85 05 78 006 084 91`, as it is written on the card."""
    number = normalize_social_security_number(value)
    if len(number) != 15:
        return number
    parts = (number[0], number[1:3], number[3:5], number[5:7], number[7:10], number[10:13])
    return " ".join((*parts, number[13:]))


def validate_social_security_number(value):
    """Check the shape and the two-digit key (a typing mistake is caught almost every time).

    Corsica (2A / 2B) is counted as 19 / 18 in the key, as the national rule says.
    """
    number = normalize_social_security_number(value)
    if not SOCIAL_SECURITY_SHAPE.match(number):
        raise ValidationError(
            _("Un n° de sécurité sociale compte 15 caractères, par exemple 1 85 05 78 006 084 91.")
        )
    base = number[:13].replace("2A", "19").replace("2B", "18")
    if 97 - int(base) % 97 != int(number[13:]):
        raise ValidationError(
            _("Ce numéro de sécurité sociale semble contenir une erreur de saisie.")
        )
