"""Qualification of organisers (F-15): follow-up label, six multiple-choice criteria, filters."""

import pytest
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

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
    return sorted(p.name for p in response.context["object_list"])


@pytest.fixture
def three(client):
    tenant = _login(client)
    PromoterFactory(
        tenant=tenant,
        name="Mairie A",
        follow_up="negotiating",
        kinds=["municipality", "festival"],
        event_types=["festival", "municipal_event"],
        aesthetics=["jazz", "chanson"],
        formats=["open_air"],
        usual_periods=["festival_period"],
        event_roles=["organiser", "programmer"],
    )
    PromoterFactory(
        tenant=tenant,
        name="Salle B",
        follow_up="active",
        kinds=["venue"],
        event_types=["concert"],
        aesthetics=["contemporary_music"],
        formats=["seated", "small_capacity"],
        usual_periods=["season"],
        event_roles=["programmer"],
    )
    PromoterFactory(tenant=tenant, name="Bar C")
    return tenant


# --- the fields -------------------------------------------------------------------------


def test_the_six_criteria_are_optional_and_empty_by_default():
    promoter = PromoterFactory()
    promoter.refresh_from_db()

    assert promoter.kinds == promoter.event_types == promoter.aesthetics == []
    assert promoter.formats == promoter.usual_periods == promoter.event_roles == []
    assert promoter.indicative_capacity is None and promoter.qualification_other == ""


def test_several_values_can_be_ticked_for_each_criterion(client):
    tenant = _login(client)

    response = client.post(
        reverse("addressbook:promoter-create"),
        {
            "name": "Mairie",
            "follow_up": "signing",
            "kinds": ["municipality", "festival"],
            "event_types": ["concert", "festival", "cultural_season"],
            "aesthetics": ["jazz", "classical"],
            "formats": ["open_air", "standing"],
            "usual_periods": ["season", "one_off"],
            "event_roles": ["organiser", "co_producer"],
            "indicative_capacity": "800",
            "qualification_other": "Aime les trios",
        },
    )

    assert response.status_code == 302
    promoter = Promoter.objects.get(tenant=tenant)
    assert promoter.follow_up == "signing"
    assert promoter.kinds == ["festival", "municipality"]  # order of the list
    assert promoter.event_types == ["concert", "festival", "cultural_season"]
    assert promoter.aesthetics == ["jazz", "classical"]
    assert promoter.formats == ["open_air", "standing"]
    assert promoter.usual_periods == ["season", "one_off"]
    assert promoter.event_roles == ["organiser", "co_producer"]
    assert promoter.indicative_capacity == 800
    assert promoter.qualification_other == "Aime les trios"


def test_the_values_always_come_back_in_the_order_of_the_list(client):
    tenant = _login(client)

    client.post(
        reverse("addressbook:promoter-create"),
        {"name": "Mairie", "aesthetics": ["classical", "chanson", "jazz"]},
    )

    assert Promoter.objects.get(tenant=tenant).aesthetics == ["chanson", "jazz", "classical"]


def test_the_criteria_can_be_emptied_again(client):
    tenant = _login(client)
    promoter = PromoterFactory(tenant=tenant, kinds=["venue"], aesthetics=["jazz"])

    client.post(reverse("addressbook:promoter-update", args=[promoter.pk]), {"name": "Même"})

    promoter.refresh_from_db()
    assert promoter.kinds == [] and promoter.aesthetics == []


@pytest.mark.parametrize(
    "field", ["kinds", "event_types", "aesthetics", "formats", "usual_periods", "event_roles"]
)
def test_an_unknown_value_is_refused(client, field):
    _login(client)

    response = client.post(reverse("addressbook:promoter-create"), {"name": "X", field: ["piraté"]})

    assert response.status_code == 200
    assert not Promoter.objects.filter(name="X").exists()


def test_an_unknown_follow_up_is_refused(client):
    _login(client)
    response = client.post(
        reverse("addressbook:promoter-create"), {"name": "X", "follow_up": "hacked"}
    )
    assert response.status_code == 200
    assert not Promoter.objects.filter(name="X").exists()


def test_the_form_shows_every_choice_as_a_checkbox(client):
    _login(client)

    content = client.get(reverse("addressbook:promoter-create")).content.decode()

    for label in [
        "Établissement culturel",
        "Action culturelle",
        "Pluridisciplinaire",
        "Petite jauge",
        "Période de programmation connue",
        "Coproducteur",
    ]:
        assert label in content
    assert content.count('type="checkbox"') >= 40


def test_detail_and_list_show_the_qualification(client, three):
    promoter = Promoter.objects.get(name="Mairie A")

    detail = client.get(reverse("addressbook:promoter-detail", args=[promoter.pk])).content.decode()
    listing = client.get(reverse(LIST)).content.decode()

    assert "En négociation" in detail and "En négociation" in listing
    assert "Collectivité, Festival" in detail and "Collectivité, Festival" in listing
    assert "Type d&#x27;évènement : Festival, Évènement municipal" in detail
    assert "Jazz, Chanson" in listing or "Chanson, Jazz" in listing
    assert "Rôle dans l&#x27;évènement : Organisateur, Programmateur" in detail
    assert "Période habituelle : Période de festival" in detail


