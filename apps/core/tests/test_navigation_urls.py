"""Menu of five entries: new addresses, 301 from the old ones, isolation of the new lists."""

import pytest
from django.urls import reverse

from apps.finance.factories import ExpenseFactory
from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def membership(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("/bord/equipe/social/", "/social/"),
        ("/bord/equipe/social/historique/", "/social/historique/"),
        ("/bord/equipe/social/export/?mois=2026-11", "/social/export/?mois=2026-11"),
        ("/documents/", "/bord/documents/"),
        ("/documents/?types=invoice", "/bord/documents/?types=invoice"),
        ("/organisateurs/", "/contacts/?type=organisateurs"),
        ("/lieux/?q=cave", "/contacts/?q=cave&type=lieux"),
    ],
)
def test_each_old_address_redirects_for_good_to_the_new_one(client, membership, old, new):
    response = client.get(old)

    assert response.status_code == 301
    assert response.url == new


@pytest.mark.parametrize(
    ("url", "entry"),
    [
        ("/", "Accueil"),
        ("/bord/", "Bòrd"),
        ("/bord/depenses/", "Bòrd"),
        ("/bord/documents/", "Bòrd"),
        ("/dates/", "Dates"),
        ("/social/", "Social"),
        ("/contacts/?type=lieux", "Contacts"),
    ],
)
def test_the_new_addresses_answer_and_light_up_one_entry(client, membership, url, entry):
    content = client.get(url).content.decode()

    assert content.count('aria-current="page"') == 2  # sidebar + burger menu
    assert f"{entry}</a>" in content.split('aria-current="page"')[1]


def test_a_page_of_ma_structure_lights_no_entry(client, membership):
    content = client.get(reverse("tenants:settings")).content.decode()

    assert 'aria-current="page"' not in content


def test_the_directory_defaults_to_organisers_and_ignores_an_unknown_type(client, membership):
    for url in ("/contacts/", "/contacts/?type=nimportequoi"):
        assert client.get(url).context["view"].__class__.__name__ == "PromoterListView"


def test_the_expense_list_shows_my_expenses_and_never_another_structures(client, membership):
    mine = ExpenseFactory(
        tenant=membership.tenant, gig=GigFactory(tenant=membership.tenant), label="Péage du matin"
    )
    other = ExpenseFactory(label="Dépense étrangère")

    content = client.get(reverse("bord-expenses")).content.decode()

    assert mine.label in content
    assert other.label not in content


def test_the_expense_list_needs_a_login(client):
    assert client.get(reverse("bord-expenses")).status_code == 302


def test_secret_link_addresses_did_not_move():
    assert reverse("roadmap-public", args=["t"]) == "/feuille-de-route/t/"
    assert reverse("team-space", args=["t"]) == "/equipe/t/"
    assert reverse("promoter-form-public", args=["t"]) == "/formulaire-organisateur/t/"
    assert reverse("tour-form-public", args=["t"]) == "/regie-de-tournee/t/"
    assert reverse("contract-share-public", args=["t"]) == "/contrat-partage/t/"


# --- Ma structure --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("/bord/informations/", "/structure/"),
        ("/bord/informations/messages/", "/structure/documents/"),
        ("/bord/equipe/", "/structure/equipe/"),
        ("/bord/equipe/12/modifier/", "/structure/equipe/12/modifier/"),
        ("/bord/equipe/?q=lea", "/structure/equipe/?q=lea"),
        ("/spectacles/", "/structure/spectacles/"),
        ("/spectacles/3/fichier/rider/", "/structure/spectacles/3/fichier/rider/"),
        ("/bord/export-donnees/", "/structure/compte/export-donnees/"),
        ("/bord/supprimer/", "/structure/compte/supprimer/"),
        ("/bord/quitter/", "/structure/compte/quitter/"),
        ("/bord/equipe/social/", "/social/"),
    ],
)
def test_each_old_address_of_ma_structure_redirects_for_good(client, membership, old, new):
    response = client.get(old)

    assert response.status_code == 301
    assert response.url == new


OWNER_TABS = [
    "tenants:settings",
    "tenants:person-list",
    "catalog:show-list",
    "tenants:paratge",
    "tenants:message-templates",
    "tenants:account",
]


@pytest.mark.parametrize("name", OWNER_TABS)
def test_the_owner_opens_every_tab_and_sees_the_six_tabs(client, membership, name):
    response = client.get(reverse(name))
    content = response.content.decode()

    assert response.status_code == 200
    nav = content.split('<nav aria-label="Ma structure"')[1].split("</nav>")[0]
    assert [
        label
        for label in ("Fiche", "Équipe", "Spectacles", "Paratge", "Documents", "Compte et offre")
        if label in nav
    ] == [
        "Fiche",
        "Équipe",
        "Spectacles",
        "Paratge",
        "Documents",
        "Compte et offre",
    ]


@pytest.fixture
def member(client):
    membership = MembershipFactory(role="member")
    client.force_login(membership.user)
    return membership


@pytest.mark.parametrize(
    "name",
    ["tenants:settings", "tenants:paratge", "tenants:message-templates", "tenants:account"],
)
def test_a_member_gets_a_403_on_the_owner_tabs(client, member, name):
    assert client.get(reverse(name)).status_code == 403


def test_a_member_reads_the_team_and_edits_the_shows(client, member):
    team = client.get(reverse("tenants:person-list"))
    shows = client.get(reverse("catalog:show-list"))
    new_show = client.get(reverse("catalog:show-create"))

    assert (team.status_code, shows.status_code, new_show.status_code) == (200, 200, 200)
    nav = team.content.decode().split('<nav aria-label="Ma structure"')[1].split("</nav>")[0]
    assert "Équipe" in nav and "Spectacles" in nav
    assert "Fiche" not in nav and "Compte et offre" not in nav and "Paratge" not in nav


def test_ma_structure_leads_a_member_to_the_team_and_an_owner_to_the_fiche(client, member):
    aside = client.get(reverse("home")).content.decode().split("<aside")[1].split("</aside>")[0]
    assert f'href="{reverse("tenants:person-list")}"' in aside and "Ma structure" in aside

    client.force_login(MembershipFactory().user)
    aside = client.get(reverse("home")).content.decode().split("<aside")[1].split("</aside>")[0]
    assert f'href="{reverse("tenants:settings")}"' in aside


def test_a_member_can_leave_the_structure_from_the_team_page(client, member):
    content = client.get(reverse("tenants:person-list")).content.decode()

    assert reverse("tenants:leave") in content
    assert reverse("tenants:person-create") not in content


def test_the_fiche_says_in_words_what_is_missing_to_issue_an_invoice(client, membership):
    tenant = membership.tenant
    tenant.siret, tenant.iban, tenant.bic = "", "", ""
    tenant.save()

    content = client.get(reverse("tenants:settings")).content.decode()

    assert "il manque" in content and "le SIRET" in content and "IBAN" in content


def test_another_structures_show_and_person_are_not_found(client, membership):
    from apps.catalog.factories import ShowFactory
    from apps.tenants.factories import PersonFactory

    show, person = ShowFactory(), PersonFactory()

    assert client.get(reverse("catalog:show-detail", args=[show.pk])).status_code == 404
    assert client.get(reverse("tenants:person-detail", args=[person.pk])).status_code == 404
