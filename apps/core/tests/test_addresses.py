"""Addresses in separate fields: street, postal code, city, department."""

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.addressbook.factories import PromoterFactory, VenueFactory
from apps.addressbook.forms import PromoterForm, VenueForm
from apps.addressbook.models import Venue
from apps.core.addresses import (
    DEPARTMENT_CHOICES,
    department_from_postal_code,
    format_address,
    normalize_postal_code,
)
from apps.documents import invoicing
from apps.documents.models import Invoice
from apps.documents.services import build_contract_context
from apps.gigs.factories import GigFactory
from apps.roadmaps.factories import LodgingFactory, RoadmapFactory
from apps.roadmaps.services import public_context
from apps.tenants.factories import MembershipFactory, TenantFactory

pytestmark = pytest.mark.django_db


# --- helpers ---------------------------------------------------------------------------


def test_the_department_list_covers_metropolitan_and_overseas_departments_once():
    codes = [code for code, _label in DEPARTMENT_CHOICES]
    assert len(codes) == len(set(codes)) == 101
    assert {"2A", "2B", "75", "971", "976"} <= set(codes)
    assert "20" not in codes


@pytest.mark.parametrize(
    ("postal_code", "expected"),
    [
        ("34000", "34"),
        ("75001", "75"),
        ("20000", "2A"),  # Ajaccio
        ("20199", "2A"),
        ("20200", "2B"),  # Bastia
        ("97100", "971"),
        ("97600", "976"),
        ("98000", ""),  # Monaco: not a department
        ("97500", ""),  # Saint-Pierre-et-Miquelon: not in the list
        ("3400", ""),
        ("abcde", ""),
        ("", ""),
        ("34 000", "34"),
    ],
)
def test_the_department_is_deduced_from_the_postal_code(postal_code, expected):
    assert department_from_postal_code(postal_code) == expected


def test_format_and_normalize():
    assert format_address("12 rue des Arts", "34000", "Montpellier") == (
        "12 rue des Arts\n34000 Montpellier"
    )
    assert format_address("", "34000", "Montpellier") == "34000 Montpellier"
    assert format_address("12 rue des Arts") == "12 rue des Arts"
    assert format_address("", "", "") == ""
    assert normalize_postal_code(" 34 000 ") == "34000"


def test_an_old_one_block_address_still_prints_as_it_was():
    venue = VenueFactory(address="12 rue des Lilas\n69000 Lyon")
    assert venue.full_address == "12 rue des Lilas\n69000 Lyon"
    assert venue.one_line_address == "12 rue des Lilas, 69000 Lyon"
    assert venue.postal_code == venue.city == venue.department == ""


# --- forms ---------------------------------------------------------------------------------


def _venue_data(**overrides):
    data = {"name": "Salle", "address": "1 rue X", "postal_code": "34 000", "city": "  Sète "}
    data.update(overrides)
    return data


def test_postal_code_is_tidied_and_the_department_guessed():
    form = VenueForm(_venue_data())
    assert form.is_valid(), form.errors
    assert form.cleaned_data["postal_code"] == "34000"
    assert form.cleaned_data["city"] == "Sète"
    assert form.cleaned_data["department"] == "34"


def test_an_explicit_department_is_kept():
    form = VenueForm(_venue_data(department="30"))
    assert form.is_valid()
    assert form.cleaned_data["department"] == "30"


@pytest.mark.parametrize("bad", ["3400", "ABCDE", "340000"])
def test_a_bad_postal_code_is_refused(bad):
    form = VenueForm(_venue_data(postal_code=bad))
    assert not form.is_valid()
    assert "postal_code" in form.errors


def test_an_unknown_department_is_refused():
    form = VenueForm(_venue_data(department="99"))
    assert not form.is_valid()
    assert "department" in form.errors


def test_all_address_fields_are_optional():
    form = PromoterForm({"name": "Mairie"}, tenant=TenantFactory())
    assert form.is_valid(), form.errors


def test_the_forms_show_the_four_fields_in_order():
    form = VenueForm()
    names = list(form.fields)
    assert names[names.index("address") : names.index("address") + 4] == [
        "address",
        "postal_code",
        "city",
        "department",
    ]


def test_saving_through_the_page_stores_the_separate_fields(client):
    membership = MembershipFactory()
    client.force_login(membership.user)

    client.post(reverse("addressbook:venue-create"), _venue_data())

    venue = Venue.objects.get()
    assert (venue.address, venue.postal_code, venue.city, venue.department) == (
        "1 rue X",
        "34000",
        "Sète",
        "34",
    )
    page = client.get(reverse("addressbook:venue-detail", args=[venue.pk])).content.decode()
    assert "34000 Sète" in page and "Hérault" in page


