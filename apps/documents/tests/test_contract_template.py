import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

from .. import services
from ..models import Contract, ContractTemplate
from ..services import build_contract_context, generate_contract_pdf

pytestmark = pytest.mark.django_db


@pytest.fixture
def two_models():
    """Several models are offered."""


@pytest.fixture
def one_model(monkeypatch):
    for model in (ContractTemplate.MODEL_2, ContractTemplate.MODEL_3):
        monkeypatch.delitem(services.CONTRACT_TEMPLATES, model)


def _member_gig(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return GigFactory(tenant=membership.tenant)


def test_a_new_contract_and_its_first_version_use_model_1():
    contract = generate_contract_pdf(GigFactory())

    assert contract.template == ContractTemplate.MODEL_1
    assert contract.latest_version.template == ContractTemplate.MODEL_1


def test_model_1_carries_no_draft_banner():
    html = render_to_string(
        "documents/contracts/model_1.html", build_contract_context(GigFactory())
    )

    assert "non relu" not in html
    assert "PROJET" not in html


def test_only_models_with_a_template_file_are_offered():
    assert services.available_contract_templates() == [
        ("model_1", "Modèle 1"),
        ("model_2", "Modèle 2"),
        ("model_3", "Modèle 3"),
    ]


def test_regenerating_with_another_model_switches_the_contract_and_keeps_old_versions(two_models):
    gig = GigFactory()
    generate_contract_pdf(gig)

    contract = generate_contract_pdf(gig, template=ContractTemplate.MODEL_2)

    assert contract.template == ContractTemplate.MODEL_2
    assert [v.template for v in contract.versions.all()] == ["model_2", "model_1"]


def test_regenerating_without_a_choice_keeps_the_current_model(two_models):
    gig = GigFactory()
    generate_contract_pdf(gig, template=ContractTemplate.MODEL_2)

    contract = generate_contract_pdf(gig)

    assert contract.template == ContractTemplate.MODEL_2
    assert contract.latest_version.template == ContractTemplate.MODEL_2


def test_a_model_without_template_file_is_refused():
    with pytest.raises(ValueError):
        generate_contract_pdf(GigFactory(), template=ContractTemplate.MODEL_4)

    assert not Contract.objects.exists()


def test_a_signed_contract_keeps_its_model(two_models):
    gig = GigFactory()
    contract = generate_contract_pdf(gig)
    Contract.objects.filter(pk=contract.pk).update(status=Contract.Status.SIGNED)

    contract = generate_contract_pdf(gig, template=ContractTemplate.MODEL_2)

    assert contract.template == ContractTemplate.MODEL_1
    assert contract.versions.count() == 1


def test_the_generate_view_applies_the_chosen_model(client, two_models):
    gig = _member_gig(client)

    response = client.post(
        reverse("documents:contract-generate", args=[gig.pk]), {"template": "model_2"}
    )

    assert response.status_code == 302
    assert gig.contract.template == ContractTemplate.MODEL_2


def test_the_generate_view_refuses_an_unknown_model(client):
    gig = _member_gig(client)

    response = client.post(
        reverse("documents:contract-generate", args=[gig.pk]), {"template": "model_4"}
    )

    assert response.status_code == 302
    assert not Contract.objects.exists()


def test_the_generate_view_without_a_choice_uses_the_default(client):
    gig = _member_gig(client)

    client.post(reverse("documents:contract-generate", args=[gig.pk]))

    assert gig.contract.template == ContractTemplate.MODEL_1


def test_the_preview_uses_the_chosen_model_and_refuses_an_unknown_one(client, two_models):
    gig = _member_gig(client)
    url = reverse("documents:contract-preview", args=[gig.pk])

    ok = client.get(url, {"template": "model_2"})
    bad = client.get(url, {"template": "model_4"})

    assert ok.status_code == 200
    assert ok["Content-Type"] == "application/pdf"
    assert bad.status_code == 302


def test_the_selector_is_hidden_with_a_single_model(client, one_model):
    gig = _member_gig(client)

    response = client.get(reverse("documents:contract-history", args=[gig.pk]))

    assert b'name="template"' not in response.content


def test_the_selector_lists_the_models_and_preselects_the_current_one(client, two_models):
    gig = _member_gig(client)
    generate_contract_pdf(gig, template=ContractTemplate.MODEL_2)

    html = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()

    assert 'name="template"' in html
    assert "Modèle 1 (par défaut)" in html
    assert '<option value="model_2" selected>' in html


def test_no_selector_once_the_contract_is_signed(client, two_models):
    gig = _member_gig(client)
    contract = generate_contract_pdf(gig)
    Contract.objects.filter(pk=contract.pk).update(status=Contract.Status.SIGNED)

    html = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()

    assert 'name="template"' not in html
