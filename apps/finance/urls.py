from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.FinanceView.as_view(), name="page"),
    path(
        "factures/<int:invoice_pk>/paiements/ajouter/",
        views.PaymentAddView.as_view(),
        name="payment-add",
    ),
    path("paiements/<int:pk>/modifier/", views.PaymentEditView.as_view(), name="payment-edit"),
    path("paiements/<int:pk>/supprimer/", views.PaymentDeleteView.as_view(), name="payment-delete"),
    path("depenses/ajouter/", views.ExpenseAddView.as_view(), name="expense-add"),
    path("depenses/<int:pk>/modifier/", views.ExpenseEditView.as_view(), name="expense-edit"),
    path("depenses/<int:pk>/supprimer/", views.ExpenseDeleteView.as_view(), name="expense-delete"),
    path(
        "depenses/<int:pk>/justificatif/",
        views.ExpenseReceiptView.as_view(),
        name="expense-receipt",
    ),
]
