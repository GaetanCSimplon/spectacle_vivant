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
from django.contrib.sitemaps.views import sitemap as sitemap_view
from django.urls import include, path

from apps.addressbook import info_public_views
from apps.addressbook import public_views as addressbook_public_views
from apps.core.lookup_views import CommuneSearchView, CompanySearchView
from apps.core.sitemaps import SitePagesSitemap
from apps.core.views import (
    ContactThanksView,
    ContactView,
    FeaturesView,
    apple_touch_icon,
    favicon,
    home,
    robots_txt,
)
from apps.documents import public_views as documents_public_views
from apps.documents.views import DocumentLibraryView
from apps.finance import team_views as finance_team_views
from apps.finance import views as finance_views
from apps.roadmaps import public_views as roadmap_public_views
from apps.roadmaps import views as roadmap_views
from apps.tenants import public_views as tenants_public_views
from apps.tenants.views import OnboardingView

urlpatterns = [
    path("", home, name="home"),
    path("fonctionnalites/", FeaturesView.as_view(), name="site-features"),
    path("contact/", ContactView.as_view(), name="site-contact"),
    path("contact/merci/", ContactThanksView.as_view(), name="site-contact-thanks"),
    path("robots.txt", robots_txt, name="robots"),
    path(
        "sitemap.xml",
        sitemap_view,
        {"sitemaps": {"site": SitePagesSitemap}},
        name="sitemap",
    ),
    path("favicon.ico", favicon, name="favicon"),
    path("apple-touch-icon.png", apple_touch_icon, name="apple-touch-icon"),
    path("bienvenue/", OnboardingView.as_view(), name="tenants-onboarding"),
    path("infos/", include("apps.core.urls")),
    path("recherche/entreprises/", CompanySearchView.as_view(), name="lookup-companies"),
    path("recherche/communes/", CommuneSearchView.as_view(), name="lookup-communes"),
    path("bord/", include("apps.tenants.urls")),
    path("", include("apps.addressbook.urls")),
    path("radar/", include("apps.radar.urls")),
    path("spectacles/", include("apps.catalog.urls")),
    path("documents/", DocumentLibraryView.as_view(), name="document-library"),
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
    path("equipe/<str:token>/", tenants_public_views.TeamSpaceView.as_view(), name="team-space"),
    path(
        "equipe/<str:token>/dates/<int:gig_id>/",
        tenants_public_views.TeamSpaceGigView.as_view(),
        name="team-space-gig",
    ),
    path(
        "equipe/<str:token>/dates/<int:gig_id>/pdf/",
        tenants_public_views.TeamSpacePdfView.as_view(),
        name="team-space-pdf",
    ),
    path(
        "equipe/<str:token>/dates/<int:gig_id>/contrat/",
        tenants_public_views.TeamSpaceContractView.as_view(),
        name="team-space-contract",
    ),
    path(
        "equipe/<str:token>/dates/<int:gig_id>/documents/<int:pk>/",
        tenants_public_views.TeamSpaceDocumentView.as_view(),
        name="team-space-document",
    ),
    path(
        "equipe/<str:token>/depenses/",
        finance_team_views.TeamExpensesView.as_view(),
        name="team-expenses",
    ),
    path(
        "equipe/<str:token>/depenses/<int:pk>/modifier/",
        finance_team_views.TeamExpenseEditView.as_view(),
        name="team-expense-edit",
    ),
    path(
        "equipe/<str:token>/depenses/<int:pk>/supprimer/",
        finance_team_views.TeamExpenseDeleteView.as_view(),
        name="team-expense-delete",
    ),
    path(
        "equipe/<str:token>/depenses/<int:pk>/justificatif/",
        finance_team_views.TeamExpenseReceiptView.as_view(),
        name="team-expense-receipt",
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
    path(
        "mes-informations/<str:token>/",
        info_public_views.PublicInfoFormView.as_view(),
        name="info-form-public",
    ),
    path(
        "contrat-partage/<str:token>/",
        documents_public_views.PublicContractDownloadView.as_view(),
        name="contract-share-public",
    ),
    path(
        "regie-de-tournee/merci/",
        roadmap_public_views.PublicTourFormThanksView.as_view(),
        name="tour-form-thanks",
    ),
    path(
        "regie-de-tournee/<str:token>/",
        roadmap_public_views.PublicTourFormView.as_view(),
        name="tour-form-public",
    ),
    path("exports/", finance_views.ExportView.as_view(), name="export"),
    path("exports/<str:kind>.csv", finance_views.ExportCsvView.as_view(), name="export-csv"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
]

# No /media/ route, even in dev: uploaded and generated files (contracts, tech sheets...)
# are only sent by views that check the tenant.
