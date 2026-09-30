from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("completer/", views.ContractCompleteView.as_view(), name="contract-complete"),
    path("apercu/", views.ContractPreviewView.as_view(), name="contract-preview"),
    path("telecharger/", views.ContractDownloadView.as_view(), name="contract-download"),
]
