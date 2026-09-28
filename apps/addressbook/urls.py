from django.urls import path

from . import views

app_name = "addressbook"

urlpatterns = [
    path("organisateurs/", views.PromoterListView.as_view(), name="promoter-list"),
    path("organisateurs/nouveau/", views.PromoterCreateView.as_view(), name="promoter-create"),
    path("organisateurs/<int:pk>/", views.PromoterDetailView.as_view(), name="promoter-detail"),
    path(
        "organisateurs/<int:pk>/modifier/",
        views.PromoterUpdateView.as_view(),
        name="promoter-update",
    ),
    path(
        "organisateurs/<int:pk>/supprimer/",
        views.PromoterDeleteView.as_view(),
        name="promoter-delete",
    ),
    path("lieux/", views.VenueListView.as_view(), name="venue-list"),
    path("lieux/nouveau/", views.VenueCreateView.as_view(), name="venue-create"),
    path("lieux/<int:pk>/", views.VenueDetailView.as_view(), name="venue-detail"),
    path("lieux/<int:pk>/modifier/", views.VenueUpdateView.as_view(), name="venue-update"),
    path("lieux/<int:pk>/supprimer/", views.VenueDeleteView.as_view(), name="venue-delete"),
]
