from django.conf import settings
from django.shortcuts import redirect


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


class OnboardingRequiredMiddleware:
    """Send a logged-in user with no Tenant yet to the onboarding screen.

    Must run after TenantMiddleware, which sets `request.tenant`. Only acts
    on GET requests, so tenant-scoped views (TenantScopedMixin) keep
    rejecting POST/other writes with a 404, as before. Exempts admin,
    allauth (login, logout, e-mail confirmation...), the public roadmap link, the legal
    pages, static/media files, and the onboarding screen itself, to avoid redirect loops.
    """

    ONBOARDING_PATH = "/bienvenue/"
    EXEMPT_PREFIXES = (
        "/admin/",
        "/accounts/",
        "/infos/",  # legal pages: public
        "/feuille-de-route/",  # public roadmap link: it needs no account nor tenant
        settings.STATIC_URL,
        settings.MEDIA_URL,
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.method == "GET"
            and request.user.is_authenticated
            and request.tenant is None
            and request.path != self.ONBOARDING_PATH
            and not request.path.startswith(self.EXEMPT_PREFIXES)
        ):
            return redirect(self.ONBOARDING_PATH)
        return self.get_response(request)
