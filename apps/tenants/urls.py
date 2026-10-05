from django.urls import path

from . import views

app_name = "tenants"

urlpatterns = [
    path("", views.TenantProfileView.as_view(), name="profile"),
    path("export-donnees/", views.DataExportView.as_view(), name="data-export"),
]
