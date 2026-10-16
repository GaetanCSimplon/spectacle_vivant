from django.urls import path

from . import views

app_name = "gigs"

urlpatterns = [
    path("", views.GigListView.as_view(), name="list"),
    path("nouvelle/spectacle/", views.GigWizardShowStepView.as_view(), name="wizard-show"),
    path(
        "nouvelle/organisateur/",
        views.GigWizardPromoterStepView.as_view(),
        name="wizard-promoter",
    ),
    path("nouvelle/lieu/", views.GigWizardVenueStepView.as_view(), name="wizard-venue"),
    path("nouvelle/details/", views.GigWizardDetailsStepView.as_view(), name="wizard-details"),
    path("nouvelle/recapitulatif/", views.GigWizardRecapView.as_view(), name="wizard-recap"),
    path("calendrier/", views.GigCalendarView.as_view(), name="calendar"),
    path("<int:pk>/", views.GigDetailView.as_view(), name="detail"),
    path("<int:pk>/checklist/", views.GigChecklistView.as_view(), name="checklist"),
    path("<int:pk>/checklist/case/", views.GigChecklistItemView.as_view(), name="checklist-item"),
    path(
        "<int:pk>/checklist/reinitialiser/",
        views.GigChecklistResetView.as_view(),
        name="checklist-reset",
    ),
    path("<int:pk>/prix/", views.GigPriceView.as_view(), name="price"),
    path("<int:pk>/echeances/", views.GigTermsView.as_view(), name="terms"),
    path("<int:pk>/confirmer/", views.GigConfirmView.as_view(), name="confirm"),
    path("<int:pk>/annuler/", views.GigCancelView.as_view(), name="cancel"),
    path("<int:pk>/supprimer/", views.GigDeleteView.as_view(), name="delete"),
    path("<int:pk>/reactiver/", views.GigReactivateView.as_view(), name="reactivate"),
]
