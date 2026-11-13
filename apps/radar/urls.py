from django.urls import path

from . import views

app_name = "radar"

urlpatterns = [
    path("", views.RadarView.as_view(), name="radar"),
]
