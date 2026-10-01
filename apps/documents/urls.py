from django.urls import path, register_converter

from . import billing_views, views

app_name = "documents"


class DocTypeConverter:
    """`factures` or `devis` in a URL."""

    regex = "factures|devis"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(DocTypeConverter, "doctype")

urlpatterns = [
    path("contrat/completer/", views.ContractCompleteView.as_view(), name="contract-complete"),
    path("contrat/apercu/", views.ContractPreviewView.as_view(), name="contract-preview"),
    path("contrat/versions/", views.ContractHistoryView.as_view(), name="contract-history"),
    path("contrat/signer/", views.ContractSignView.as_view(), name="contract-sign"),
    path("contrat/pdf-signe/", views.ContractSignedPdfView.as_view(), name="contract-signed-pdf"),
    path("contrat/generer/", views.ContractGenerateView.as_view(), name="contract-generate"),
    path("contrat/telecharger/", views.ContractDownloadView.as_view(), name="contract-download"),
    path(
        "contrat/versions/<int:number>/",
        views.ContractDownloadView.as_view(),
        name="contract-version-download",
    ),
    path("facturation/", billing_views.BillingView.as_view(), name="billing"),
    path("devis/nouveau/", billing_views.CreateDocumentView.as_view(), name="quote-create"),
    path(
        "factures/nouvelle/<str:kind>/",
        billing_views.CreateDocumentView.as_view(),
        name="invoice-create",
    ),
    path(
        "<doctype:doc_type>/<int:pk>/",
        billing_views.DocumentDetailView.as_view(),
        name="document-detail",
    ),
    path(
        "<doctype:doc_type>/<int:pk>/lignes/ajouter/",
        billing_views.LineAddView.as_view(),
        name="line-add",
    ),
    path(
        "<doctype:doc_type>/<int:pk>/lignes/<int:line_pk>/modifier/",
        billing_views.LineEditView.as_view(),
        name="line-edit",
    ),
    path(
        "<doctype:doc_type>/<int:pk>/lignes/<int:line_pk>/supprimer/",
        billing_views.LineRemoveView.as_view(),
        name="line-remove",
    ),
    path(
        "<doctype:doc_type>/<int:pk>/pdf/",
        billing_views.DocumentPdfView.as_view(),
        name="document-pdf",
    ),
    path(
        "<doctype:doc_type>/<int:pk>/emettre/",
        billing_views.DocumentIssueView.as_view(),
        name="document-issue",
    ),
    path(
        "<doctype:doc_type>/<int:pk>/supprimer/",
        billing_views.DocumentDeleteView.as_view(),
        name="document-delete",
    ),
    path(
        "factures/<int:pk>/avoir/",
        billing_views.CreditNoteView.as_view(),
        name="credit-note-create",
    ),
]
