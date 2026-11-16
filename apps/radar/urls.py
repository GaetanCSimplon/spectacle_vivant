from django.urls import path

from . import views

app_name = "radar"

urlpatterns = [
    path("", views.RadarView.as_view(), name="radar"),
    path("bouton/", views.RadarButtonView.as_view(), name="button"),
    path("fenetre/", views.RadarPanelView.as_view(), name="panel"),
]
