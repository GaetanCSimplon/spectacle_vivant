import pytest
from django.http import JsonResponse
from django.urls import path, reverse
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.factories import UserFactory
from apps.core.models import Note
from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.core.views import TenantScopedMixin
from apps.organizations.factories import MembershipFactory

mark_isolation_tested(Note)

pytestmark = pytest.mark.django_db


class JsonInsteadOfTemplateMixin:
    """Skip template rendering: these views only exist to exercise TenantScopedMixin."""

    def render_to_response(self, context, **kwargs):
        return JsonResponse({"pks": [note.pk for note in context["object_list"]]})


class NoteListView(TenantScopedMixin, JsonInsteadOfTemplateMixin, ListView):
    model = Note


class NoteDetailView(TenantScopedMixin, DetailView):
    model = Note

    def render_to_response(self, context, **kwargs):
        return JsonResponse({"pk": context["object"].pk})


class NoteCreateView(TenantScopedMixin, CreateView):
    model = Note
    fields = ["text"]
    success_url = "/"


urlpatterns = [
    path("__test__/notes/", NoteListView.as_view(), name="test-note-list"),
    path("__test__/notes/new/", NoteCreateView.as_view(), name="test-note-create"),
    path("__test__/notes/<int:pk>/", NoteDetailView.as_view(), name="test-note-detail"),
]


@pytest.fixture
def urls(settings):
    settings.ROOT_URLCONF = __name__


@pytest.fixture
def membership_a():
    return MembershipFactory()


@pytest.fixture
def membership_b():
    return MembershipFactory()


def test_middleware_sets_current_organization(client, membership_a):
    client.force_login(membership_a.user)

    response = client.get("/admin/")

    assert response.wsgi_request.organization == membership_a.organization


def test_middleware_organization_is_none_without_membership(client):
    user = UserFactory()
    client.force_login(user)

    response = client.get("/admin/")

    assert response.wsgi_request.organization is None


def test_list_view_does_not_mix_organizations(client, urls, membership_a, membership_b):
    note_a = Note.objects.create(organization=membership_a.organization, text="Note A")
    Note.objects.create(organization=membership_b.organization, text="Note B")

    client.force_login(membership_a.user)
    response = client.get(reverse("test-note-list"))

    assert response.json()["pks"] == [note_a.pk]


def test_detail_of_another_organization_is_not_found(client, urls, membership_a, membership_b):
    note_b = Note.objects.create(organization=membership_b.organization, text="Note B")

    client.force_login(membership_a.user)
    response = client.get(reverse("test-note-detail", args=[note_b.pk]))

    assert response.status_code == 404


def test_detail_of_own_organization_is_found(client, urls, membership_a):
    note_a = Note.objects.create(organization=membership_a.organization, text="Note A")

    client.force_login(membership_a.user)
    response = client.get(reverse("test-note-detail", args=[note_a.pk]))

    assert response.status_code == 200


def test_create_view_forces_current_organization(client, urls, membership_a, membership_b):
    client.force_login(membership_a.user)

    client.post(reverse("test-note-create"), {"text": "Nouvelle note"})

    note = Note.objects.get(text="Nouvelle note")
    assert note.organization == membership_a.organization
    assert note.organization != membership_b.organization
