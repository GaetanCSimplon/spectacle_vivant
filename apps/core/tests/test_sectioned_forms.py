"""The long forms are laid out in titled blocks: no field may be lost on the way."""

import pytest
from django.urls import reverse

from apps.addressbook.forms import PromoterForm, VenueForm
from apps.catalog.forms import ShowForm
from apps.core.forms import SectionedFormMixin
from apps.tenants.factories import MembershipFactory
from apps.tenants.forms import PersonForm, TenantProfileForm
from apps.tenants.models import Tenant

pytestmark = pytest.mark.django_db

PAGES = [
    ("addressbook:promoter-create", PromoterForm, {}),
    ("addressbook:venue-create", VenueForm, {}),
    ("catalog:show-create", ShowForm, {"tenant": None}),
    ("tenants:person-create", PersonForm, {"tenant": None, "is_owner": True}),
]


@pytest.mark.parametrize(("_url", "form_class", "kwargs"), PAGES)
def test_every_field_belongs_to_a_titled_block(_url, form_class, kwargs):
    tenant = Tenant.objects.create(name="T")
    kwargs = {key: tenant if key == "tenant" else value for key, value in kwargs.items()}
    form = form_class(**kwargs)

    assert all(block["title"] for block in form.sections), "a field is missing from `layout`"
    shown = {field.name for block in form.sections for field in block["fields"]}
    expected = set(form.fields) - set(getattr(form, "NEW_MEMBER_FIELDS", []))
    assert shown == expected


def test_the_structure_form_has_every_field_in_a_block():
    form = TenantProfileForm()

    assert all(block["title"] for block in form.sections)
    assert {f.name for b in form.sections for f in b["fields"]} == set(form.fields)


@pytest.mark.parametrize(("url_name", "_form", "_kwargs"), PAGES)
def test_the_page_renders_every_field(client, url_name, _form, _kwargs):
    client.force_login(MembershipFactory(role="owner").user)

    page = client.get(reverse(url_name)).content.decode()

    assert page.count("<fieldset") >= 2 and 'class="form-grid' in page
    assert 'name="csrfmiddlewaretoken"' in page


def test_a_member_without_the_private_fields_gets_no_empty_block(client):
    tenant = Tenant.objects.create(name="T")
    form = PersonForm(tenant=tenant, is_owner=False)

    titles = [block["title"] for block in form.sections]

    assert not any("privées" in title for title in titles)
    assert "La personne" in titles


def test_the_mixin_puts_unlisted_fields_in_a_last_untitled_block():
    class Demo(SectionedFormMixin):
        layout = [("A", ["a"])]
        fields = {"a": 1, "b": 2}

        def __getitem__(self, name):
            return name

    blocks = Demo().sections

    assert blocks == [{"title": "A", "fields": ["a"]}, {"title": "", "fields": ["b"]}]
