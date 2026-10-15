from django.urls import path

from . import views

app_name = "tenants"

urlpatterns = [
    path("", views.BordView.as_view(), name="profile"),
    path("informations/", views.TenantSettingsView.as_view(), name="settings"),
    path("supprimer/", views.DeleteTenantView.as_view(), name="delete"),
    path("annuler-suppression/", views.CancelDeletionView.as_view(), name="cancel-deletion"),
    path("quitter/", views.LeaveTenantView.as_view(), name="leave"),
    path("equipe/", views.PersonListView.as_view(), name="person-list"),
    path("equipe/nouveau/", views.PersonCreateView.as_view(), name="person-create"),
    path("equipe/<int:pk>/", views.PersonDetailView.as_view(), name="person-detail"),
    path("equipe/<int:pk>/modifier/", views.PersonUpdateView.as_view(), name="person-update"),
    path("equipe/<int:pk>/supprimer/", views.PersonDeleteView.as_view(), name="person-delete"),
    path("export-donnees/", views.DataExportView.as_view(), name="data-export"),
]
