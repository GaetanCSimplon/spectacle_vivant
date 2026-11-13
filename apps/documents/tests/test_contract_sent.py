import pytest
from django.urls import reverse

from apps.gigs.factories import GigFactory
from apps.gigs.models import Gig
from apps.tenants.factories import MembershipFactory

from ..services import (
    ContractSigningError,
    generate_contract_pdf,
    mark_contract_sent,
    mark_contract_signed,
    unmark_contract_sent,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _gig(tenant=None, generated=True):
    gig = GigFactory(status=Gig.Status.CONFIRMED, **({"tenant": tenant} if tenant else {}))
    if generated:
        generate_contract_pdf(gig)
    return gig


def _login(client, tenant=None):
    membership = MembershipFactory(**({"tenant": tenant} if tenant else {}))
    client.force_login(membership.user)
    return membership


def test_a_new_contract_is_not_sent():
    assert _gig().contract.sent_at is None


def test_marking_sent_records_the_date_and_unmarking_clears_it():
    gig = _gig()

    assert mark_contract_sent(gig).sent_at is not None
    assert unmark_contract_sent(gig).sent_at is None


def test_a_contract_that_was_never_generated_cannot_be_marked_sent():
    with pytest.raises(ContractSigningError):
        mark_contract_sent(_gig(generated=False))


def test_a_signed_contract_can_be_neither_marked_nor_unmarked():
    gig = _gig()
    mark_contract_signed(gig)

    with pytest.raises(ContractSigningError):
        mark_contract_sent(gig)
    with pytest.raises(ContractSigningError):
        unmark_contract_sent(gig)


def test_a_new_version_makes_the_contract_not_sent_again():
    gig = _gig()
    mark_contract_sent(gig)

    contract = generate_contract_pdf(gig)

    assert contract.sent_at is None


def test_the_page_offers_the_button_and_shows_the_date(client):
    membership = _login(client)
    gig = _gig(membership.tenant)
    url = reverse("documents:contract-history", args=[gig.pk])

    assert "Marquer comme envoyé" in client.get(url).content.decode()
    client.post(reverse("documents:contract-sent", args=[gig.pk, "envoye"]))
    content = client.get(url).content.decode()

    assert "Envoyé à l'organisateur le" in content and "Retirer la mention" in content
    client.post(reverse("documents:contract-sent", args=[gig.pk, "non-envoye"]))
    assert "Marquer comme envoyé" in client.get(url).content.decode()


def test_no_button_before_the_contract_is_generated(client):
    membership = _login(client)
    gig = _gig(membership.tenant, generated=False)

    content = client.get(reverse("documents:contract-history", args=[gig.pk])).content.decode()

    assert "Marquer comme envoyé" not in content


def test_the_sent_view_is_login_only_and_the_get_page_is_only_for_sending(client):
    gig = _gig()
    url = reverse("documents:contract-sent", args=[gig.pk, "envoye"])

    assert client.post(url).status_code == 302  # to the login page
    assert client.get(url).status_code == 302
    _login(client, gig.tenant)
    assert client.get(url).status_code == 200  # Radar's confirmation page
    back = client.get(reverse("documents:contract-sent", args=[gig.pk, "non-envoye"]))
    assert back.status_code == 302  # taking the mark back is a POST


def test_another_tenants_contract_is_a_404_and_stays_untouched(client):
    gig = _gig()
    _login(client)

    response = client.post(reverse("documents:contract-sent", args=[gig.pk, "envoye"]))

    assert response.status_code == 404
    gig.contract.refresh_from_db()
    assert gig.contract.sent_at is None
