"""The exports must be easy to find: home card, "Ma structure", and each other."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from .helpers import make_gig

pytestmark = pytest.mark.django_db

CSV_PAGE = "export"
ZIP_PAGE = "tenants:data-export"


def _login(client, role="owner"):
    membership = MembershipFactory(role=role)
    client.force_login(membership.user)
    return membership.tenant


def test_home_shows_the_export_link_without_opening_the_detail(client):
    tenant = _login(client)
    make_gig(tenant=tenant)

    html = client.get(reverse("home")).content.decode()

    card = html.split('aria-labelledby="balance-title"')[1].split("</section>")[0]
    link = reverse(CSV_PAGE)
    assert link in card
    assert card.index(link) > card.index("</details>")  # outside the folded detail
    assert html.count(f'href="{link}"') == 1


@pytest.mark.parametrize("role", ["owner", "member"])
def test_ma_structure_links_to_both_exports(client, role):
    _login(client, role)

    html = client.get(reverse("tenants:profile")).content.decode()

    assert f'href="{reverse(CSV_PAGE)}"' in html
    assert f'href="{reverse(ZIP_PAGE)}"' in html
    assert "Exporter mes chiffres (CSV)" in html
    assert "Télécharger toutes mes données (ZIP)" in html


def test_the_csv_export_page_points_to_the_full_data_download(client):
    _login(client)

    html = client.get(reverse(CSV_PAGE)).content.decode()

    assert f'href="{reverse(ZIP_PAGE)}"' in html


def test_the_linked_pages_open_for_a_member(client):
    _login(client, "member")

    assert client.get(reverse(CSV_PAGE)).status_code == 200
    assert client.get(reverse(ZIP_PAGE)).status_code == 200
