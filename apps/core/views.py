from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404


class TenantScopedMixin(LoginRequiredMixin):
    """Restrict a generic view to objects of the current organization.

    Requires `request.organization` (set by OrganizationMiddleware). Views
    using this mixin must never let the organization be chosen by the
    client: it is always taken from the request.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.organization is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(organization=self.request.organization)

    def form_valid(self, form):
        form.instance.organization = self.request.organization
        return super().form_valid(form)
