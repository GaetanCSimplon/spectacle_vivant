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
]
