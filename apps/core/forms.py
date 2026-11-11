from django import forms
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .addresses import department_from_postal_code, normalize_postal_code


class SectionedFormMixin:
    """A long form laid out in titled blocks (two columns of fields on a PC screen).

    `layout` is `[(title, [field names])]`. A field the form no longer has (the private ones of
    the team card for a simple member) is skipped, and a block left empty disappears. Any field
    missing from `layout` is still shown, in a last untitled block, so one can never be lost.
    """

    layout = []

    @property
    def sections(self):
        placed = {name for _title, names in self.layout for name in names}
        blocks = [
            {"title": title, "fields": [self[name] for name in names if name in self.fields]}
            for title, names in self.layout
        ]
        leftovers = [self[name] for name in self.fields if name not in placed]
        if leftovers:
            blocks.append({"title": "", "fields": leftovers})
        return [block for block in blocks if block["fields"]]


class CityInput(forms.TextInput):
    """The city field: it offers the communes of the postal code (a `<datalist>` refreshed by HTMX)
    and fills itself, when empty, if the postal code points to a single commune (ORG-02)."""

    def render(self, name, value, attrs=None, renderer=None):
        field = super().render(name, value, attrs, renderer)
        return mark_safe(f'{field}<datalist id="city-options"></datalist>')  # noqa: S308


class AddressModelForm(forms.ModelForm):
    """Base of the forms of a model with `AddressMixin`: tidy postal code, guess the department.

    The postal code is declared here (not taken from the model) so that "34 000" is accepted
    and cleaned to 34000 before the model checks it has 5 digits.
    """

    postal_code = forms.CharField(
        label=_("Code postal"),
        required=False,
        max_length=10,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "postal-code"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "postal_code" in self.fields and "city" in self.fields:
            self.fields["postal_code"].widget.attrs.update(
                {
                    "hx-get": reverse_lazy("lookup-communes"),
                    "hx-trigger": "input[this.value.length >= 5] changed delay:400ms",
                    "hx-target": "#city-options",
                    "hx-swap": "outerHTML",
                }
            )
            self.fields["city"].widget = CityInput(
                attrs={
                    "list": "city-options",
                    "autocomplete": "address-level2",
                    "x-data": "{}",
                    "@commune-found.window": "if (!$el.value) $el.value = $event.detail.name",
                }
            )

    def clean_postal_code(self):
        return normalize_postal_code(self.cleaned_data["postal_code"])

    def clean_city(self):
        return " ".join(self.cleaned_data["city"].split())

    def clean(self):
        cleaned = super().clean()
        # Left empty, the department is deduced from the postal code when it is clear.
        if cleaned.get("postal_code") and not cleaned.get("department"):
            cleaned["department"] = department_from_postal_code(cleaned["postal_code"])
        return cleaned


class MultiSelectDropdown(forms.CheckboxSelectMultiple):
    """A drop-down holding one checkbox per choice: pick one or several without a long list.

    Plain HTML (`<details>`), so it works without JavaScript; Alpine only keeps the summary
    line ("Jazz, Danse") up to date while ticking.
    """

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)["widget"]
        options = [
            option for _group, group_options, _i in context["optgroups"] for option in group_options
        ]
        context["options"] = options
        context["summary"] = ", ".join(str(o["label"]) for o in options if o["selected"])
        return mark_safe(render_to_string("components/_multi_select.html", {"widget": context}))


class ContactForm(forms.Form):
    """The contact form of the presentation site: its content is only e-mailed, never stored."""

    name = forms.CharField(label=_("Votre nom"), max_length=100)
    email = forms.EmailField(label=_("Votre adresse e-mail"), max_length=254)
    message = forms.CharField(
        label=_("Votre message"),
        min_length=10,
        max_length=3000,
        widget=forms.Textarea(attrs={"rows": 6}),
    )
    # A trap for robots: a person never sees nor fills this field.
    website = forms.CharField(
        required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"})
    )

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())

    @property
    def is_spam(self):
        return bool(self.cleaned_data.get("website"))
