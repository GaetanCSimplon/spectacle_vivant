"""Recette n°1, CTR-07 and FDR-04: meals and lodging taken in charge, and the day's program."""

import datetime
import html as html_lib
import re

import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.documents.services import build_contract_context
from apps.finance.tests.helpers import TENANT_FIELDS, make_gig
from apps.roadmaps.factories import (
    LodgingFactory,
    MealFactory,
    RoadmapFactory,
    RoadmapSlotFactory,
)
from apps.roadmaps.services import build_program, public_context, publish
from apps.tenants.factories import MembershipFactory, TenantFactory

from .. import hospitality as h

pytestmark = pytest.mark.django_db

T = datetime.time


@pytest.fixture
def tenant(client):
    membership = MembershipFactory(
        **{f"tenant__{key}": value for key, value in TENANT_FIELDS.items()}
    )
    client.force_login(membership.user)
    return membership.tenant


def _complete_url(gig):
    return reverse("documents:contract-complete", args=[gig.pk])


def _text(html):
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL)
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", html)).split())


# --- the sentence of the contract ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("covered_by", "count", "notes", "expected"),
    [
        ("organiser", 8, "Végétarien ×2", "À la charge de l'Organisateur : 8 repas. Végétarien ×2"),
        ("organiser", 1, "", "À la charge de l'Organisateur : 1 repas"),
        ("producer", None, "", "À la charge du Producteur"),
        ("shared", 4, "moitié chacun", "Pris en charge à frais partagés : 4 repas. moitié chacun"),
        ("none", 6, "", "Non concerné"),
        ("", None, "Buffet froid", "Buffet froid"),
        ("", None, "", ""),
        ("", 3, "", "3 repas"),
    ],
)
def test_the_sentence_is_composed(covered_by, count, notes, expected):
    assert h.compose(covered_by, count, h.MEAL_UNIT, notes) == expected


def test_nights_are_counted_in_the_singular_and_plural():
    assert h.compose("organiser", 1, h.NIGHT_UNIT, "") == "À la charge de l'Organisateur : 1 nuit"
    assert h.compose("organiser", 2, h.NIGHT_UNIT, "") == "À la charge de l'Organisateur : 2 nuits"


def test_the_roadmap_line_names_who_pays_and_how_many_only():
    assert (
        h.roadmap_line("organiser", 8, h.MEAL_UNIT) == "pris en charge par l'organisateur · 8 repas"
    )
    assert h.roadmap_line("producer", None, h.MEAL_UNIT) == "pris en charge par le producteur"
    assert h.roadmap_line("none", 3, h.MEAL_UNIT) == ""
    assert h.roadmap_line("", 3, h.MEAL_UNIT) == ""


# --- the form -----------------------------------------------------------------------------------


def test_the_answers_are_saved_and_the_sentences_composed(client, tenant):
    gig = make_gig(tenant=tenant)

    client.post(
        _complete_url(gig),
        {
            "gig-meals_covered_by": "organiser",
            "gig-meals_count": "8",
            "gig-meals_notes": "Végétarien ×2",
            "gig-lodging_covered_by": "shared",
            "gig-lodging_nights": "2",
            "gig-lodging_notes": "Une chambre chacun",
        },
    )

    gig.refresh_from_db()
    assert gig.meals_covered_by == "organiser" and gig.meals_count == 8
    assert gig.meals == "À la charge de l'Organisateur : 8 repas. Végétarien ×2"
    assert gig.lodging == "Pris en charge à frais partagés : 2 nuits. Une chambre chacun"


def test_clearing_the_answers_clears_the_sentences(client, tenant):
    gig = make_gig(tenant=tenant, gig_fields={"meals_covered_by": "organiser", "meals": "x"})

    client.post(_complete_url(gig), {"gig-meals_covered_by": ""})

    gig.refresh_from_db()
    assert gig.meals == "" and gig.meals_covered_by == ""


def test_an_old_sentence_is_offered_as_the_notes_and_kept_when_saved(client, tenant):
    gig = make_gig(tenant=tenant, gig_fields={"meals": "3 repas chauds", "lodging": "2 chambres"})

    form = client.get(_complete_url(gig)).context["forms"]["gig"]
    assert form.initial["meals_notes"] == "3 repas chauds"
    assert form.initial["lodging_notes"] == "2 chambres"
    client.post(
        _complete_url(gig),
        {"gig-meals_notes": "3 repas chauds", "gig-lodging_notes": "2 chambres"},
    )

    gig.refresh_from_db()
    assert (gig.meals, gig.lodging) == ("3 repas chauds", "2 chambres")


def test_the_longest_possible_sentence_always_fits_the_field(client, tenant):
    gig = make_gig(tenant=tenant)

    response = client.post(
        _complete_url(gig),
        {
            "gig-meals_covered_by": "shared",
            "gig-meals_count": "30000",
            "gig-meals_notes": "x" * 150,
            "gig-lodging_covered_by": "shared",
            "gig-lodging_nights": "30000",
            "gig-lodging_notes": "y" * 150,
        },
    )

    assert response.status_code == 302
    gig.refresh_from_db()
    assert len(gig.meals) <= 255 and len(gig.lodging) <= 255


def test_an_unknown_party_is_refused(client, tenant):
    gig = make_gig(tenant=tenant)

    response = client.post(_complete_url(gig), {"gig-meals_covered_by": "the-moon"})

    assert response.status_code == 200
    gig.refresh_from_db()
    assert gig.meals_covered_by == ""


