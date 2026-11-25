"""The date page: summary with its progress rule, latest actions, then the four volet cards."""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.addressbook import services as addressbook_services
from apps.addressbook.factories import ContactFactory
from apps.documents.models import Invoice
from apps.documents.services import generate_contract_pdf, mark_contract_sent, mark_contract_signed
from apps.finance.models import Payment
from apps.gigs import checklist, services
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


def test_the_page_is_ordered_summary_then_timeline_then_the_four_volets(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)

    content = _page(client, gig)

    positions = [
        content.index("gig-summary"),
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


def test_the_timeline_gives_each_milestone_its_stored_date_and_leaves_the_rest_to_come():
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)
    mark_contract_sent(gig)

    steps = {step["label"]: step["day"] for step in services.gig_timeline(gig)}

    assert steps["Contrat généré"] is not None and steps["Contrat envoyé"] is not None
    assert steps["Contrat signé"] is None and steps["Solde payé"] is None
    labels = [step["label"] for step in services.gig_timeline(gig)]
    assert labels.index("Contrat généré") < labels.index("Contrat signé")
    assert labels.index("Facture d'acompte émise") < labels.index("Solde payé")


def test_the_timeline_follows_the_form_sent_to_the_organiser():
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    invitation = addressbook_services.create_invitation(gig.promoter, None)

    steps = {step["label"]: step["day"] for step in services.gig_timeline(gig)}
    assert steps["Formulaire envoyé"] is not None and steps["Formulaire reçu"] is None

    invitation.completed_at = timezone.now()
    invitation.save()
    steps = {step["label"]: step["day"] for step in services.gig_timeline(gig)}
    assert steps["Formulaire reçu"] is not None


def test_the_timeline_shows_an_invoice_paid_on_the_payment_date():
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    invoice = Invoice.objects.create(
        gig=gig,
        tenant=gig.tenant,
        kind=Invoice.Kind.DEPOSIT,
        status=Invoice.Status.PAID,
        issue_date=datetime.date(2030, 1, 2),
    )
    Payment.objects.create(
        invoice=invoice,
        tenant=gig.tenant,
        date=datetime.date(2030, 1, 9),
        amount=100,
        method="transfer",
    )

    steps = {step["label"]: step["day"] for step in services.gig_timeline(gig)}

    assert steps["Facture d'acompte émise"] == datetime.date(2030, 1, 2)
    assert steps["Acompte payé"] == datetime.date(2030, 1, 9)


def test_the_page_shows_the_timeline_the_documents_and_the_contacts(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=Gig.Status.CONFIRMED)
    ContactFactory(tenant=tenant, name="Alice Régie", email="a@example.org", promoter=gig.promoter)
    ContactFactory(
        tenant=tenant, name="Bob Salle", phone="0102030405", promoter=None, venue=gig.venue
    )
    generate_contract_pdf(gig)

    content = _page(client, gig)

    assert "Suivi de la date" in content and "Dernières actions" not in content
    assert "Version 1" in content
    assert "Alice Régie" in content and "mailto:a@example.org" in content
    assert "Bob Salle" in content and "tel:0102030405" in content


def test_a_contact_of_another_structure_never_shows_on_the_date(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=Gig.Status.CONFIRMED)
    other = GigFactory(status=Gig.Status.CONFIRMED)
    ContactFactory(tenant=other.tenant, name="Secret Autre", promoter=gig.promoter)
    Invoice.objects.create(
        gig=other,
        tenant=other.tenant,
        kind="full",
        number="F-SECRET",
        issue_date=datetime.date(2030, 1, 1),
    )

    content = _page(client, gig)

    assert "Secret Autre" not in content and "F-SECRET" not in content


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


# --- "Mes dates": the four icons on each card -------------------------------------------------


def test_the_cards_of_my_dates_show_the_four_volets_with_their_steps(client):
    tenant = _login(client)
    gig = GigFactory(tenant=tenant, status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)
    mark_contract_signed(gig)

    content = client.get(reverse("gigs:list")).content.decode()

    assert "brand/volet-contrats.svg" in content  # signed: the full icon
    assert "Contrats : 3 étape(s) sur 3" in content
    assert "Budget : 0 étape(s) sur 2" in content
    assert content.count("volet-todo") == 3  # Budget, Social, Régie: dashed letters


def test_a_cancelled_date_has_no_volet_icons_on_its_card(client):
    GigFactory(tenant=_login(client), status=Gig.Status.CANCELLED)

    assert "Avancement de la date" not in client.get(reverse("gigs:list")).content.decode()


