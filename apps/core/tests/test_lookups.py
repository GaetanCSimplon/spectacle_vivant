"""Recette n°1: ORG-01 (company by SIRET or name), ORG-02 (communes of a postal code), STR-04."""

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.addressbook.models import Promoter
from apps.catalog.factories import ShowFactory
from apps.core import lookups
from apps.tenants import choices
from apps.tenants.factories import MembershipFactory, TenantFactory

pytestmark = pytest.mark.django_db

SIREN = "732829320"
COMPANY_ANSWER = {
    "results": [
        {
            "siren": SIREN,
            "nom_complet": "ASSOCIATION DES AMIS DU SOLEIL",
            "siege": {
                "siret": "73282932000074",
                "activite_principale": "90.01Z",
                "numero_voie": "12",
                "type_voie": "RUE",
                "libelle_voie": "DES ARTS",
                "code_postal": "34000",
                "libelle_commune": "MONTPELLIER",
                "adresse": "12 RUE DES ARTS 34000 MONTPELLIER",
            },
        }
    ]
}


@pytest.fixture(autouse=True)
def _on(settings):
    settings.LOOKUPS_ENABLED = True
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def fake(monkeypatch):
    """Replace the network: `fake.answer` is returned, `fake.calls` records the parameters."""

    class Fake:
        answer = COMPANY_ANSWER
        error = None
        calls = []

    def fetch(url, params):
        Fake.calls.append((url, params))
        if Fake.error:
            raise Fake.error
        return Fake.answer

    Fake.calls = []
    Fake.error = None
    Fake.answer = COMPANY_ANSWER
    monkeypatch.setattr(lookups, "_fetch_json", fetch)
    return Fake


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership


# --- the pure pieces ----------------------------------------------------------------------------


def test_the_vat_number_follows_the_siren():
    assert lookups.vat_number_from_siren("356000000") == "FR39356000000"  # La Poste
    assert lookups.vat_number_from_siren(SIREN).startswith("FR")
    assert lookups.vat_number_from_siren("12") == ""
    assert lookups.vat_number_from_siren("") == ""


def test_a_company_is_read_from_the_answer(fake):
    search = lookups.search_companies("amis du soleil")

    company = search.companies[0]
    assert company.name == "ASSOCIATION DES AMIS DU SOLEIL"
    assert company.siret == "73282932000074"
    assert company.code_ape == "9001Z"
    assert company.street == "12 RUE DES ARTS"
    assert (company.postal_code, company.city, company.department) == ("34000", "Montpellier", "34")
    assert company.vat_number == lookups.vat_number_from_siren(SIREN)


def test_a_siret_asks_for_the_digits_only_and_picks_that_establishment(fake):
    fake.answer = {
        "results": [
            {
                "siren": SIREN,
                "nom_complet": "ASSOCIATION",
                "siege": {"siret": "73282932000074", "code_postal": "34000"},
                "matching_etablissements": [
                    {
                        "siret": "73282932000082",
                        "code_postal": "31000",
                        "libelle_commune": "TOULOUSE",
                        "adresse": "1 PLACE DU CAPITOLE 31000 TOULOUSE",
                    }
                ],
            }
        ]
    }

    search = lookups.search_companies("732 829 320 00082")

    assert fake.calls[0][1]["q"] == "73282932000082"
    assert search.companies[0].postal_code == "31000"
    assert search.companies[0].street == "1 PLACE DU CAPITOLE"


def test_a_street_without_detail_loses_its_postal_code_and_town(fake):
    fake.answer = {
        "results": [
            {
                "siren": SIREN,
                "nom_complet": "X",
                "siege": {
                    "siret": "73282932000074",
                    "adresse": "3 RUE NEUVE 34000 MONTPELLIER",
                    "code_postal": "34000",
                    "libelle_commune": "MONTPELLIER",
                },
            }
        ]
    }

    assert lookups.search_companies("xxx").companies[0].street == "3 RUE NEUVE"


