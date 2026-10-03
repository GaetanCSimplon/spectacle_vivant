from django.urls import path, register_converter

from . import views

app_name = "roadmaps"


class SectionConverter:
    """A section of the editor in a URL."""

    regex = "creneaux|hebergements|repas|equipe"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


class ShareActionConverter:
    regex = "activer|arreter"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(SectionConverter, "section")
register_converter(ShareActionConverter, "shareaction")

urlpatterns = [
    path("", views.EditorView.as_view(), name="editor"),
    path("notes/", views.NotesView.as_view(), name="notes"),
    path("partage/<shareaction:action>/", views.ShareView.as_view(), name="share"),
    path("<section:section>/ajouter/", views.ItemAddView.as_view(), name="item-add"),
    path("<section:section>/<int:pk>/modifier/", views.ItemEditView.as_view(), name="item-edit"),
    path(
        "<section:section>/<int:pk>/supprimer/",
        views.ItemDeleteView.as_view(),
        name="item-delete",
    ),
]
