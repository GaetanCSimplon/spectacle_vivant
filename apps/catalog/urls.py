from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.ShowListView.as_view(), name="show-list"),
    path("nouveau/", views.ShowCreateView.as_view(), name="show-create"),
    path("<int:pk>/", views.ShowDetailView.as_view(), name="show-detail"),
    path("<int:pk>/modifier/", views.ShowUpdateView.as_view(), name="show-update"),
    path("<int:pk>/supprimer/", views.ShowDeleteView.as_view(), name="show-delete"),
    path("<int:pk>/fichier/<slug:kind>/", views.ShowFileView.as_view(), name="show-file"),
]
