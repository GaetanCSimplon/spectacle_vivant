"""R8: a breadcrumb on every page of level 2 or more, none on the top-level pages."""

import pytest
from django.urls import reverse

from apps.addressbook.factories import ContactFactory, PromoterFactory, VenueFactory
from apps.catalog.factories import ShowFactory
from apps.finance.tests.helpers import TENANT_FIELDS, make_gig
from apps.tenants.factories import MembershipFactory, PersonFactory

pytestmark = pytest.mark.django_db

MARK = "Fil d&#x27;Ariane"


def _login(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    return membership.tenant


def _html(client, url):
    response = client.get(url, follow=True)
    assert response.status_code == 200, url
    return response.content.decode()


def _crumb(content):
    assert MARK in content or "Fil d'Ariane" in content
    return content.split('<nav aria-label="Fil d', 1)[1].split("</nav>", 1)[0]


def test_the_directory_pages_lead_back_to_the_right_list(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)
    contact = ContactFactory(tenant=tenant)
    directory = reverse("addressbook:directory")

    for url, kind, name in [
        (
            reverse("addressbook:promoter-detail", args=[promoter.pk]),
            "organisateurs",
            promoter.name,
        ),
        (
            reverse("addressbook:promoter-update", args=[promoter.pk]),
            "organisateurs",
            promoter.name,
        ),
        (reverse("addressbook:promoter-create"), "organisateurs", "Nouvel organisateur"),
        (reverse("addressbook:venue-detail", args=[venue.pk]), "lieux", venue.name),
        (reverse("addressbook:venue-delete", args=[venue.pk]), "lieux", venue.name),
        (reverse("addressbook:contact-update", args=[contact.pk]), "personnes", "Modifier"),
        (reverse("addressbook:contact-create"), "personnes", "Nouveau contact"),
        (reverse("addressbook:import"), None, "Importer"),
    ]:
        crumb = _crumb(_html(client, url))
        assert f'href="{directory}' + (f'?type={kind}"' if kind else '"') in crumb, url
        assert name in crumb, url


def test_the_pages_of_ma_structure_start_with_ma_structure(client):
    tenant = _login(client)
    person = PersonFactory(tenant=tenant)
    show = ShowFactory(tenant=tenant)
    root = reverse("tenants:settings")

    for url, middle in [
        (reverse("tenants:person-detail", args=[person.pk]), reverse("tenants:person-list")),
        (reverse("tenants:person-update", args=[person.pk]), reverse("tenants:person-list")),
        (reverse("catalog:show-detail", args=[show.pk]), reverse("catalog:show-list")),
        (
            reverse("catalog:show-update", args=[show.pk]),
            reverse("catalog:show-detail", args=[show.pk]),
        ),
        (reverse("catalog:show-create"), reverse("catalog:show-list")),
        (reverse("tenants:delete"), reverse("tenants:account")),
        (reverse("tenants:data-export"), reverse("tenants:account")),
    ]:
        crumb = _crumb(_html(client, url))
        assert f'href="{root}"' in crumb, url
        assert f'href="{middle}"' in crumb, url


def test_the_current_page_is_not_a_link(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant)

    crumb = _crumb(_html(client, reverse("addressbook:promoter-detail", args=[promoter.pk])))

    assert (
        f'aria-current="page" class="min-w-0 font-semibold text-gray-900">{promoter.name}' in crumb
    )
    assert crumb.count("<a ") == 1


def test_the_date_pages_start_with_mes_dates(client):
    tenant = _login(client)
    gig = make_gig(tenant=tenant)

    for url in (
        reverse("gigs:detail", args=[gig.pk]),
        reverse("roadmaps:editor", args=[gig.pk]),
        reverse("finance:page", args=[gig.pk]),
    ):
        crumb = _crumb(_html(client, url))
        assert f'href="{reverse("gigs:list")}"' in crumb, url


def test_social_history_and_export_have_a_breadcrumb(client):
    _login(client)

    assert f'href="{reverse("tenants:social")}"' in _crumb(
        _html(client, reverse("tenants:social-history"))
    )
    assert f'href="{reverse("tenants:profile")}"' in _crumb(_html(client, reverse("export")))


def test_top_level_pages_have_no_breadcrumb(client):
    _login(client)

    for url in (
        reverse("home"),
        reverse("gigs:list"),
        reverse("tenants:profile"),
        reverse("tenants:social"),
        reverse("addressbook:directory"),
        reverse("tenants:settings"),
        reverse("tenants:person-list"),
    ):
        content = _html(client, url)
        assert MARK not in content and "Fil d'Ariane" not in content, url
