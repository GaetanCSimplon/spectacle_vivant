"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from apps.addressbook import public_views as addressbook_public_views
from apps.core.views import HelloPdfView, HomeView, apple_touch_icon, favicon
from apps.finance import views as finance_views
from apps.roadmaps import views as roadmap_views
from apps.tenants.views import OnboardingView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("pdf-test/", HelloPdfView.as_view(), name="pdf-test"),
    path("favicon.ico", favicon, name="favicon"),
    path("apple-touch-icon.png", apple_touch_icon, name="apple-touch-icon"),
    path("bienvenue/", OnboardingView.as_view(), name="tenants-onboarding"),
    path("infos/", include("apps.core.urls")),
    path("bord/", include("apps.tenants.urls")),
    path("", include("apps.addressbook.urls")),
    path("spectacles/", include("apps.catalog.urls")),
    path("dates/", include("apps.gigs.urls")),
    path("dates/<int:gig_id>/feuille-de-route/", include("apps.roadmaps.urls")),
    path("dates/<int:gig_id>/finances/", include("apps.finance.urls")),
    path("dates/<int:gig_id>/", include("apps.documents.urls")),
    path(
        "feuille-de-route/<str:token>/",
        roadmap_views.PublicRoadmapView.as_view(),
        name="roadmap-public",
    ),
    path(
        "feuille-de-route/<str:token>/pdf/",
        roadmap_views.PublicRoadmapPdfView.as_view(),
        name="roadmap-public-pdf",
    ),
    path(
        "formulaire-organisateur/merci/",
        addressbook_public_views.PublicPromoterFormThanksView.as_view(),
        name="promoter-form-thanks",
    ),
    path(
        "formulaire-organisateur/<str:token>/",
        addressbook_public_views.PublicPromoterFormView.as_view(),
        name="promoter-form-public",
    ),
    path("exports/", finance_views.ExportView.as_view(), name="export"),
    path("exports/<str:kind>.csv", finance_views.ExportCsvView.as_view(), name="export-csv"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
]

# No /media/ route, even in dev: uploaded and generated files (contracts, tech sheets...)
# are only sent by views that check the tenant.
