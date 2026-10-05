from django.urls import path

from . import views

app_name = "tenants"

urlpatterns = [
    path("", views.TenantProfileView.as_view(), name="profile"),
    path("supprimer/", views.DeleteTenantView.as_view(), name="delete"),
    path("annuler-suppression/", views.CancelDeletionView.as_view(), name="cancel-deletion"),
    path("quitter/", views.LeaveTenantView.as_view(), name="leave"),
    path("export-donnees/", views.DataExportView.as_view(), name="data-export"),
]