def test_the_fields_are_in_the_budget_block(client, tenant):
    gig = make_gig(tenant=tenant)

    content = client.get(_complete_url(gig)).content.decode()

    budget, roadmap = content.index('id="block-budget"'), content.index('id="block-roadmap"')
    for name in ("meals_covered_by", "meals_count", "lodging_covered_by", "lodging_nights"):
        assert budget < content.index(f'name="gig-{name}"') < roadmap


def test_the_contract_prints_the_composed_sentences(tenant):
    gig = make_gig(
        tenant=tenant,
        gig_fields={
            "meals": "À la charge de l'Organisateur : 8 repas",
            "lodging": "À la charge du Producteur : 2 nuits",
        },
    )

    html = render_to_string("documents/contracts/contract.html", build_contract_context(gig))

    text = _text(html)
    assert "À la charge de l'Organisateur : 8 repas" in text
    assert "À la charge du Producteur : 2 nuits" in text


# --- the program of the roadmap (FDR-04) ---------------------------------------------------------


@pytest.fixture
def roadmap(tenant):
    gig = make_gig(tenant=tenant)
    return RoadmapFactory(gig=gig)


def test_meals_and_arrivals_with_a_time_join_the_program_in_order(roadmap):
    RoadmapSlotFactory(roadmap=roadmap, kind="soundcheck", time=T(16, 0))
    RoadmapSlotFactory(roadmap=roadmap, kind="performance", time=T(21, 0), label="Concert")
    MealFactory(roadmap=roadmap, place="Chez Paul", time=T(19, 0))
    LodgingFactory(roadmap=roadmap, name="Hôtel des Arts", arrival_time=T(23, 30))

    program = build_program(roadmap)

    assert [(item.time, item.kind) for item in program] == [
        (T(16, 0), "soundcheck"),
        (T(19, 0), "meal"),
        (T(21, 0), "performance"),
        (T(23, 30), "lodging"),
    ]
    assert program[1].label == "Repas — Chez Paul"
    assert program[3].label == "Arrivée à l’hébergement — Hôtel des Arts"


def test_a_meal_or_a_lodging_without_a_time_is_not_in_the_program(roadmap):
    MealFactory(roadmap=roadmap, place="Chez Paul", time=None)
    LodgingFactory(roadmap=roadmap, name="Hôtel", arrival_time=None)

    assert build_program(roadmap) == []


def test_a_meal_already_planned_as_a_slot_is_not_repeated(roadmap):
    RoadmapSlotFactory(roadmap=roadmap, kind="meal", time=T(19, 0), label="Dîner")
    MealFactory(roadmap=roadmap, place="Chez Paul", time=T(19, 0))
    MealFactory(roadmap=roadmap, place="Autre", time=T(20, 0))

    labels = [item.label for item in build_program(roadmap)]

    assert labels == ["Dîner", "Repas — Autre"]


def test_a_slot_keeps_its_name_or_its_kind(roadmap):
    RoadmapSlotFactory(roadmap=roadmap, kind="arrival", time=T(14, 0), label="")
    RoadmapSlotFactory(
        roadmap=roadmap, kind="other", time=T(15, 0), label="Interview", note="radio"
    )

    program = build_program(roadmap)

    assert program[0].label == "Arrivée" and program[1].label == "Interview"
    assert program[1].note == "radio"


def test_the_public_page_and_the_pdf_show_the_meal_in_the_program(client, roadmap):
    MealFactory(roadmap=roadmap, place="Chez Paul", time=T(19, 0))
    publish(roadmap)

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()
    pdf_html = render_to_string("roadmaps/roadmap_pdf.html", public_context(roadmap))

    for content in (page, pdf_html):
        text = _text(content)
        assert text.index("Programme de la journée") < text.index("Repas — Chez Paul")


def test_the_roadmap_says_who_takes_meals_and_lodging_in_charge(client, roadmap):
    gig = roadmap.gig
    gig.meals_covered_by, gig.meals_count = "organiser", 8
    gig.lodging_covered_by, gig.lodging_nights = "producer", 2
    gig.save()
    publish(roadmap)

    page = _text(client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode())
    pdf = _text(render_to_string("roadmaps/roadmap_pdf.html", public_context(roadmap)))

    for text in (page, pdf):
        assert "Pris en charge par l'organisateur · 8 repas" in text
        assert "Pris en charge par le producteur · 2 nuits" in text


def test_the_roadmap_never_shows_the_free_text_or_the_contract_sentence(client, roadmap):
    gig = roadmap.gig
    gig.meals_covered_by = "shared"
    gig.meals_notes = "NOTES-SECRETES 500 euros chacun"
    gig.meals = "Pris en charge à frais partagés. NOTES-SECRETES 500 euros chacun"
    gig.save()
    publish(roadmap)

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()
    pdf = render_to_string("roadmaps/roadmap_pdf.html", public_context(roadmap))

    assert "NOTES-SECRETES" not in page and "NOTES-SECRETES" not in pdf
    assert "frais partagés" in page


def test_a_date_where_nobody_pays_says_nothing_on_the_roadmap(client, roadmap):
    gig = roadmap.gig
    gig.meals_covered_by = "none"
    gig.save()

    assert public_context(roadmap)["meals_cover"] == ""


def test_the_program_of_a_link_only_has_the_meals_of_its_own_date(client, roadmap):
    other = RoadmapFactory(gig=make_gig(tenant=TenantFactory(name="Autre")))
    MealFactory(roadmap=other, place="CHEZ-UN-AUTRE", time=T(19, 0))
    MealFactory(roadmap=roadmap, place="Chez Paul", time=T(19, 0))
    publish(roadmap)

    page = client.get(reverse("roadmap-public", args=[roadmap.token])).content.decode()

    assert "Chez Paul" in page and "CHEZ-UN-AUTRE" not in page
