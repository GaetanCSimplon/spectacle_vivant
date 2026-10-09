"""Suggestions for the free-text qualification fields of a Promoter (F-15)."""

from .models import Promoter

EVENT_TYPE_SUGGESTIONS = [
    "Concert",
    "Festival",
    "Fête locale",
    "Soirée privée",
    "Jeune public",
    "Scolaire",
    "Spectacle de rue",
    "Saison culturelle",
]
AESTHETIC_SUGGESTIONS = [
    "Chanson",
    "Jazz",
    "Rock",
    "Pop",
    "Musiques du monde",
    "Musique classique",
    "Électro",
    "Théâtre musical",
    "Jeune public",
]


def used_values(tenant, field):
    """Values already typed by this tenant for `field`, alphabetical, without duplicates."""
    values = Promoter.objects.filter(tenant=tenant).exclude(**{field: ""})
    seen = {}
    for value in values.values_list(field, flat=True):
        seen.setdefault(value.casefold(), value)
    return sorted(seen.values(), key=str.casefold)


def suggestions(tenant, field, fixed):
    """The proposed values followed by the tenant's own, ignoring case duplicates."""
    merged = {}
    for value in [*fixed, *used_values(tenant, field)]:
        merged.setdefault(value.casefold(), value)
    return sorted(merged.values(), key=str.casefold)
