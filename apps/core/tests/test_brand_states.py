"""States and icons follow the charter: green = validated, amber = to watch, red = late or error,
grey = cancelled; coral only for the action; outline icons (docs/marque/charte-graphique.md)."""

import datetime
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.finance.tests.helpers import TENANT_FIELDS, issued_invoice, make_gig
from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db

ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = ROOT / "templates"
TODAY = timezone.localdate()


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _badge(status):
    gig = SimpleNamespace(status=status, get_status_display=lambda: status.title())
    return render_to_string("gigs/_status_badge.html", {"gig": gig})


@pytest.mark.parametrize(
    ("status", "css"),
    [
        ("option", "pill-warn"),
        ("confirmed", "pill-good"),
        ("signed", "pill-good-strong"),
        ("cancelled", "pill-neutral"),
    ],
)
def test_a_gig_status_has_the_charter_colour_and_always_its_label(status, css):
    html = _badge(status)

    assert css in html
    assert status.title() in html
    assert "blue" not in html  # blue is no longer a status colour


def test_confirmed_and_signed_stay_apart_without_colour():
    assert "pill-good-strong" not in _badge("confirmed")
    assert "pill-good " in _badge("confirmed") or 'pill-good"' in _badge("confirmed")


@pytest.mark.parametrize(
    ("status", "css"),
    [
        ("option", "bg-amber-500"),
        ("confirmed", "bg-green-500"),
        ("signed", "bg-green-700"),
        ("cancelled", "bg-gray-400"),
    ],
)
def test_the_calendar_dots_use_the_same_colours_with_a_text_label(status, css):
    gig = SimpleNamespace(status=status, get_status_display=lambda: status.title())

    html = render_to_string("gigs/_status_dot.html", {"gig": gig})

    assert css in html and 'class="sr-only"' in html


def test_the_calendar_legend_matches_the_dots(client):
    client.force_login(MembershipFactory().user)

    content = client.get(reverse("gigs:calendar")).content.decode()
    legend = content.split("Légende")[1].split("</ul>")[0]

    assert "bg-amber-500" in legend and "bg-green-500" in legend and "bg-green-700" in legend
    assert "bg-blue-600" not in legend


