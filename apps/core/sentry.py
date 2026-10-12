"""Cleaning of what is sent to Sentry: the secret links (roadmap, organiser form) never leave."""

import re

# /feuille-de-route/<token>/ (and /pdf/) and /formulaire-organisateur/<token>/, also inside a
# full URL: the token is the whole access right to the page.
ROADMAP_TOKEN = re.compile(r"(/(?:feuille-de-route|formulaire-organisateur)/)[^/?#\s\"']+")
MASK = "[masque]"


def _scrub(value):
    if isinstance(value, str):
        return ROADMAP_TOKEN.sub(rf"\1{MASK}", value)
    if isinstance(value, dict):
        return {key: _scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


def scrub_event(event, hint=None):
    """`before_send` / `before_breadcrumb` hook: hide the roadmap token everywhere."""
    return _scrub(event)