def test_the_profile_page_and_the_organiser_form_have_the_fields(client):
    client.force_login(MembershipFactory().user)
    for name in ("tenants:profile", "addressbook:promoter-create", "addressbook:venue-create"):
        content = client.get(reverse(name)).content.decode()
        assert "Code postal" in content and "Ville" in content and "Département" in content, name


def test_the_quick_create_forms_of_the_wizard_have_them_too():
    from apps.gigs.forms import PromoterQuickCreateForm, VenueQuickCreateForm
    from apps.roadmaps.forms import LodgingForm

    for form in (PromoterQuickCreateForm(), VenueQuickCreateForm(), LodgingForm()):
        assert {"postal_code", "city", "department"} <= set(form.fields)


# --- documents and sheets -----------------------------------------------------------------


def _gig():
    gig = GigFactory(
        price="1000.00",
        tenant__address="1 rue des Arts",
        tenant__postal_code="69001",
        tenant__city="Lyon",
        tenant__siret="12345678900012",
        promoter__billing_address="3 place de la Mairie",
        promoter__postal_code="34000",
        promoter__city="Montpellier",
        venue__address="Quai du Môle",
        venue__postal_code="34200",
        venue__city="Sète",
    )
    gig.refresh_from_db()
    return gig


def test_the_contract_prints_postal_code_and_city():
    html = render_to_string("documents/contracts/model_1.html", build_contract_context(_gig()))
    for expected in ("69001 Lyon", "34000 Montpellier", "34200 Sète"):
        assert expected in html


def test_an_issued_invoice_snapshots_the_full_addresses():
    gig = _gig()
    invoice = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.FULL))

    assert invoice.issuer_snapshot["address"] == "1 rue des Arts\n69001 Lyon"
    assert invoice.customer_snapshot["billing_address"] == "3 place de la Mairie\n34000 Montpellier"
    # Editing the address later never changes an issued invoice.
    gig.tenant.city = "Paris"
    gig.tenant.save()
    invoice.refresh_from_db()
    assert invoice.issuer_snapshot["address"].endswith("69001 Lyon")


def test_an_invoice_can_be_issued_with_only_the_new_fields_filled():
    gig = GigFactory(
        price="500.00",
        tenant__postal_code="69001",
        tenant__city="Lyon",
        tenant__siret="12345678900012",
        promoter__city="Nîmes",
    )
    gig.refresh_from_db()
    invoice = invoicing.create_invoice(gig, Invoice.Kind.FULL)
    missing = [str(item) for item in invoicing.missing_issue_requirements(invoice)]
    assert "l'adresse de votre structure" not in missing
    assert "l'adresse de facturation de l'organisateur" not in missing


def test_the_public_roadmap_prints_the_address_and_searches_it_on_one_line():
    roadmap = RoadmapFactory(gig=_gig())
    LodgingFactory(
        roadmap=roadmap,
        name="Hôtel",
        address="5 rue Neuve",
        postal_code="34200",
        city="Sète",
    )
    from apps.roadmaps.services import publish

    publish(roadmap)
    context = public_context(roadmap)
    assert context["venue"]["address"] == "Quai du Môle\n34200 Sète"
    assert context["venue"]["address_one_line"] == "Quai du Môle, 34200 Sète"

    from django.test import Client

    page = Client().get(reverse("roadmap-public", args=[roadmap.token])).content.decode()
    assert "34200 Sète" in page
    assert "query=Quai%20du%20M%C3%B4le%2C%2034200%20S%C3%A8te" in page
    assert "query=5%20rue%20Neuve%2C%2034200%20S%C3%A8te" in page


def test_the_promoter_city_never_reaches_the_public_roadmap():
    gig = GigFactory(promoter__billing_address="x", promoter__city="VILLE-SECRETE")
    roadmap = RoadmapFactory(gig=gig)
    from django.test import Client

    from apps.roadmaps.services import publish

    publish(roadmap)
    page = Client().get(reverse("roadmap-public", args=[roadmap.token])).content.decode()
    assert "VILLE-SECRETE" not in page


def test_the_promoter_search_also_finds_a_city(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    PromoterFactory(tenant=membership.tenant, name="Mairie A", city="Sète")
    PromoterFactory(tenant=membership.tenant, name="Mairie B", city="Lyon")

    response = client.get(reverse("addressbook:promoter-list"), {"q": "sète"})

    assert [p.name for p in response.context["object_list"]] == ["Mairie A"]