def test_the_list_computes_the_progress_in_a_constant_number_of_queries(
    client, django_assert_max_num_queries
):
    tenant = _login(client)
    for _ in range(12):
        GigFactory(tenant=tenant, status=Gig.Status.CONFIRMED)
    client.get(reverse("gigs:list"))  # warm up

    with django_assert_max_num_queries(40):
        client.get(reverse("gigs:list"))


def test_the_bulk_progress_matches_the_single_gig_progress():
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)
    mark_contract_sent(gig)

    [bulk] = services.attach_progress([gig])

    assert bulk.progress == services.date_progress(gig)


def test_the_progress_of_a_list_never_reads_another_tenants_data():
    gig = GigFactory(status=Gig.Status.CONFIRMED)
    other = GigFactory(status=Gig.Status.CONFIRMED)
    generate_contract_pdf(other)

    [bulk] = services.attach_progress([gig])

    assert bulk.progress[0]["done_count"] == 0


def test_the_summary_shows_the_address_of_the_venue_next_to_its_name(client):
    gig = GigFactory(
        tenant=_login(client),
        venue__name="Le Bikini",
        venue__address="Parc de la Plaine",
        venue__postal_code="31520",
        venue__city="Ramonville-Saint-Agne",
    )

    content = _page(client, gig)

    assert "Le Bikini" in content
    assert "Parc de la Plaine, 31520 Ramonville-Saint-Agne" in content


def test_the_summary_shows_the_venue_alone_when_it_has_no_address(client):
    gig = GigFactory(
        tenant=_login(client),
        venue__name="Salle sans adresse",
        venue__address="",
        venue__postal_code="",
        venue__city="",
    )

    summary = _page(client, gig).split("gig-summary", 1)[1].split("</section>", 1)[0]

    assert "Salle sans adresse" in summary
    assert "·</span>" not in summary.split("Lieu", 1)[1].split("</p>", 1)[0]


def test_the_title_names_the_organiser_the_venue_and_the_city(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)

    content = _page(client, gig)

    heading = content.split("<h1")[1].split("</h1>")[0]
    assert gig.promoter.name in heading and gig.venue.name in heading
    if gig.venue.city:
        assert gig.venue.city in heading
    assert gig.show.title not in heading  # the show is only a line under the title


def test_the_next_action_comes_first_and_the_side_column_after_the_volets(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)

    content = _page(client, gig)

    ids = ("gig-next", "gig-summary", "volet-regie", "gig-contacts", "gig-documents")
    order = [content.index(f'id="{name}"') for name in (*ids, "gig-timeline")]
    assert order == sorted(order)
    assert "Ensuite : marquer le contrat comme envoyé" in content


@pytest.mark.parametrize("status", [Gig.Status.OPTION, Gig.Status.CONFIRMED])
def test_there_is_only_one_coral_button(client, status):
    gig = GigFactory(tenant=_login(client), status=status)

    assert _page(client, gig).count("btn-primary") == 1


def test_the_contract_and_budget_volets_hold_their_boxes_once(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)

    content = _page(client, gig)

    for volet, keys in checklist.VOLET_ITEMS.items():
        card = content.split(f'id="volet-{volet}"')[1].split("</section>")[0]
        for key in keys:
            assert f'id="checklist-{key}"' in card
            assert content.count(f'id="checklist-{key}"') == 1


def test_a_box_of_a_volet_is_read_only_when_automatic_and_stays_ticked_when_manual(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)
    generate_contract_pdf(gig)
    mark_contract_sent(gig)
    checklist.set_item(gig, "rider_sent", True, None)

    content = _page(client, gig)

    sent = content.split('id="checklist-contract_sent"')[1].split("</li>")[0]
    assert "disabled checked" in sent and "<form" not in sent
    rider = content.split('id="checklist-rider_sent"')[1].split("</li>")[0]
    assert 'value="true" checked' in rider


def test_a_step_already_shown_as_a_box_is_not_listed_twice(client):
    gig = GigFactory(tenant=_login(client), status=Gig.Status.CONFIRMED)

    content = _page(client, gig)

    contrats = content.split('id="volet-contrats"')[1].split("</section>")[0]
    assert "Contrat généré" in contrats and contrats.count(">Contrat envoyé<") == 1
    budget = content.split('id="volet-budget"')[1].split("</section>")[0]
    assert "Facture émise" not in budget and "Factures payées" not in budget
