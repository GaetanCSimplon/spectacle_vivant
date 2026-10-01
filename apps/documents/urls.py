from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("completer/", views.ContractCompleteView.as_view(), name="contract-complete"),
    path("apercu/", views.ContractPreviewView.as_view(), name="contract-preview"),
    path("versions/", views.ContractHistoryView.as_view(), name="contract-history"),
    path("signer/", views.ContractSignView.as_view(), name="contract-sign"),
    path("pdf-signe/", views.ContractSignedPdfView.as_view(), name="contract-signed-pdf"),
    path("generer/", views.ContractGenerateView.as_view(), name="contract-generate"),
    path("telecharger/", views.ContractDownloadView.as_view(), name="contract-download"),
    path(
        "versions/<int:number>/",
        views.ContractDownloadView.as_view(),
        name="contract-version-download",
    ),
]
