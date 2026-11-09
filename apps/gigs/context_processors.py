from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models import Gig

DATE_NAMESPACES = {"gigs", "documents", "roadmaps", "finance"}
VOLETS = (
    ("contrats", _("Contrats")),
    ("budget", _("Budget")),
    ("social", _("Social")),
    ("regie", _("Régie")),
)


def _current_volet(match):
    """Which volet the page being shown belongs to (None on the date page itself)."""
    if match.namespace == "finance":
        return "budget"
    if match.namespace == "roadmaps":
        return "regie"
    if match.namespace == "documents":
        return "contrats" if match.url_name.startswith("contract") else "budget"
    if match.namespace == "gigs" and ("team" in match.url_name or "member" in match.url_name):
        return "social"
    return None


def gig_navigation(request):
    """The menu of a date, shown in the navigation while a date (or one of its pages) is open.

    The gig is read with the tenant filter: another tenant's date gives no menu at all.
    """
    match = getattr(request, "resolver_match", None)
    tenant = getattr(request, "tenant", None)
    if match is None or tenant is None or match.namespace not in DATE_NAMESPACES:
        return {}
    gig_id = match.kwargs.get("gig_id") or (
        match.kwargs.get("pk") if match.namespace == "gigs" else None
    )
    if gig_id is None or not request.user.is_authenticated:
        return {}
    gig = Gig.objects.filter(pk=gig_id, tenant=tenant).select_related("show").first()
    if gig is None:
        return {}
    detail = reverse("gigs:detail", args=[gig.pk])
    current = _current_volet(match)
    return {
        "gig_nav": {
            "gig": gig,
            "volets": [
                {
                    "key": key,
                    "label": label,
                    "url": f"{detail}#volet-{key}",
                    "active": key == current,
                }
                for key, label in VOLETS
            ],
        }
    }
