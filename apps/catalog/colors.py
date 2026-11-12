"""The colour a show can be given, to tell shows apart at a glance (SPE-03).

A short palette, not a free colour picker: every colour is dark enough to be seen on a white page
(3:1 at least, checked by a test) and none is a state colour (green, amber, burgundy: they only
mean a status) nor the coral of the main action. The dot is decoration: the title of the show is
always written next to it. PROVISIONAL palette, to be validated with the graphic designer.
"""

from django.utils.translation import gettext_lazy as _

PALETTE = {
    "night": ("#10243F", _("Nuit")),
    "ocean": ("#007299", _("Océan")),
    "slate": ("#465A6C", _("Ardoise")),
    "indigo": ("#3F51A8", _("Indigo")),
    "violet": ("#6A3F9C", _("Violet")),
    "plum": ("#8A3A6E", _("Prune")),
    "copper": ("#A24A1F", _("Cuivre")),
    "brown": ("#6B4F2A", _("Brun")),
}
CHOICES = [(key, name) for key, (_hex, name) in PALETTE.items()]


def hex_of(key):
    """The colour code of a palette key, "" when there is none (or an unknown key)."""
    return PALETTE.get(key, ("", ""))[0]


def name_of(key):
    return PALETTE.get(key, ("", ""))[1]
