"""The brand colours of css/source.css stay readable (charter, docs/marque/charte-graphique.md).

The tokens are read from the `:root` block of the stylesheet, so changing a colour there that
breaks a pair fails this test. Text needs 4.5:1; the border of a form field, the focus ring and
a chart series need 3:1 (WCAG 2.1).
"""

import re
from pathlib import Path

import pytest

CSS = (Path(__file__).resolve().parents[3] / "css/source.css").read_text()
ROOT_BLOCK = re.search(r":root \{(.*?)\n\}", CSS, re.S).group(1)
TOKENS = dict(
    re.findall(r"--bord-([a-z-]+):\s*(#[0-9a-fA-F]{6}|var\(--bord-[a-z-]+\));", ROOT_BLOCK)
)
SCALES = {
    f"{name}-{step}": value
    for name, step, value in re.findall(r"--color-([a-z]+)-(\d+):\s*(#[0-9a-fA-F]{6});", CSS)
}


def _luminance(hex_color):
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first, second):
    light, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


# (foreground token, background token, minimum ratio)
TEXT_PAIRS = [
    ("text", "bg", 4.5),
    ("text", "surface", 4.5),
    ("text-muted", "bg", 4.5),
    ("text-muted", "surface", 4.5),
    ("surface", "brand-navy", 4.5),
    ("text", "info-bg", 4.5),
    ("brand-coral", "brand-navy", 4.5),
    ("text", "brand-cream", 4.5),
    ("text-muted", "brand-cream", 4.5),
    ("text", "context-bg", 4.5),
    ("promoter-text", "promoter-bg", 4.5),
    ("venue-text", "venue-bg", 4.5),
    ("contact-text", "contact-bg", 4.5),
    ("text-muted", "context-bg", 4.5),
    ("surface", "brand-ocean", 4.5),
    ("brand-ocean", "surface", 4.5),
    ("action-text", "action-bg", 4.5),
    ("action-text", "action-bg-hover", 4.5),
    ("success-text", "success-bg", 4.5),
    ("success-text", "surface", 4.5),
    ("warning-text", "warning-bg", 4.5),
    ("warning-text", "surface", 4.5),
    ("danger-text", "danger-bg", 4.5),
    ("danger-text", "surface", 4.5),
    ("control-border", "surface", 3.0),
    ("control-border", "bg", 3.0),
    ("focus", "bg", 3.0),
    ("chart-revenue", "surface", 3.0),
    ("chart-expense", "surface", 3.0),
    ("chart-revenue", "chart-expense", 1.2),
]


def _color(name):
    value = TOKENS[name]
    while value.startswith("var("):  # `--bord-text: var(--bord-brand-navy)`
        value = TOKENS[value[len("var(--bord-") : -1]]
    return value


@pytest.mark.parametrize(("foreground", "background", "minimum"), TEXT_PAIRS)
def test_the_token_pair_is_readable(foreground, background, minimum):
    ratio = contrast(_color(foreground), _color(background))

    assert ratio >= minimum, f"{foreground} on {background}: {ratio:.2f}:1 (needs {minimum}:1)"


def test_all_the_charter_tokens_are_present():
    for name in (
        "brand-navy",
        "brand-coral",
        "brand-cream",
        "brand-ocean",
        "context-bg",
        "brand-gray",
        "brand-green",
        "brand-amber",
        "brand-plum",
        "bg",
        "surface",
        "info-bg",
        "border",
        "control-border",
    ):
        assert name in TOKENS


def test_white_text_is_never_put_on_coral():
    """White on the coral action is 2.8:1: the action text is Bleu Nuit."""
    assert contrast("#ffffff", _color("brand-coral")) < 4.5
    assert _color("action-text") == _color("brand-navy")


@pytest.mark.parametrize("scale", ["gray", "stone"])
def test_the_text_greys_of_the_templates_are_readable(scale):
    """`text-gray-500` / `text-stone-500` and darker are used for secondary text everywhere."""
    for step in (500, 600, 700, 800, 900):
        for background in ("#ffffff", _color("bg")):
            ratio = contrast(SCALES[f"{scale}-{step}"], background)
            assert ratio >= 4.5, f"{scale}-{step} on {background}: {ratio:.2f}"


@pytest.mark.parametrize("scale", ["green", "amber", "red"])
def test_the_dark_tones_of_the_state_scales_are_readable_as_text(scale):
    for step in (700, 800, 900):
        ratio = contrast(SCALES[f"{scale}-{step}"], "#ffffff")
        assert ratio >= 4.5, f"{scale}-{step}: {ratio:.2f}"


def test_the_charter_v1_values_are_adopted():
    """Charter of 2026-10-26: white page, coral #FF695B, ocean #007299, secondary text #465A6C."""
    assert _color("bg").lower() == "#ffffff"
    assert _color("brand-coral").lower() == "#ff695b"
    assert _color("brand-ocean").lower() == "#007299"
    assert _color("context-bg").lower() == "#e2f1f6"
    assert _color("text-muted").lower() == "#465a6c"
    assert _color("border").lower() == "#c4cfda"


def test_a_light_separator_never_identifies_a_field_alone():
    """The charter's own #C4CFDA is for cards and lines; a field keeps a border that reaches 3:1."""
    assert contrast(_color("border"), _color("surface")) < 3.0
    assert contrast(_color("control-border"), _color("surface")) >= 3.0


def test_the_navy_scale_is_the_brand_navy_at_700():
    assert SCALES["blue-700"].lower() == _color("brand-navy").lower()


def test_the_solid_green_pill_keeps_its_white_text_readable():
    """`pill-good-strong` (a signed date): white on the dark success green."""
    assert contrast("#ffffff", _color("success-text")) >= 4.5


def test_a_button_in_a_colour_block_keeps_its_own_colours():
    """A white button inside a navy card must not inherit the card's white text."""
    rules = CSS.split("Outside any layer on purpose", 1)[1]
    assert "a:not(.btn)" in rules
    assert not re.search(r"\.card-regie\)\s+a\s*\{", rules)
