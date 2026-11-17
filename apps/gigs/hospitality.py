"""Who takes the meals and the lodging in charge (recette n°1, CTR-07).

The contract prints one sentence per item (`Gig.meals`, `Gig.lodging`): it is composed here from
the structured answers, so that the contract templates did not have to change. The roadmap
shows only who takes it in charge and how many, never the free text, which may talk about money.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class CoveredBy(models.TextChoices):
    ORGANISER = "organiser", _("L'organisateur")
    PRODUCER = "producer", _("Ma structure (le producteur)")
    SHARED = "shared", _("Partagé")
    NONE = "none", _("Non concerné")


# The words of the contract (the Organisateur and the Producteur).
CONTRACT_PHRASES = {
    CoveredBy.ORGANISER: "À la charge de l'Organisateur",
    CoveredBy.PRODUCER: "À la charge du Producteur",
    CoveredBy.SHARED: "Pris en charge à frais partagés",
    CoveredBy.NONE: "Non concerné",
}
# What a person reading the roadmap is told.
ROADMAP_PHRASES = {
    CoveredBy.ORGANISER: "pris en charge par l'organisateur",
    CoveredBy.PRODUCER: "pris en charge par le producteur",
    CoveredBy.SHARED: "pris en charge à frais partagés",
}


def _plural(count, one, many):
    return f"{count} {one if count == 1 else many}"


def compose(covered_by, count, unit, notes, people=None):
    """The sentence of the contract: "À la charge de l'Organisateur : 4 personnes, 8 repas"."""
    sentence = CONTRACT_PHRASES.get(covered_by, "")
    details = []
    if covered_by != CoveredBy.NONE:
        if people:
            details.append(_plural(people, "personne", "personnes"))
        if count:
            details.append(_plural(count, *unit))
    if details:
        joined = ", ".join(details)
        sentence = f"{sentence} : {joined}" if sentence else joined
    notes = " ".join((notes or "").split())
    if notes:
        sentence = f"{sentence}. {notes}" if sentence else notes
    return sentence


MEAL_UNIT = ("repas", "repas")
NIGHT_UNIT = ("nuit", "nuits")


def roadmap_line(covered_by, count, unit):
    """ "pris en charge par l'organisateur · 8 repas", or "" when there is nothing to say."""
    phrase = ROADMAP_PHRASES.get(covered_by)
    if not phrase:
        return ""
    return f"{phrase} · {_plural(count, *unit)}" if count else phrase
