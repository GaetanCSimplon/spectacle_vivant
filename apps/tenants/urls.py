from django.urls import path

from . import views

app_name = "tenants"

urlpatterns = [
    path("", views.BordView.as_view(), name="profile"),
    path("dates/<int:pk>/statut/", views.BordStatusView.as_view(), name="bord-status"),
    path("informations/", views.TenantSettingsView.as_view(), name="settings"),
    path("supprimer/", views.DeleteTenantView.as_view(), name="delete"),
    path("annuler-suppression/", views.CancelDeletionView.as_view(), name="cancel-deletion"),
    path("quitter/", views.LeaveTenantView.as_view(), name="leave"),
    path("equipe/", views.PersonListView.as_view(), name="person-list"),
    path("equipe/nouveau/", views.PersonCreateView.as_view(), name="person-create"),
    path("equipe/<int:pk>/", views.PersonDetailView.as_view(), name="person-detail"),
    path("equipe/<int:pk>/modifier/", views.PersonUpdateView.as_view(), name="person-update"),
    path("equipe/<int:pk>/supprimer/", views.PersonDeleteView.as_view(), name="person-delete"),
    path(
        "equipe/<int:pk>/espace/creer/",
        views.PersonAccessView.as_view(action="enable"),
        name="person-access-enable",
    ),
    path(
        "equipe/<int:pk>/espace/revoquer/",
        views.PersonAccessView.as_view(action="revoke"),
        name="person-access-revoke",
    ),
    path("equipe/social/", views.SocialView.as_view(), name="social"),
    path("equipe/social/export/", views.SocialExportView.as_view(), name="social-export"),
    path("export-donnees/", views.DataExportView.as_view(), name="data-export"),
]
