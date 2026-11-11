"""Recette n°1, "Ma structure": STR-01, STR-02, STR-03, STR-05, STR-06."""

import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.tenants import choices
from apps.tenants.models import Tenant
from apps.tenants.validators import format_siret, normalize_siret, validate_siret

from ..factories import MembershipFactory, TenantFactory

pytestmark = pytest.mark.django_db

URL = reverse("tenants:settings")
ONBOARDING = reverse("tenants-onboarding")
VALID_SIRET = "73282932000074"


def _login(client, **tenant_fields):
    fields = {"name": "Compagnie A", **tenant_fields}
    membership = MembershipFactory(**{f"tenant__{key}": value for key, value in fields.items()})
    client.force_login(membership.user)
    return membership.tenant


def _payload(**overrides):
    data = {"name": "Compagnie A", "vat_regime": "franchise"}
    data.update(overrides)
    return data


# --- STR-03: SIRET ------------------------------------------------------------------------------


def test_spaces_are_removed_and_the_stored_siret_has_14_digits(client):
    tenant = _login(client)

    client.post(URL, _payload(siret="732 829 320 00074"))

    tenant.refresh_from_db()
    assert tenant.siret == VALID_SIRET


@pytest.mark.parametrize("siret", ["73282932000075", "1234", "7328293200007A", "1" * 15])
def test_a_wrong_siret_is_refused_and_nothing_is_saved(client, siret):
    tenant = _login(client, name="Compagnie A")

    response = client.post(URL, _payload(name="Autre nom", siret=siret))

    assert response.status_code == 200
    tenant.refresh_from_db()
    assert tenant.name == "Compagnie A" and tenant.siret == ""


def test_an_empty_siret_stays_allowed(client):
    tenant = _login(client, siret=VALID_SIRET)

    response = client.post(URL, _payload(siret=""))

    assert response.status_code == 302
    tenant.refresh_from_db()
    assert tenant.siret == ""


def test_the_form_shows_the_siret_in_groups(client):
    _login(client, siret=VALID_SIRET)

    content = client.get(URL).content.decode()

    assert 'value="732 829 320 00074"' in content


def test_la_poste_siret_follows_its_own_rule():
    validate_siret("35600000000048")  # head office, valid Luhn
    validate_siret("35600000000022")  # an establishment: digit sum divisible by 5


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        (VALID_SIRET, "732 829 320 00074"),
        ("732 829 320", "732 829 320"),
        ("123456789", "123 456 789"),
        ("abc", "abc"),
        ("", ""),
        (None, ""),
    ],
)
def test_format_siret(raw, shown):
    assert format_siret(raw) == shown
    assert " " not in normalize_siret(shown) if shown else True


# --- STR-01: legal form -------------------------------------------------------------------------


def test_a_legal_form_of_the_list_is_stored_as_its_label(client):
    tenant = _login(client)

    client.post(URL, _payload(legal_form=choices.LEGAL_FORMS[2]))

    tenant.refresh_from_db()
    assert tenant.legal_form == "Association loi 1901"


def test_other_legal_form_stores_the_typed_text(client):
    tenant = _login(client)

    client.post(URL, _payload(legal_form="other", legal_form_other="  GIE   du Sud "))

    tenant.refresh_from_db()
    assert tenant.legal_form == "GIE du Sud"


def test_other_without_a_text_is_refused(client):
    tenant = _login(client, legal_form="SA")

    response = client.post(URL, _payload(legal_form="other", legal_form_other=""))

    assert response.status_code == 200
    assert "Précisez votre choix" in response.content.decode()
    tenant.refresh_from_db()
    assert tenant.legal_form == "SA"


def test_a_value_outside_the_list_is_refused(client):
    _login(client)

    response = client.post(URL, _payload(legal_form="Société imaginaire"))

    assert response.status_code == 200


def test_an_old_free_text_is_shown_under_other_and_kept(client):
    tenant = _login(client, legal_form="micro-entreprise")

    content = client.get(URL).content.decode()
    form = client.get(URL).context["form"]

    assert form.initial["legal_form"] == "other"
    assert form.initial["legal_form_other"] == "micro-entreprise"
    assert "micro-entreprise" in content
    client.post(URL, _payload(legal_form="other", legal_form_other="micro-entreprise"))
    tenant.refresh_from_db()
    assert tenant.legal_form == "micro-entreprise"


