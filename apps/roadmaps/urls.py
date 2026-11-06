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


class PlaceConverter:
    """A section whose items can carry contacts."""

    regex = "hebergements|repas"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(SectionConverter, "section")
register_converter(PlaceConverter, "place")
register_converter(ShareActionConverter, "shareaction")

urlpatterns = [
    path("", views.EditorView.as_view(), name="editor"),
    path("pdf/", views.PdfView.as_view(), name="pdf"),
    path("apercu/", views.PreviewView.as_view(), name="preview"),
    path("notes/", views.NotesView.as_view(), name="notes"),
    path("partage/<shareaction:action>/", views.ShareView.as_view(), name="share"),
    path(
        "regie-de-tournee/creer/",
        views.TourRequestCreateView.as_view(),
        name="tour-request-create",
    ),
    path(
        "regie-de-tournee/annuler/",
        views.TourRequestRevokeView.as_view(),
        name="tour-request-revoke",
    ),
    path(
        "regie-de-tournee/verifier/",
        views.TourRequestReviewView.as_view(),
        name="tour-request-review",
    ),
    path("equipe/depuis-mon-equipe/", views.TeamMemberAddView.as_view(), name="team-add"),
    path(
        "<place:section>/<int:pk>/contacts/ajouter/",
        views.PlaceContactAddView.as_view(),
        name="contact-add",
    ),
    path(
        "<place:section>/<int:pk>/contacts/<int:contact_pk>/supprimer/",
        views.PlaceContactDeleteView.as_view(),
        name="contact-delete",
    ),
    path("<section:section>/ajouter/", views.ItemAddView.as_view(), name="item-add"),
    path("<section:section>/<int:pk>/modifier/", views.ItemEditView.as_view(), name="item-edit"),
    path(
        "<section:section>/<int:pk>/supprimer/",
        views.ItemDeleteView.as_view(),
        name="item-delete",
    ),
]