def test_the_detail_shows_the_indicative_capacity_and_the_other_details(client):
    tenant = _login(client)
    promoter = PromoterFactory(
        tenant=tenant, indicative_capacity=450, qualification_other="Scène couverte"
    )

    content = client.get(
        reverse("addressbook:promoter-detail", args=[promoter.pk])
    ).content.decode()

    assert "Jauge indicative : 450" in content
    assert "Autres précisions : Scène couverte" in content


# --- filters ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("param", "value", "expected"),
    [
        ("follow_up", "active", ["Salle B"]),
        ("kind", "festival", ["Mairie A"]),
        ("kind", "municipality", ["Mairie A"]),
        ("kind", "venue", ["Salle B"]),
        ("event_type", "municipal_event", ["Mairie A"]),
        ("event_type", "concert", ["Salle B"]),
        ("aesthetic", "chanson", ["Mairie A"]),
        ("aesthetic", "contemporary_music", ["Salle B"]),
        ("format", "small_capacity", ["Salle B"]),
        ("format", "open_air", ["Mairie A"]),
        ("period", "season", ["Salle B"]),
        ("role", "programmer", ["Mairie A", "Salle B"]),
        ("role", "organiser", ["Mairie A"]),
    ],
)
def test_each_filter_matches_organisers_having_the_value_among_several(
    client, three, param, value, expected
):
    assert _names(client.get(reverse(LIST), {param: value})) == expected


def test_filters_combine_with_each_other_and_with_the_search(client, three):
    assert _names(client.get(reverse(LIST), {"role": "programmer", "format": "seated"})) == [
        "Salle B"
    ]
    assert _names(client.get(reverse(LIST), {"follow_up": "active", "aesthetic": "jazz"})) == []
    assert _names(client.get(reverse(LIST), {"q": "salle", "follow_up": "active"})) == ["Salle B"]
    assert _names(client.get(reverse(LIST), {"q": "mairie", "follow_up": "active"})) == []


def test_an_invalid_filter_value_is_ignored(client, three):
    response = client.get(reverse(LIST), {"follow_up": "nope", "event_type": "Inconnu"})

    assert _names(response) == ["Bar C", "Mairie A", "Salle B"]


def test_filtering_is_live_with_htmx_and_an_empty_result_is_explained(client, three):
    response = client.get(reverse(LIST), {"follow_up": "dropped"}, **HTMX)
    content = response.content.decode()

    assert "<html" not in content
    assert "Aucun organisateur ne correspond" in content


def test_the_filters_never_match_another_tenants_organisers(client, three):
    PromoterFactory(name="Autre", follow_up="active", kinds=["venue"], aesthetics=["jazz"])

    assert "Autre" not in _names(client.get(reverse(LIST), {"kind": "venue"}))
    assert "Autre" not in _names(client.get(reverse(LIST), {"aesthetic": "jazz"}))


def test_every_filter_is_offered_on_the_list_page(client, three):
    content = client.get(reverse(LIST)).content.decode()

    for name in ("follow_up", "kind", "event_type", "aesthetic", "format", "period", "role"):
        assert f'name="{name}"' in content


# --- the venue configuration ------------------------------------------------------------


def test_the_venue_configuration_is_saved_and_shown(client):
    tenant = _login(client)

    client.post(
        reverse("addressbook:venue-create"), {"name": "Salle des fêtes", "configuration": "Debout"}
    )

    venue = tenant.venue_set.get()
    assert venue.configuration == "Debout"
    page = client.get(reverse("addressbook:venue-detail", args=[venue.pk])).content.decode()
    assert "Configuration : Debout" in page


def test_the_completion_form_sets_the_venue_configuration_and_model_3_prints_it(client):
    import html as html_lib
    import re

    from django.template.loader import render_to_string

    from apps.documents.services import build_contract_context
    from apps.gigs.factories import GigFactory

    tenant = _login(client)
    gig = GigFactory(tenant=tenant)

    client.post(
        reverse("documents:contract-complete", args=[gig.pk]),
        {"venue-configuration": "Assis, 300 places"},
    )

    gig.refresh_from_db()
    html = render_to_string("documents/contracts/model_3.html", build_contract_context(gig))
    text = " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", html.split("</style>")[1])).split())
    assert "Configuration : Assis, 300 places" in text


def test_the_export_carries_the_six_criteria(client):
    from apps.tenants import data_export

    tenant = _login(client)
    PromoterFactory(
        tenant=tenant,
        kinds=["venue", "festival"],
        event_types=["concert"],
        aesthetics=["jazz", "dance"],
        formats=["seated"],
        usual_periods=["season"],
        event_roles=["co_producer"],
        indicative_capacity=300,
        qualification_other="=1+1",
    )

    header, rows = data_export.promoters_rows(tenant)

    row = dict(zip(header, rows[0], strict=True))
    assert row["Type d'organisateur"] == "Salle, Festival"
    assert row["Type d'évènement"] == "Concert"
    assert row["Esthétique / discipline"] == "Jazz, Danse"
    assert row["Format / jauge"] == "Assis"
    assert row["Période habituelle"] == "Saison"
    assert row["Rôle dans l'évènement"] == "Coproducteur"
    assert row["Jauge indicative"] == 300
    assert row["Autres précisions"] == "'=1+1"  # neutralised like every free text
