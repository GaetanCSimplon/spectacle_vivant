class OrganizationMiddleware:
    """Attach the current tenant to the request as `request.organization`.

    For now a user belongs to a single Organization in practice, so we take
    the first Membership. A real organization switcher can be added later
    if users start belonging to several organizations.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        if request.user.is_authenticated:
            membership = (
                request.user.memberships.select_related("organization").order_by("id").first()
            )
            if membership:
                request.organization = membership.organization

        return self.get_response(request)
