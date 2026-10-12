"""The form an organiser fills in from a temporary link (F-16)."""

import datetime

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.core.tests.isolation_registry import mark_isolation_tested
from apps.finance import dashboard
from apps.tenants.factories import MembershipFactory

from .. import services
from ..factories import PromoterFactory
from ..models import Contact, PromoterInvitation

mark_isolation_tested(PromoterInvitation)

pytestmark = pytest.mark.django_db

ANSWER = {
    "billing_address": "1 place de la Mairie",
    "postal_code": "34 200",
    "city": "Sète",
    "siret": "213 400 000 000 19",
    "representative_name": "Hélène Roux",
    "representative_role": "Maire adjointe",
    "email": "culture@example.org",
}


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership


def _invitation(promoter, user=None):
    return services.create_invitation(promoter, user)


def _public(invitation):
    return reverse("promoter-form-public", args=[invitation.token])


def _answered(promoter, **answer):
    invitation = _invitation(promoter)
    form_data = {**ANSWER, **answer}
    from ..forms import PromoterPublicForm

    form = PromoterPublicForm(form_data)
    assert form.is_valid(), form.errors
    services.submit_response(invitation, form.cleaned_data)
    invitation.refresh_from_db()
    return invitation


# --- the link ---------------------------------------------------------------------------


def test_a_link_is_secret_random_and_valid_for_a_week():
    promoter = PromoterFactory()
    first, second = _invitation(promoter), _invitation(promoter)

    assert len(first.token) >= 43 and first.token != second.token
    assert first.expires_at - first.created_at == pytest.approx(
        datetime.timedelta(days=7), abs=datetime.timedelta(minutes=1)
    )


def test_status_follows_the_life_of_the_link():
    promoter = PromoterFactory()
    invitation = _invitation(promoter)
    assert invitation.status == PromoterInvitation.Status.ACTIVE

    invitation.expires_at = timezone.now() - datetime.timedelta(seconds=1)
    assert invitation.status == PromoterInvitation.Status.EXPIRED

    invitation.expires_at = timezone.now() + datetime.timedelta(days=1)
    invitation.revoked_at = timezone.now()
    assert invitation.status == PromoterInvitation.Status.REVOKED

    invitation.completed_at = timezone.now()
    assert invitation.status == PromoterInvitation.Status.ANSWERED
    invitation.reviewed_at = timezone.now()
    assert invitation.status == PromoterInvitation.Status.REVIEWED


def test_a_new_link_cancels_the_active_one_but_not_an_unreviewed_answer():
    promoter = PromoterFactory()
    old = _invitation(promoter)
    new = _invitation(promoter)
    old.refresh_from_db()
    assert old.status == PromoterInvitation.Status.REVOKED
    assert new.status == PromoterInvitation.Status.ACTIVE

    answered = _answered(promoter)
    _invitation(promoter)
    answered.refresh_from_db()
    assert answered.status == PromoterInvitation.Status.ANSWERED


# --- the user's side ----------------------------------------------------------------------


def test_the_user_creates_and_sees_the_link(client):
    membership = _login(client)
    promoter = PromoterFactory(tenant=membership.tenant)

    response = client.post(reverse("addressbook:promoter-invite", args=[promoter.pk]))

    invitation = PromoterInvitation.objects.get()
    assert response.url == reverse("addressbook:promoter-detail", args=[promoter.pk])
    assert invitation.created_by == membership.user and invitation.tenant == membership.tenant
    page = client.get(response.url).content.decode()
    assert f"http://testserver{_public(invitation)}" in page
    assert "Copier le lien" in page and "Annuler ce lien" in page


def test_the_user_can_cancel_the_link(client):
    membership = _login(client)
    promoter = PromoterFactory(tenant=membership.tenant)
    invitation = _invitation(promoter)

    client.post(reverse("addressbook:promoter-invite-revoke", args=[promoter.pk]))

    invitation.refresh_from_db()
    assert invitation.status == PromoterInvitation.Status.REVOKED
    assert client.get(_public(invitation)).status_code == 410


def test_invite_routes_are_post_only_and_need_a_login(client):
    promoter = PromoterFactory()
    for name in ("addressbook:promoter-invite", "addressbook:promoter-invite-revoke"):
        url = reverse(name, args=[promoter.pk])
        assert client.post(url).url.startswith(reverse("account_login"))
    membership = _login(client)
    own = PromoterFactory(tenant=membership.tenant)
    assert client.get(reverse("addressbook:promoter-invite", args=[own.pk])).status_code == 405


def test_another_tenant_cannot_invite_or_review(client):
    _login(client)
    foreign = PromoterFactory()
    answered = _answered(foreign)

    for name in ("addressbook:promoter-invite", "addressbook:promoter-invite-revoke"):
        assert client.post(reverse(name, args=[foreign.pk])).status_code == 404
    answer_url = reverse("addressbook:promoter-answer", args=[foreign.pk])
    assert client.get(answer_url).status_code == 404
    assert client.post(answer_url, {"fields": ["city"]}).status_code == 404
    answered.refresh_from_db()
    assert answered.status == PromoterInvitation.Status.ANSWERED
    assert PromoterInvitation.objects.filter(promoter=foreign).count() == 1


