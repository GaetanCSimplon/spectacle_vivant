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
]
