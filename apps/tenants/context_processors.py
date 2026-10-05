from .services import deletion_date


def pending_deletion(request):
    """The purge day of the current tenant, for the banner shown on every page."""
    tenant = getattr(request, "tenant", None)
    return {"pending_deletion_date": deletion_date(tenant) if tenant else None}