@pytest.mark.parametrize("query", ["", "ab", "  a "])
def test_a_short_search_asks_for_more_and_calls_nothing(fake, query):
    search = lookups.search_companies(query)

    assert search.too_short and not fake.calls


def test_a_failure_gives_an_unavailable_answer_that_is_not_kept(fake):
    fake.error = TimeoutError("slow")

    assert lookups.search_companies("amis du soleil").available is False
    fake.error = None
    assert lookups.search_companies("amis du soleil").available is True


def test_a_badly_formed_answer_is_unavailable_not_an_error(fake):
    fake.answer = {"unexpected": True}

    assert lookups.search_companies("amis du soleil").available is False


def test_the_same_search_is_asked_once(fake):
    lookups.search_companies("amis du soleil")
    lookups.search_companies("amis du soleil")

    assert len(fake.calls) == 1


def test_a_disabled_service_never_calls_out(settings, fake):
    settings.LOOKUPS_ENABLED = False

    assert lookups.search_companies("amis du soleil").available is False
    assert not lookups.search_communes("34000").available
    assert not fake.calls


def test_communes_are_sorted_and_unique(fake):
    fake.answer = [{"nom": "Montpellier"}, {"nom": "Castelnau"}, {"nom": "Montpellier"}]

    assert lookups.search_communes("34 000").names == ["Castelnau", "Montpellier"]
    assert fake.calls[0][1]["codePostal"] == "34000"


@pytest.mark.parametrize("code", ["", "3400", "abcde", "340000"])
def test_a_wrong_postal_code_calls_nothing(fake, code):
    assert lookups.search_communes(code).names == []
    assert not fake.calls


# --- the views ----------------------------------------------------------------------------------


def test_the_company_view_requires_a_login(client):
    response = client.get(reverse("lookup-companies"), {"q": "soleil"})

    assert response.status_code == 302 and "login" in response.url


def test_the_company_view_lists_the_results_escaped(client, fake):
    _login(client)
    fake.answer = {
        "results": [
            {
                "siren": SIREN,
                "nom_complet": '<script>alert("x")</script>',
                "siege": {"siret": "73282932000074", "code_postal": "34000"},
            }
        ]
    }

    content = client.get(reverse("lookup-companies"), {"q": "soleil"}).content.decode()

    assert "<script>" not in content and "&lt;script&gt;" in content
    assert "732 829 320 00074" in content


def test_the_company_view_says_so_when_nothing_is_found_or_unavailable(client, fake):
    _login(client)
    fake.answer = {"results": []}
    assert (
        "Aucune structure trouvée"
        in client.get(reverse("lookup-companies"), {"q": "zzzz"}).content.decode()
    )
    fake.error = OSError("down")
    cache.clear()
    assert "indisponible" in client.get(reverse("lookup-companies"), {"q": "yyyy"}).content.decode()


def test_the_company_view_is_rate_limited_per_person(client, fake, monkeypatch):
    _login(client)
    monkeypatch.setitem(lookups.RATE_LIMIT, "companies", 2)

    answers = [
        client.get(reverse("lookup-companies"), {"q": f"nom {n}"}).content.decode()
        for n in range(3)
    ]

    assert "indisponible" in answers[2] and "indisponible" not in answers[1]


def test_the_commune_view_offers_the_options_and_announces_a_single_one(client, fake):
    _login(client)
    fake.answer = [{"nom": "Montpellier"}]

    response = client.get(reverse("lookup-communes"), {"postal_code": "34070"})

    assert '<datalist id="city-options"><option value="Montpellier">' in response.content.decode()
    assert "commune-found" in response["HX-Trigger"] and "Montpellier" in response["HX-Trigger"]


def test_the_commune_view_with_several_communes_announces_nothing(client, fake):
    _login(client)
    fake.answer = [{"nom": "A"}, {"nom": "B"}]

    response = client.get(reverse("lookup-communes"), {"postal_code": "34070"})

    assert "HX-Trigger" not in response and response.content.decode().count("<option") == 2


