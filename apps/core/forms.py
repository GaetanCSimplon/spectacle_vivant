from django import forms
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .addresses import department_from_postal_code, normalize_postal_code


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