# --- the organiser's page ------------------------------------------------------------------


def test_the_public_page_needs_no_account_and_shows_nothing_of_the_structure():
    promoter = PromoterFactory(
        name="Mairie de Sète",
        notes="NOTE-SECRETE",
        siret="99999999999999",
        email="prive@example.org",
        tenant__name="Compagnie du Test",
        tenant__siret="12345678900012",
        tenant__address="ADRESSE-SECRETE",
    )
    invitation = _invitation(promoter)

    response = Client().get(_public(invitation))
    page = response.content.decode()

    assert response.status_code == 200
    assert "Compagnie du Test" in page and "Mairie de Sète" in page
    for secret in (
        "NOTE-SECRETE",
        "99999999999999",
        "prive@example.org",
        "ADRESSE-SECRETE",
        "12345678900012",
    ):
        assert secret not in page
    assert response["Cache-Control"] == "no-store"
    assert "noindex" in response["X-Robots-Tag"]
    assert response["Referrer-Policy"] == "no-referrer"


def test_an_unknown_token_is_a_plain_404():
    assert (
        Client().get(reverse("promoter-form-public", args=["pas-un-vrai-jeton"])).status_code == 404
    )
    assert (
        Client()
        .post(reverse("promoter-form-public", args=["pas-un-vrai-jeton"]), ANSWER)
        .status_code
        == 404
    )


def test_the_answer_is_stored_for_review_and_the_card_is_untouched():
    promoter = PromoterFactory(city="Ancienne ville", siret="")
    invitation = _invitation(promoter)

    response = Client().post(
        _public(invitation),
        {**ANSWER, "contact_name": "Julien Blanc", "contact_email": "julien@example.org"},
    )

    assert response.url == reverse("promoter-form-thanks")
    invitation.refresh_from_db()
    assert invitation.status == PromoterInvitation.Status.ANSWERED
    assert invitation.response["fields"]["postal_code"] == "34200"
    assert invitation.response["fields"]["siret"] == "21340000000019"
    assert invitation.response["fields"]["department"] == "34"  # deduced from the postal code
    assert invitation.response["contact"] == {"name": "Julien Blanc", "email": "julien@example.org"}
    promoter.refresh_from_db()
    assert (promoter.city, promoter.siret) == ("Ancienne ville", "")
    assert Contact.objects.count() == 0
    assert Client().get(reverse("promoter-form-thanks")).status_code == 200


def test_the_link_works_only_once():
    promoter = PromoterFactory()
    invitation = _invitation(promoter)
    client = Client()
    client.post(_public(invitation), ANSWER)

    second = client.post(_public(invitation), {"city": "Pirate"})
    again = client.get(_public(invitation))

    assert second.status_code == again.status_code == 410
    assert "n'est plus valable" in again.content.decode().replace("&#x27;", "'")
    invitation.refresh_from_db()
    assert invitation.response["fields"]["city"] == "Sète"


@pytest.mark.parametrize("state", ["expired", "revoked"])
def test_an_expired_or_cancelled_link_is_closed(state):
    invitation = _invitation(PromoterFactory())
    if state == "expired":
        invitation.expires_at = timezone.now() - datetime.timedelta(minutes=1)
    else:
        invitation.revoked_at = timezone.now()
    invitation.save()

    assert Client().get(_public(invitation)).status_code == 410
    assert Client().post(_public(invitation), ANSWER).status_code == 410
    invitation.refresh_from_db()
    assert invitation.response == {} and invitation.completed_at is None


@pytest.mark.parametrize(
    "bad",
    [
        {"siret": "123"},
        {"siret": "abcdefghijklmn"},
        {"postal_code": "3400"},
        {"email": "pas-un-mail"},
        {"contact_email": "x@example.org"},  # contact without a name
    ],
)
def test_bad_answers_are_refused_and_nothing_is_stored(bad):
    invitation = _invitation(PromoterFactory())

    response = Client().post(_public(invitation), {"city": "Sète", **bad})

    assert response.status_code == 200
    invitation.refresh_from_db()
    assert invitation.completed_at is None and invitation.response == {}


def test_an_empty_form_is_refused():
    invitation = _invitation(PromoterFactory())
    response = Client().post(_public(invitation), {})
    assert response.status_code == 200
    assert "au moins un champ" in response.content.decode()
    invitation.refresh_from_db()
    assert invitation.completed_at is None


def test_the_form_needs_the_csrf_token():
    invitation = _invitation(PromoterFactory())
    client = Client(enforce_csrf_checks=True)
    assert client.post(_public(invitation), ANSWER).status_code == 403
    invitation.refresh_from_db()
    assert invitation.completed_at is None