def test_the_commune_view_requires_a_login(client):
    assert client.get(reverse("lookup-communes"), {"postal_code": "34070"}).status_code == 302


# --- where the search box and the commune help appear ---------------------------------------------


def test_the_search_box_is_on_the_organiser_form_and_fills_the_billing_address(client):
    _login(client)

    content = client.get(reverse("addressbook:promoter-create")).content.decode()

    assert "Retrouver par SIRET ou par nom" in content
    assert "set('billing_address', d.street)" in content
    assert 'hx-get="/recherche/communes/"' in content and 'list="city-options"' in content


def test_the_search_box_is_in_the_new_organiser_step_of_a_date(client):
    membership = _login(client)
    show = ShowFactory(tenant=membership.tenant)
    client.post(reverse("gigs:wizard-show"), {"mode": "existing", "show": show.pk})

    content = client.get(reverse("gigs:wizard-promoter")).content.decode()

    assert "Retrouver par SIRET ou par nom" in content
    assert "set('billing_address', d.street)" in content


def test_the_search_box_is_on_the_structure_card_for_the_owner_only(client):
    owner = _login(client)
    assert (
        "Retrouver par SIRET ou par nom" in client.get(reverse("tenants:settings")).content.decode()
    )

    member = MembershipFactory(tenant=owner.tenant, role="member")
    client.force_login(member.user)
    assert (
        "Retrouver par SIRET ou par nom"
        not in client.get(reverse("tenants:settings")).content.decode()
    )


def test_a_filled_form_creates_the_organiser_only_in_the_users_structure(client):
    mine = _login(client)
    other = TenantFactory(name="Autre")

    client.post(
        reverse("addressbook:promoter-create"),
        {
            "name": "ASSOCIATION DES AMIS DU SOLEIL",
            "siret": "73282932000074",
            "code_ape": "9001Z",
            "billing_address": "12 RUE DES ARTS",
            "postal_code": "34000",
            "city": "Montpellier",
            "department": "34",
        },
    )

    promoter = Promoter.objects.get(name="ASSOCIATION DES AMIS DU SOLEIL")
    assert promoter.tenant == mine.tenant
    assert not Promoter.objects.filter(tenant=other).exists()


# --- STR-04: the list of APE codes ----------------------------------------------------------------


def test_a_code_of_the_list_is_stored_as_it_is(client):
    membership = _login(client)

    client.post(
        reverse("tenants:settings"),
        {"name": "Compagnie A", "vat_regime": "franchise", "code_ape": "9004Z"},
    )

    membership.tenant.refresh_from_db()
    assert membership.tenant.code_ape == "9004Z"


def test_a_code_outside_the_list_is_refused_unless_given_under_other(client):
    membership = _login(client)
    url = reverse("tenants:settings")
    base = {"name": "Compagnie A", "vat_regime": "franchise"}

    assert client.post(url, {**base, "code_ape": "1234X"}).status_code == 200
    client.post(url, {**base, "code_ape": "other", "code_ape_other": "62.01Z"})

    membership.tenant.refresh_from_db()
    assert membership.tenant.code_ape == "6201Z"


def test_an_old_code_outside_the_list_is_shown_under_other(client):
    membership = _login(client)
    membership.tenant.code_ape = "6201Z"
    membership.tenant.save()

    form = client.get(reverse("tenants:settings")).context["form"]

    assert form.initial["code_ape"] == "other" and form.initial["code_ape_other"] == "6201Z"


def test_the_listed_codes_have_the_right_shape():
    from apps.tenants.validators import validate_code_ape

    for code in choices.APE_CODE_VALUES:
        validate_code_ape(code)


# --- the privacy page ---------------------------------------------------------------------------


def test_the_privacy_page_tells_what_the_look_ups_send(client):
    content = client.get(reverse("legal-privacy")).content.decode()

    assert "Recherche d&#x27;entreprises" in content or "Recherche d'entreprises" in content
    assert "Découpage administratif" in content
