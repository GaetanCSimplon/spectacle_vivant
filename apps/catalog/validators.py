"""The object number of a show, as the rights society writes it (SPE-02)."""

import re

from django import forms
from django.utils.translation import gettext_lazy as _

# 22-3-P-513447-57: two digits for the year, one for the agreement, one letter for the kind of
# project, six digits of sequence, two of key. Typed with or without the dashes.
OBJECT_NUMBER = re.compile(r"(\d{2})[\s.-]*(\d)[\s.-]*([A-Za-z])[\s.-]*(\d{6})[\s.-]*(\d{2})")
HELP = _("Par exemple 22-3-P-513447-57 (les tirets sont facultatifs).")


def normalize_object_number(value):
    """ "223P51344757" -> "22-3-P-513447-57"; another shape is returned as typed."""
    value = (value or "").strip()
    match = OBJECT_NUMBER.fullmatch(value)
    if not match:
        return value
    year, agreement, kind, sequence, key = match.groups()
    return f"{year}-{agreement}-{kind.upper()}-{sequence}-{key}"


class ObjectNumberMixin:
    """Cleans `sacem_object_number` of a show form: the format is checked and written the same
    way everywhere. A value already stored that does not follow the format (typed before this
    check existed) is kept as long as it is not changed, so a show can always be saved."""

    def clean_sacem_object_number(self):
        value = normalize_object_number(self.cleaned_data["sacem_object_number"])
        if value and not OBJECT_NUMBER.fullmatch(value):
            if value != self.instance.sacem_object_number:
                raise forms.ValidationError(
                    _(
                        "Un n° d'objet ressemble à 22-3-P-513447-57 : année, convention, "
                        "lettre du type de projet, 6 chiffres, clé."
                    )
                )
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("sacem_object_number")
        if field is not None:
            field.help_text = HELP
