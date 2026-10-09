"""Qualification of organisers (F-15): follow-up label, event type, aesthetic, filters."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from .. import services
from ..factories import PromoterFactory
from ..models import Promoter

pytestmark = pytest.mark.django_db

LIST = "addressbook:promoter-list"
HTMX = {"HTTP_HX_REQUEST": "true"}


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _names(response):
    return [p.name for p in response.context["object_list"]]


@pytest.fixture
def three(client):
    tenant = _login(client)
    PromoterFactory(
        tenant=tenant,
        name="Mairie A",
        follow_up="negotiating",
        event_type="Festival",
        aesthetic="Jazz",
    )
    PromoterFactory(
        tenant=tenant, name="Salle B", follow_up="active", event_type="Concert", aesthetic="Rock"
    )
    PromoterFactory(tenant=tenant, name="Bar C")
    return tenant


# --- the fields ---------------------------------------------------------------------


def test_qualification_is_optional_and_saved_from_the_form(client):
    tenant = _login(client)

    response = client.post(
        reverse("addressbook:promoter-create"),
        {
            "name": "Mairie",
            "follow_up": "signing",
            "event_type": "  Fête   locale ",
            "aesthetic": "Chanson",
        },
    )

    assert response.status_code == 302
    promoter = Promoter.objects.get(tenant=tenant)
    assert (promoter.follow_up, promoter.event_type, promoter.aesthetic) == (
        "signing",
        "Fête locale",
        "Chanson",
    )
    client.post(reverse("addressbook:promoter-create"), {"name": "Nu"})
    assert Promoter.objects.get(name="Nu").follow_up == ""


def test_an_unknown_follow_up_is_refused(client):
    _login(client)
    response = client.post(
        reverse("addressbook:promoter-create"), {"name": "X", "follow_up": "hacked"}
    )
    assert response.status_code == 200
    assert not Promoter.objects.filter(name="X").exists()


def test_detail_and_list_show_the_qualification(client, three):
    promoter = Promoter.objects.get(name="Mairie A")

    detail = client.get(reverse("addressbook:promoter-detail", args=[promoter.pk])).content.decode()
    listing = client.get(reverse(LIST)).content.decode()

    for content in (detail, listing):
        assert "En négociation" in content
        assert "Festival" in content or "Jazz" in content


def test_the_form_proposes_fixed_values_plus_the_tenants_own(client):
    tenant = _login(client)
    PromoterFactory(tenant=tenant, event_type="Marché de Noël", aesthetic="jazz")
    PromoterFactory(event_type="Valeur d'un autre tenant")

    content = client.get(reverse("addressbook:promoter-create")).content.decode()

    assert "Marché de Noël" in content
    assert "Concert" in content
    assert "Valeur d&#x27;un autre tenant" not in content and "Valeur d'un autre" not in content
    assert services.suggestions(tenant, "aesthetic", ["Jazz"]) == ["Jazz"]  # no case duplicate


# --- filters ------------------------------------------------------------------------


def test_each_filter_narrows_the_list(client, three):
    assert _names(client.get(reverse(LIST), {"follow_up": "active"})) == ["Salle B"]
    assert _names(client.get(reverse(LIST), {"event_type": "Festival"})) == ["Mairie A"]
    assert _names(client.get(reverse(LIST), {"aesthetic": "Rock"})) == ["Salle B"]


def test_filters_combine_with_each_other_and_with_the_search(client, three):
    assert _names(client.get(reverse(LIST), {"follow_up": "active", "aesthetic": "Jazz"})) == []
    assert _names(client.get(reverse(LIST), {"q": "salle", "follow_up": "active"})) == ["Salle B"]
    assert _names(client.get(reverse(LIST), {"q": "mairie", "follow_up": "active"})) == []


def test_an_invalid_filter_value_is_ignored(client, three):
    response = client.get(reverse(LIST), {"follow_up": "nope", "event_type": "Inconnu"})
    assert sorted(_names(response)) == ["Bar C", "Mairie A", "Salle B"]


def test_filtering_is_live_with_htmx_and_an_empty_result_is_explained(client, three):
    response = client.get(reverse(LIST), {"follow_up": "dropped"}, **HTMX)
    content = response.content.decode()
    assert "<html" not in content
    assert "Aucun organisateur ne correspond" in content


def test_filters_never_offer_or_match_another_tenants_values(client, three):
    PromoterFactory(name="Autre", follow_up="active", event_type="Secret", aesthetic="Secret")

    response = client.get(reverse(LIST), {"event_type": "Secret", "follow_up": "active"})

    assert "Secret" not in response.content.decode()
    assert "Autre" not in _names(client.get(reverse(LIST), {"follow_up": "active"}))
