"""The brand colours of css/source.css stay readable (charter, docs/cadrage/13-charte-graphique.md).

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
    ("focus", "action-bg", 3.0),
    ("chart-muted", "surface", 3.0),
    ("brand-navy", "chart-muted", 3.0),
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
        "brand-offwhite",
        "brand-slate",
        "brand-green",
        "brand-amber",
        "brand-red",
        "surface",
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
        for background in ("#ffffff", _color("brand-offwhite")):
            ratio = contrast(SCALES[f"{scale}-{step}"], background)
            assert ratio >= 4.5, f"{scale}-{step} on {background}: {ratio:.2f}"


@pytest.mark.parametrize("scale", ["green", "amber", "red"])
def test_the_dark_tones_of_the_state_scales_are_readable_as_text(scale):
    for step in (700, 800, 900):
        ratio = contrast(SCALES[f"{scale}-{step}"], "#ffffff")
        assert ratio >= 4.5, f"{scale}-{step}: {ratio:.2f}"


def test_the_navy_scale_is_the_brand_navy_at_700():
    assert SCALES["blue-700"].lower() == _color("brand-navy").lower()
