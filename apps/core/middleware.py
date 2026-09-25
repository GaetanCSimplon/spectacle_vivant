class TenantMiddleware:
    """Attach the current tenant to the request as `request.tenant`.

    For now a user belongs to a single Tenant in practice, so we take
    the first Membership. A real tenant switcher can be added later
    if users start belonging to several tenants.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        if request.user.is_authenticated:
            membership = request.user.memberships.select_related("tenant").order_by("id").first()
            if membership:
                request.tenant = membership.tenant

        return self.get_response(request)
