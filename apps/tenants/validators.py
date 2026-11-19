import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

IBAN_SHAPE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")


def normalize_iban(value):
    """Spaces, dots and dashes are only for reading: store the IBAN as capitals without them."""
    return re.sub(r"[\s.-]+", "", value or "").upper()


def validate_iban(value):
    """Check the shape and the modulo-97 key, which catches most typing mistakes."""
    iban = normalize_iban(value)
    if not IBAN_SHAPE.match(iban):
        raise ValidationError(
            _(
                "Un IBAN commence par 2 lettres et 2 chiffres (FR76 pour la France, 27 caractères "
                "au total) : vous en avez saisi %(count)d. Vérifiez chaque caractère, "
                "en particulier la lettre O et le zéro 0, la lettre I et le chiffre 1."
            )
            % {"count": len(iban)}
        )
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


def normalize_siret(value):
    """Spaces and dots are only for reading: store the 14 digits."""
    return re.sub(r"[\s.]+", "", value or "")


def _luhn_ok(digits):
    total = 0
    for position, char in enumerate(reversed(digits)):
        number = int(char)
        if position % 2 == 1:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def validate_siret(value):
    """14 digits and a valid Luhn key (La Poste's establishments: digit sum divisible by 5)."""
    siret = normalize_siret(value)
    if not re.fullmatch(r"\d{14}", siret):
        raise ValidationError(_("Un SIRET comporte 14 chiffres, par exemple 123 456 789 00012."))
    # La Poste's establishments (SIREN 356 000 000) follow another rule: digit sum divisible by 5.
    la_poste = siret.startswith("356000000") and sum(int(char) for char in siret) % 5 == 0
    if not (_luhn_ok(siret) or la_poste):
        raise ValidationError(_("Ce SIRET semble contenir une erreur de saisie."))


def format_siret(value):
    """ "12345678900012" -> "123 456 789 00012" (a SIREN: "123 456 789"); anything else as is."""
    digits = normalize_siret(value)
    if re.fullmatch(r"\d{14}", digits):
        return f"{digits[:3]} {digits[3:6]} {digits[6:9]} {digits[9:]}"
    if re.fullmatch(r"\d{9}", digits):
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    return value or ""


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