def test_a_link_only_reaches_its_own_organiser():
    first, second = PromoterFactory(), PromoterFactory()
    link_first, link_second = _invitation(first), _invitation(second)

    Client().post(_public(link_first), ANSWER)

    link_first.refresh_from_db(), link_second.refresh_from_db()
    assert link_first.status == PromoterInvitation.Status.ANSWERED
    assert link_second.status == PromoterInvitation.Status.ACTIVE


# --- reviewing and applying ---------------------------------------------------------------


def test_the_review_screen_compares_and_the_user_applies_the_checked_fields(client):
    membership = _login(client)
    promoter = PromoterFactory(
        tenant=membership.tenant, city="Montpellier", siret="", representative_name="Ancien"
    )
    _answered(promoter, contact_name="Julien Blanc", contact_role="Accueil")
    url = reverse("addressbook:promoter-answer", args=[promoter.pk])

    page = client.get(url).content.decode()
    assert "Montpellier" in page and "Sète" in page and "Actuellement vide" in page

    response = client.post(url, {"fields": ["city", "siret", "postal_code"], "contact": "1"})

    assert response.url == reverse("addressbook:promoter-detail", args=[promoter.pk])
    promoter.refresh_from_db()
    assert (promoter.city, promoter.siret, promoter.postal_code) == (
        "Sète",
        "21340000000019",
        "34200",
    )
    assert promoter.representative_name == "Ancien"  # not checked: untouched
    contact = Contact.objects.get()
    assert (contact.promoter, contact.name, contact.role) == (promoter, "Julien Blanc", "Accueil")
    invitation = PromoterInvitation.objects.get()
    assert invitation.status == PromoterInvitation.Status.REVIEWED and invitation.response == {}


def test_unchecked_everything_changes_nothing(client):
    membership = _login(client)
    promoter = PromoterFactory(tenant=membership.tenant, city="Montpellier")
    _answered(promoter, contact_name="Julien Blanc")

    client.post(reverse("addressbook:promoter-answer", args=[promoter.pk]), {})

    promoter.refresh_from_db()
    assert promoter.city == "Montpellier" and not Contact.objects.exists()
    assert PromoterInvitation.objects.get().response == {}


def test_ignoring_an_answer_applies_nothing(client):
    membership = _login(client)
    promoter = PromoterFactory(tenant=membership.tenant, city="Montpellier")
    _answered(promoter)

    client.post(
        reverse("addressbook:promoter-answer", args=[promoter.pk]),
        {"ignore": "1", "fields": ["city"]},
    )

    promoter.refresh_from_db()
    assert promoter.city == "Montpellier"
    assert PromoterInvitation.objects.get().status == PromoterInvitation.Status.REVIEWED


def test_only_known_fields_can_be_applied(client):
    membership = _login(client)
    promoter = PromoterFactory(tenant=membership.tenant, name="Mairie")
    _answered(promoter)

    client.post(
        reverse("addressbook:promoter-answer", args=[promoter.pk]),
        {"fields": ["name", "tenant", "follow_up", "city"]},
    )

    promoter.refresh_from_db()
    assert promoter.name == "Mairie" and promoter.city == "Sète"


def test_an_answer_cannot_be_applied_twice(client):
    membership = _login(client)
    promoter = PromoterFactory(tenant=membership.tenant)
    _answered(promoter)
    url = reverse("addressbook:promoter-answer", args=[promoter.pk])
    client.post(url, {"fields": ["city"], "contact": "1"})
    promoter.city = "Modifié après"
    promoter.save()

    response = client.post(url, {"fields": ["city"]})

    promoter.refresh_from_db()
    assert response.status_code == 302 and promoter.city == "Modifié après"


def test_what_the_organiser_typed_is_escaped(client):
    membership = _login(client)
    promoter = PromoterFactory(tenant=membership.tenant)
    _answered(promoter, representative_name="<script>alert(1)</script>")

    page = client.get(reverse("addressbook:promoter-answer", args=[promoter.pk])).content.decode()

    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_a_pending_answer_is_an_alert_on_the_home_page_until_reviewed(client):
    membership = _login(client)
    promoter = PromoterFactory(tenant=membership.tenant, name="Mairie de Sète")
    _answered(promoter)

    items = dashboard.alerts(membership.tenant, datetime.date.today())["items"]
    assert any("Mairie de Sète a répondu au formulaire" in a["text"] for a in items)
    assert items[0]["url"] == reverse("addressbook:promoter-answer", args=[promoter.pk])

    services.ignore_response(PromoterInvitation.objects.get())
    items = dashboard.alerts(membership.tenant, datetime.date.today())["items"]
    assert not any("a répondu" in a["text"] for a in items)


def test_other_tenants_answers_are_never_listed_in_the_alerts():
    mine = MembershipFactory().tenant
    _answered(PromoterFactory())
    assert dashboard.alerts(mine, datetime.date.today())["items"] == []
