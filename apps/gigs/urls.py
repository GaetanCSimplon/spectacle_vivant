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
    path("<int:pk>/confirmer/", views.GigConfirmView.as_view(), name="confirm"),
    path("<int:pk>/annuler/", views.GigCancelView.as_view(), name="cancel"),
    path("<int:pk>/reactiver/", views.GigReactivateView.as_view(), name="reactivate"),
]