def test_the_onboarding_offers_the_same_list_and_stores_the_label(client):
    user = UserFactory()
    client.force_login(user)

    page = client.get(ONBOARDING).content.decode()
    client.post(
        ONBOARDING, {"name": "Les Pins", "legal_form": "SARL / EURL", "vat_regime": "franchise"}
    )

    assert "Association loi 1901" in page
    assert Tenant.objects.get(name="Les Pins").legal_form == "SARL / EURL"


def test_the_onboarding_accepts_another_legal_form(client):
    client.force_login(UserFactory())

    client.post(
        ONBOARDING,
        {
            "name": "Les Pins",
            "legal_form": "other",
            "legal_form_other": "GIE",
            "vat_regime": "franchise",
        },
    )

    assert Tenant.objects.get(name="Les Pins").legal_form == "GIE"


# --- STR-02: where to complete the legal information ----------------------------------------------


def test_the_onboarding_points_to_the_legal_information(client):
    client.force_login(UserFactory())

    response = client.post(
        ONBOARDING, {"name": "Les Pins", "legal_form": "", "vat_regime": "franchise"}, follow=True
    )

    content = response.content.decode()
    assert response.redirect_chain[-1][0] == reverse("gigs:wizard-show")
    assert "Les compléter maintenant" in content
    assert f'href="{URL}"' in content


# --- STR-05: first and last name of the representative ----------------------------------------


def test_first_and_last_name_make_the_name_printed_on_documents(client):
    tenant = _login(client)

    client.post(
        URL, _payload(representative_first_name=" Julie ", representative_last_name="Martin  ")
    )

    tenant.refresh_from_db()
    assert tenant.representative_first_name == "Julie"
    assert tenant.representative_last_name == "Martin"
    assert tenant.representative_name == "Julie Martin"


def test_a_compound_name_is_not_cut(client):
    tenant = _login(client)

    client.post(
        URL,
        _payload(representative_first_name="Marie Anne", representative_last_name="de la Tour"),
    )

    tenant.refresh_from_db()
    assert tenant.representative_name == "Marie Anne de la Tour"
    assert tenant.representative_first_name == "Marie Anne"


def test_clearing_both_names_clears_the_printed_name(client):
    tenant = _login(client, representative_name="Julie Martin")

    client.post(URL, _payload(representative_first_name="", representative_last_name=""))

    tenant.refresh_from_db()
    assert tenant.representative_name == ""


def test_an_old_single_name_is_offered_in_the_last_name_to_be_split(client):
    tenant = _login(client, representative_name="Julie Martin")

    page = client.get(URL)

    assert page.context["form"].initial["representative_last_name"] == "Julie Martin"
    assert "répartissez-le" in page.content.decode()
    tenant.refresh_from_db()
    assert tenant.representative_name == "Julie Martin"  # nothing changes until it is saved


def test_the_hint_goes_away_once_the_name_is_split(client):
    _login(
        client,
        representative_name="Julie Martin",
        representative_first_name="Julie",
        representative_last_name="Martin",
    )

    assert "répartissez-le" not in client.get(URL).content.decode()


# --- STR-06: role of the representative -------------------------------------------------------


def test_a_role_of_the_list_is_stored_as_written(client):
    tenant = _login(client)

    client.post(URL, _payload(representative_role="Trésorier(ère)"))

    tenant.refresh_from_db()
    assert tenant.representative_role == "Trésorier(ère)"


def test_other_role_stores_the_typed_text(client):
    tenant = _login(client)

    client.post(URL, _payload(representative_role="other", representative_role_other="Mandataire"))

    tenant.refresh_from_db()
    assert tenant.representative_role == "Mandataire"


def test_a_role_outside_the_list_is_refused(client):
    _login(client)

    assert client.post(URL, _payload(representative_role="Roi")).status_code == 200


def test_an_old_free_role_is_shown_under_other(client):
    _login(client, representative_role="Présidente")

    form = client.get(URL).context["form"]

    assert form.initial["representative_role"] == "other"
    assert form.initial["representative_role_other"] == "Présidente"


def test_every_role_is_written_once():
    assert len(choices.ROLES) == len(set(choices.ROLES))


# --- isolation ------------------------------------------------------------------------------------


def test_a_member_never_changes_another_structure(client):
    mine = _login(client)
    other = TenantFactory(name="Autre", siret=VALID_SIRET, representative_name="Z Z")

    client.post(URL, _payload(siret="", representative_first_name="Julie"))

    other.refresh_from_db()
    assert other.siret == VALID_SIRET and other.representative_name == "Z Z"
    mine.refresh_from_db()
    assert mine.representative_name == "Julie"
