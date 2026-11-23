from django.urls import reverse

from apps.accounts.services import is_tenant_owner

# Which of the five menu entries a page belongs to (R7): one entry active per page, or none.
DATE_NAMESPACES = {"gigs", "documents", "roadmaps", "finance"}
BORD_VIEWS = {"tenants:profile", "tenants:bord-status", "bord-expenses", "document-library"}


def active_menu(request):
    match = getattr(request, "resolver_match", None)
    if match is None:
        return {}
    view, namespace = match.view_name, match.namespace
    if view == "home":
        menu = "home"
    elif view in BORD_VIEWS or view in {"export", "export-csv"}:
        menu = "bord"
    elif view.startswith("tenants:social"):
        menu = "social"
    elif namespace in DATE_NAMESPACES:
        menu = "dates"
    elif namespace == "addressbook":
        menu = "contacts"
    else:  # Ma structure, Radar, account pages: no entry of the five
        menu = ""
    return {"active_menu": menu}


def structure_link(request):
    """Where "Ma structure" leads: the owner's first tab, or the team for a member (NAV-D4)."""
    tenant = getattr(request, "tenant", None)
    if tenant is None or not request.user.is_authenticated:
        return {}
    owner = is_tenant_owner(request.user, tenant)
    return {
        "structure_is_owner": owner,
        "structure_url": reverse("tenants:settings" if owner else "tenants:person-list"),
    }
