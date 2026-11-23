"""Confirmation messages of the roadmap editor, the billing pages and the shows (PR 0)."""

import html

import pytest
from django.urls import reverse

from apps.catalog.factories import ShowFactory
from apps.documents import invoicing
from apps.gigs.factories import GigFactory
from apps.roadmaps.models import Lodging
from apps.tenants.factories import MembershipFactory, PersonFactory

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def tenant(client):
    membership = MembershipFactory(
        tenant__address="1 rue des Arts, 69001 Lyon",
        tenant__siret="12345678900012",
        tenant__vat_regime="franchise",
    )
    client.force_login(membership.user)
    return membership.tenant


def _says(client, url, data, text, **extra):
    response = client.post(url, data, follow=True, **extra)
    assert text in html.unescape(response.content.decode())
    return response


def test_roadmap_changes_are_confirmed(client, tenant):
    gig = GigFactory(tenant=tenant)
    rm = lambda name, *args: reverse(f"roadmaps:{name}", args=[gig.pk, *args])  # noqa: E731
    _says(client, rm("notes"), {"notes": "Parking derrière"}, "Les notes sont enregistrées.")
    _says(
        client,
        rm("item-add", "hebergements"),
        {"name": "Hôtel", "address": "3 quai"},
        "L'élément est ajouté.",
    )
    lodging = Lodging.objects.get()
    _says(
        client,
        rm("item-edit", "hebergements", lodging.pk),
        {"name": "Hôtel du Lac", "address": "3 quai"},
        "L'élément est modifié.",
    )
    _says(
        client,
        rm("contact-add", "hebergements", lodging.pk),
        {"name": "Accueil"},
        "Le contact est ajouté.",
    )
    contact = lodging.contacts.get()
    _says(
        client,
        rm("contact-delete", "hebergements", lodging.pk, contact.pk),
        {},
        "Le contact est supprimé.",
    )
    _says(client, rm("item-delete", "hebergements", lodging.pk), {}, "L'élément est supprimé.")
    person = PersonFactory(tenant=tenant)
    _says(client, rm("team-add"), {"person": person.pk}, "La personne est ajoutée")


def test_roadmap_htmx_shows_the_message_once_inside_the_block(client, tenant):
    gig = GigFactory(tenant=tenant)
    url = reverse("roadmaps:item-add", args=[gig.pk, "hebergements"])

    content = html.unescape(
        client.post(url, {"name": "Hôtel", "address": "3 quai"}, **HTMX).content.decode()
    )

    assert "<html" not in content
    assert content.count("L'élément est ajouté.") == 1


def test_a_roadmap_form_error_gives_no_success_message(client, tenant):
    gig = GigFactory(tenant=tenant)
    url = reverse("roadmaps:item-add", args=[gig.pk, "creneaux"])

    content = html.unescape(client.post(url, {"label": "x"}, **HTMX).content.decode())

    assert "L'élément est ajouté." not in content


def test_billing_drafts_and_lines_are_confirmed(client, tenant):
    gig = GigFactory(
        tenant=tenant, price="1000.00", promoter__billing_address="3 place de la Mairie, Nîmes"
    )
    invoice = invoicing.create_invoice(gig, invoicing.Invoice.Kind.FULL)
    base = ["documents:line-add", gig.pk, "factures", invoice.pk]
    data = {"label": "Transport", "quantity": "2", "unit_price_excl_tax": "40.50"}
    _says(client, reverse(base[0], args=base[1:]), data, "La ligne est ajoutée.")
    line = invoice.lines.get(label="Transport")
    _says(
        client,
        reverse("documents:line-edit", args=[gig.pk, "factures", invoice.pk, line.pk]),
        {
            f"line{line.pk}-label": "Péage",
            f"line{line.pk}-quantity": "1",
            f"line{line.pk}-unit_price_excl_tax": "9.00",
        },
        "La ligne est modifiée.",
    )
    _says(
        client,
        reverse("documents:line-remove", args=[gig.pk, "factures", invoice.pk, line.pk]),
        {},
        "La ligne est supprimée.",
    )


def test_a_new_quote_draft_is_confirmed(client, tenant):
    gig = GigFactory(
        tenant=tenant, price="1000.00", promoter__billing_address="3 place de la Mairie, Nîmes"
    )
    _says(client, reverse("documents:quote-create", args=[gig.pk]), {}, "Le brouillon est créé.")


def test_a_credit_note_draft_is_confirmed(client, tenant):
    gig = GigFactory(
        tenant=tenant, price="1000.00", promoter__billing_address="3 place de la Mairie, Nîmes"
    )
    invoice = invoicing.issue_invoice(invoicing.create_invoice(gig, invoicing.Invoice.Kind.FULL))
    _says(
        client,
        reverse("documents:credit-note-create", args=[gig.pk, invoice.pk]),
        {},
        "Le brouillon d'avoir est créé.",
    )


def test_deleting_a_show_is_confirmed_but_a_refusal_is_not(client, tenant):
    show = ShowFactory(tenant=tenant)
    used = ShowFactory(tenant=tenant)
    GigFactory(tenant=tenant, show=used)

    refused = client.post(reverse("catalog:show-delete", args=[used.pk]), follow=True)
    assert "Impossible de supprimer" in refused.content.decode()
    assert "Le spectacle est supprimé." not in refused.content.decode()
    _says(client, reverse("catalog:show-delete", args=[show.pk]), {}, "Le spectacle est supprimé.")
