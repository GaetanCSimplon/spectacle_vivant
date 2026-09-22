import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_pdf_test_view_requires_login(client):
    response = client.get(reverse("pdf-test"))

    assert response.status_code == 302


def test_pdf_test_view_returns_a_pdf(client):
    client.force_login(UserFactory())

    response = client.get(reverse("pdf-test"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