def test_the_bord_table_pills_follow_the_charter(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    tenant = membership.tenant
    pending = make_gig(tenant=tenant, gig_fields={"status": Gig.Status.OPTION})
    cancelled = make_gig(tenant=tenant, gig_fields={"status": Gig.Status.CANCELLED})
    assert pending.pk != cancelled.pk

    content = client.get(reverse("tenants:profile")).content.decode()
    table = content.split('id="operations"')[1].split('id="depenses"')[0]

    assert "pill pill-warn" in table and "En attente" in table
    assert "pill pill-neutral" in table and "Annulé" in table
    assert "pill pill-bad" not in table  # red is for late invoices, not for "pending"


def test_late_invoices_stay_red(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    gig = make_gig(tenant=membership.tenant, gig_fields={"status": Gig.Status.SIGNED})
    invoice = issued_invoice(gig)
    type(invoice).objects.filter(pk=invoice.pk).update(due_date=TODAY - datetime.timedelta(days=3))

    content = client.get(reverse("tenants:profile")).content.decode()

    assert "pill pill-bad" in content and "en retard" in content


def test_document_and_payment_badges_use_the_pills(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    gig = make_gig(tenant=membership.tenant, gig_fields={"status": Gig.Status.SIGNED})
    invoice = issued_invoice(gig)

    detail = client.get(
        reverse("documents:document-detail", args=[gig.pk, "factures", invoice.pk])
    ).content.decode()
    finance = client.get(reverse("finance:page", args=[gig.pk])).content.decode()

    assert re.search(r'class="pill [^"]*pill-good', detail)  # issued
    assert re.search(r'class="pill [^"]*pill-warn', finance) and "Reste" in finance  # to collect
    assert "bg-green-100" not in detail + finance and "bg-amber-100" not in detail + finance


def test_the_chart_keeps_coral_for_the_action_and_draws_expenses_in_grey(client):
    membership = MembershipFactory(**{f"tenant__{k}": v for k, v in TENANT_FIELDS.items()})
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant, status=Gig.Status.SIGNED)
    from apps.finance.factories import ExpenseFactory

    ExpenseFactory(gig=gig, amount="80.00", date=TODAY)

    content = client.get(reverse("tenants:profile")).content.decode()
    chart = content.split('id="bord-chart"')[1].split('id="bord-upcoming"')[0]
    categories = content.split('id="depenses"')[1]

    assert "fill-chart-revenue" in chart and "fill-chart-expense" in chart
    assert "bg-chart-expense" in chart and "bg-chart-revenue" in categories
    assert "coral" not in chart + categories


def test_no_template_uses_coral_directly():
    """Coral belongs to the main action (`btn-primary`) and to the active-page bar in the CSS."""
    offenders = [
        str(path.relative_to(ROOT))
        for path in TEMPLATES.rglob("*.html")
        if "coral" in path.read_text(errors="ignore")
    ]

    assert offenders == []


def test_no_filled_icon_is_left_and_the_icon_partial_is_outline():
    for path in TEMPLATES.rglob("*.html"):
        text = path.read_text(errors="ignore")
        assert not re.search(r'<svg[^>]*fill="currentColor"', text), path.name
    icon = (TEMPLATES / "components/_icon.html").read_text()
    assert 'fill="none"' in icon and 'stroke="currentColor"' in icon
    assert 'stroke-linecap="round"' in icon
    width = float(re.search(r'stroke-width="([0-9.]+)"', icon).group(1))
    assert 1.5 <= width <= 2


def test_the_icons_are_used_where_the_filled_ones_were(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    gig = GigFactory(tenant=membership.tenant)

    list_page = client.get(reverse("gigs:list")).content.decode()
    detail = client.get(reverse("gigs:detail", args=[gig.pk])).content.decode()
    bord = client.get(reverse("tenants:profile")).content.decode()

    assert 'stroke-width="1.75"' in list_page  # the pencils
    assert 'stroke-width="1.75"' in detail  # the checklist button
    assert 'stroke-width="1.75"' in bord  # the gear of "Informations de la structure"


def test_every_status_pill_carries_an_icon_as_well_as_a_word():
    """V06: tick = done, clock = to follow, alert = to complete or problem (CSS masks)."""
    css = (ROOT / "css/source.css").read_text()

    for pill in ("pill-good", "pill-warn", "pill-bad"):
        assert f".{pill}::before" in css
        assert re.search(rf"\.{pill}[^{{]*\{{\s*--pill-icon: url\(", css)
    assert "mask: var(--pill-icon)" in css


def test_a_refused_field_and_a_disabled_or_loading_button_have_their_own_look():
    css = (ROOT / "css/source.css").read_text()

    assert 'input[aria-invalid="true"]' in css
    assert ".btn.htmx-request" in css and ".btn:disabled" in css


def test_the_dashboard_summaries_are_colour_blocks_with_readable_text():
    """V06: summaries are solid blocks; their text colour is forced outside the CSS layers
    (Tailwind utilities would otherwise leave grey text on the navy block)."""
    css = (ROOT / "css/source.css").read_text()
    results = (TEMPLATES / "tenants/_bord_results.html").read_text()

    for block in ("card-navy", "card-ocean", "card-regie", "card-accent"):
        assert f".{block} {{" in css
        assert block in results
    for block in ("card-info", "card-cream"):
        assert f".{block} {{" in css
    unlayered = css.split("\n}\n\n/*\n * Outside any layer")[1]
    assert ".text-stone-600" in unlayered and "color: inherit" in unlayered


def test_a_very_long_word_never_pushes_a_page_wider_than_the_screen():
    """Recette V06: titles and paragraphs break anywhere (a 100-character name, a long URL)."""
    css = (ROOT / "css/source.css").read_text()

    for selector in ("h1,\n  h2,\n  h3 {", "  p {"):
        block = css.split(selector)[1].split("}")[0]
        assert "wrap-anywhere" in block, selector
    assert "button.underline {" in css  # a link-like button keeps a comfortable target


def test_links_in_a_text_are_underlined_and_a_cancelled_list_is_not_faded():
    """A link must not rely on its colour (1.5:1 against navy text); opacity breaks contrast."""
    for path in TEMPLATES.rglob("*.html"):
        for tag in re.findall(r"<a [^>]*>", path.read_text(errors="ignore")):
            assert "text-blue-600" not in tag, f"{path.name}: {tag[:80]}"
    gig_results = (TEMPLATES / "gigs/_gig_results.html").read_text()
    assert "opacity-" not in gig_results


def test_the_desktop_navigation_is_navy_with_the_white_logo_and_a_coral_current_page(client):
    """Charter v1.0: navy navigation, coral selection; the white logo (the dark one vanishes)."""
    client.force_login(MembershipFactory().user)
    css = (ROOT / "css/source.css").read_text()

    content = client.get(reverse("home")).content.decode()
    sidebar = content.split("<aside")[1].split("</aside>")[0]

    assert "brand/logo-white.svg" in sidebar and "brand/logo.svg" not in sidebar
    assert "bg-white" not in sidebar.split("<nav")[0]
    block = css.split('.sidebar .nav-link[aria-current="true"] {')[1].split("}")[0]
    assert "var(--bord-brand-coral)" in block
    assert "brand/logo.svg" in content.split("</aside>")[1]  # the top bar stays white


def test_the_information_block_is_cream_not_ocean_and_the_light_blue_is_a_discreet_context():
    css = (ROOT / "css/source.css").read_text()

    ocean = css.split("  .card-info {")[1].split("}")[0]
    context = css.split("  .card-context {")[1].split("}")[0]

    assert "var(--bord-info-bg)" in ocean and "var(--bord-text)" in ocean
    assert "--bord-info-bg: var(--bord-brand-cream)" in css  # ocean = Social volet only (v1.3)
    assert "var(--bord-context-bg)" in context and "var(--bord-text)" in context


def test_the_focus_ring_is_ocean_and_turns_white_or_navy_on_a_solid_block():
    css = (ROOT / "css/source.css").read_text()

    assert "outline: 3px solid var(--bord-focus)" in css
    assert ".sidebar :focus-visible" in css and "outline-color: var(--bord-surface)" in css
    assert ".card-accent :focus-visible" in css and "outline-color: var(--bord-text)" in css


def test_no_blurred_shadow_is_left_on_the_interface():
    """Charter v1.0: no blurred decorative shadow (menu, dialog and floating button included)."""
    leftovers = [
        path.name
        for path in TEMPLATES.rglob("*.html")
        if re.search(r"\bshadow-(sm|md|lg|xl|2xl)\b", path.read_text(errors="ignore"))
    ]

    assert leftovers == []


def test_help_bubbles_stay_inside_a_phone_screen():
    """Audit axe-core 2026-11-10: the 16 rem bubble pushed the page wider than 375 px."""
    css = (ROOT / "css" / "source.css").read_text()
    block = css[css.index("  .tip-body {") :].split("}")[0]
    assert "max-sm:fixed" in block and "max-sm:inset-x-4" in block
