"""The date page: summary with its progress rule, latest actions, then the four volet cards."""

import datetime

import pytest
from django.urls import reverse

from apps.documents.services import generate_contract_pdf, mark_contract_sent, mark_contract_signed
from apps.finance.factories import ExpenseFactory
from apps.gigs import services
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _page(client, gig):
    return client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def test_the_page_is_ordered_summary_then_history_then_the_four_volets(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)

    content = _page(client, gig)

    positions = [
        content.index("gig-summary"),
        content.index("gig-history"),
        content.index('id="volet-contrats"'),
        content.index('id="volet-budget"'),
        content.index('id="volet-social"'),
        content.index('id="volet-regie"'),
    ]
    assert positions == sorted(positions)


def test_a_new_confirmed_date_starts_at_zero_and_the_contract_is_the_next_step(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)

    response = client.get(reverse("gigs:detail", args=[gig.pk]))

    assert response.context["overall_percent"] == 0
    assert response.context["next_step"]["todo"] == "Générer le contrat"
    assert "Avancement de la date : 0 %" in response.content.decode()


def test_the_contract_has_three_steps_generated_sent_signed():
    gig = GigFactory(status=Gig.Status.CONFIRMED)

    def contrats():
        return services.date_progress(gig)[0]

    assert [step["done"] for step in contrats()["steps"]] == [False, False, False]
    generate_contract_pdf(gig)
    assert [step["done"] for step in contrats()["steps"]] == [True, False, False]
    mark_contract_sent(gig)
    assert [step["done"] for step in contrats()["steps"]] == [True, True, False]
    mark_contract_signed(gig)
    assert contrats()["done"] and contrats()["percent"] == 100


def test_a_signed_contract_counts_as_sent():
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)
    mark_contract_signed(gig)

    assert services.date_progress(gig)[0]["steps"][1]["done"] is True


def test_the_overall_progress_weighs_each_volet_a_quarter():
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)
    mark_contract_signed(gig)

    progress = services.date_progress(gig)

    assert services.overall_progress(progress) == 25


def test_no_next_step_for_an_option_or_a_cancelled_date():
    for status in (Gig.Status.OPTION, Gig.Status.CANCELLED):
        gig = GigFactory(status=status)
        assert services.next_step(gig, services.date_progress(gig)) is None


def test_the_history_lists_the_latest_actions_newest_first_and_is_capped():
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)
    mark_contract_sent(gig)
    ExpenseFactory(gig=gig, tenant=gig.tenant, label="Péage", date=datetime.date(2030, 1, 1))

    history = services.gig_history(gig)
    texts = [event["text"] for event in history]

    assert texts[0] == "Dépense ajoutée : Péage"
    assert "Contrat envoyé à l'organisateur" in texts and "Contrat généré (version 1)" in texts
    assert texts.index("Contrat envoyé à l'organisateur") < texts.index(
        "Contrat généré (version 1)"
    )
    for _ in range(10):
        ExpenseFactory(gig=gig, tenant=gig.tenant)
    assert len(services.gig_history(gig)) == 8


def test_the_history_never_shows_another_tenants_actions():
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    other = GigFactory(status=Gig.Status.CONFIRMED)
    ExpenseFactory(gig=other, tenant=other.tenant, label="Secret")

    assert all("Secret" not in event["text"] for event in services.gig_history(gig))


def test_the_page_says_so_when_nothing_was_done_and_shows_the_table_otherwise(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)

    content = _page(client, gig)

    assert "Dernières actions" in content and "Contrat généré (version 1)" in content


def test_each_volet_card_gives_access_to_its_actions(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)

    content = _page(client, gig)

    for name, args in (
        ("documents:contract-complete", [gig.pk]),
        ("documents:contract-history", [gig.pk]),
        ("documents:billing", [gig.pk]),
        ("finance:page", [gig.pk]),
        ("roadmaps:editor", [gig.pk]),
    ):
        assert reverse(name, args=args) in content
    assert 'id="equipe"' in content


def test_a_cancelled_date_has_no_progress_rule_and_no_next_step(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CANCELLED)

    content = _page(client, gig)

    assert "Avancement de la date" not in content
    assert "Réactiver la date" in content


def test_another_tenants_date_is_a_404(client):
    _login(client)
    gig = GigFactory(status=Gig.Status.CONFIRMED)

    assert client.get(reverse("gigs:detail", args=[gig.pk])).status_code == 404
