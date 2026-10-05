from django.urls import path
from django.views.generic import TemplateView

# Public pages: no login, no tenant (see OnboardingRequiredMiddleware.EXEMPT_PREFIXES).
urlpatterns = [
    path(
        "mentions-legales/",
        TemplateView.as_view(template_name="legal/mentions.html"),
        name="legal-notice",
    ),
    path("cgu/", TemplateView.as_view(template_name="legal/terms.html"), name="legal-terms"),
    path(
        "confidentialite/",
        TemplateView.as_view(template_name="legal/privacy.html"),
        name="legal-privacy",
    ),
]
