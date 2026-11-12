import datetime

import pytest
from django.urls import reverse

from apps.addressbook.factories import PromoterFactory, VenueFactory
from apps.catalog.factories import ShowFactory
from apps.tenants.factories import MembershipFactory

from ..models import Gig

pytestmark = pytest.mark.django_db


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def test_wizard_show_step_requires_login(client):
    response = client.get(reverse("gigs:wizard-show"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_full_wizard_creates_a_gig(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)

    response = client.post(reverse("gigs:wizard-show"), {"mode": "existing", "show": show.pk})
    assert response.status_code == 302

    response = client.post(
        reverse("gigs:wizard-promoter"), {"mode": "existing", "promoter": promoter.pk}
    )
    assert response.status_code == 302

    response = client.post(reverse("gigs:wizard-venue"), {"mode": "existing", "venue": venue.pk})
    assert response.status_code == 302

    gig_date = datetime.date.today() + datetime.timedelta(days=10)
    response = client.post(
        reverse("gigs:wizard-details"),
        {"date": gig_date.isoformat(), "price": "800.00", "conditions": "Loge chauffée"},
    )
    assert response.status_code == 302

    response = client.get(reverse("gigs:wizard-recap"))
    assert response.status_code == 200
    assert show.title in response.content.decode()

    response = client.post(reverse("gigs:wizard-recap"))
    assert response.status_code == 302

    gig = Gig.objects.get(tenant=tenant)
    assert response.url == reverse("gigs:detail", args=[gig.pk])
    assert gig.show == show
    assert gig.promoter == promoter
    assert gig.venue == venue
    assert gig.date == gig_date
    assert str(gig.price) == "800.00"
    assert gig.conditions == "Loge chauffée"
    assert "gig_wizard" not in client.session


def test_wizard_quick_create_attaches_objects_to_the_current_tenant(client):
    tenant = _login(client)

    response = client.post(
        reverse("gigs:wizard-show"),
        {
            "mode": "new",
            "title": "Concert acoustique",
            "duration_minutes": 90,
            "default_price": "600",
        },
    )
    assert response.status_code == 302

    response = client.post(
        reverse("gigs:wizard-promoter"),
        {
            "mode": "new",
            "name": "Salle des fêtes de Yville",
            "siret": "",
            "billing_address": "",
            "email": "",
        },
    )
    assert response.status_code == 302

    response = client.post(
        reverse("gigs:wizard-venue"),
        {"mode": "new", "name": "La Grange", "address": "1 rue du Port"},
    )
    assert response.status_code == 302

    gig_date = datetime.date.today() + datetime.timedelta(days=20)
    client.post(
        reverse("gigs:wizard-details"),
        {"date": gig_date.isoformat(), "price": "700.00", "conditions": ""},
    )
    client.post(reverse("gigs:wizard-recap"))

    gig = Gig.objects.get(tenant=tenant)
    assert gig.show.title == "Concert acoustique"
    assert gig.show.tenant == tenant
    assert gig.promoter.name == "Salle des fêtes de Yville"
    assert gig.promoter.tenant == tenant
    assert gig.venue.name == "La Grange"
    assert gig.venue.tenant == tenant


def test_details_step_rejects_invalid_price(client):
    tenant = _login(client)
    show = ShowFactory(tenant=tenant)
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)
    client.post(reverse("gigs:wizard-show"), {"mode": "existing", "show": show.pk})
    client.post(reverse("gigs:wizard-promoter"), {"mode": "existing", "promoter": promoter.pk})
    client.post(reverse("gigs:wizard-venue"), {"mode": "existing", "venue": venue.pk})

    response = client.post(
        reverse("gigs:wizard-details"),
        {"date": "not-a-date", "price": "800.00", "conditions": ""},
    )

    assert response.status_code == 200
    assert Gig.objects.count() == 0


def test_promoter_step_redirects_to_first_step_if_show_not_chosen(client):
    _login(client)

    response = client.get(reverse("gigs:wizard-promoter"))

    assert response.status_code == 302
    assert response.url == reverse("gigs:wizard-show")


def test_wizard_show_step_only_lists_shows_from_the_current_tenant(client):
    tenant = _login(client)
    own_show = ShowFactory(tenant=tenant)
    other_show = ShowFactory()

    response = client.get(reverse("gigs:wizard-show"))

    content = response.content.decode()
    assert own_show.title in content
    assert other_show.title not in content


def test_wizard_cannot_reuse_another_tenants_show(client):
    tenant = _login(client)
    other_show = ShowFactory()
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)

    response = client.post(reverse("gigs:wizard-show"), {"mode": "existing", "show": other_show.pk})

    assert response.status_code == 200
    assert Gig.objects.count() == 0

    # Even if a show_id from another tenant ended up in the session,
    # the creation step must not leak across tenants.
    session = client.session
    session["gig_wizard"] = {
        "show_id": other_show.pk,
        "promoter_id": promoter.pk,
        "venue_id": venue.pk,
        "date": (datetime.date.today() + datetime.timedelta(days=5)).isoformat(),
        "price": "500.00",
        "conditions": "",
    }
    session.save()

    response = client.post(reverse("gigs:wizard-recap"))

    assert response.status_code == 404
    assert Gig.objects.count() == 0


def _fill_until_recap(client, tenant):
    show = ShowFactory(tenant=tenant)
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)
    gig_date = datetime.date.today() + datetime.timedelta(days=10)
    client.post(reverse("gigs:wizard-show"), {"mode": "existing", "show": show.pk})
    client.post(reverse("gigs:wizard-promoter"), {"mode": "existing", "promoter": promoter.pk})
    client.post(reverse("gigs:wizard-venue"), {"mode": "existing", "venue": venue.pk})
    client.post(reverse("gigs:wizard-details"), {"date": gig_date.isoformat(), "price": "800.00"})
    return show, promoter, venue, gig_date


@pytest.mark.parametrize(
    ("step", "previous"),
    [
        ("wizard-promoter", "wizard-show"),
        ("wizard-venue", "wizard-promoter"),
        ("wizard-details", "wizard-venue"),
        ("wizard-recap", "wizard-details"),
    ],
)
def test_each_step_links_to_the_previous_one(client, step, previous):
    tenant = _login(client)
    _fill_until_recap(client, tenant)

    response = client.get(reverse(f"gigs:{step}"))

    assert response.status_code == 200
    assert f'href="{reverse(f"gigs:{previous}")}"' in response.content.decode()
    assert "Précédent" in response.content.decode()


def test_first_step_offers_to_cancel_instead_of_previous(client):
    _login(client)

    content = client.get(reverse("gigs:wizard-show")).content.decode()

    assert "Précédent" not in content
    assert "Annuler" in content
    assert f'href="{reverse("gigs:list")}"' in content


def test_going_back_keeps_the_previous_answers(client):
    tenant = _login(client)
    _, _, venue, gig_date = _fill_until_recap(client, tenant)

    details = client.get(reverse("gigs:wizard-details")).content.decode()
    venue_page = client.get(reverse("gigs:wizard-venue")).content.decode()

    assert gig_date.isoformat() in details
    assert "800" in details
    assert f'value="{venue.pk}" selected' in venue_page


def _create_gig_through_the_wizard(client, tenant, event_name=""):
    show = ShowFactory(tenant=tenant)
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)
    client.post(reverse("gigs:wizard-show"), {"mode": "existing", "show": show.pk})
    client.post(reverse("gigs:wizard-promoter"), {"mode": "existing", "promoter": promoter.pk})
    client.post(reverse("gigs:wizard-venue"), {"mode": "existing", "venue": venue.pk})
    client.post(
        reverse("gigs:wizard-details"),
        {
            "date": (datetime.date.today() + datetime.timedelta(days=10)).isoformat(),
            "price": "800.00",
            "event_name": event_name,
        },
    )
    return client.post(reverse("gigs:wizard-recap")), promoter


def test_the_wizard_keeps_the_optional_event_name(client):
    tenant = _login(client)

    _create_gig_through_the_wizard(client, tenant, event_name="Festival d'été")

    assert Gig.objects.get(tenant=tenant).event_name == "Festival d'été"


def test_the_event_name_is_optional_in_the_wizard(client):
    tenant = _login(client)

    _create_gig_through_the_wizard(client, tenant)

    assert Gig.objects.get(tenant=tenant).event_name == ""


def test_the_organiser_form_is_offered_once_after_the_creation(client):
    tenant = _login(client)
    response, _promoter = _create_gig_through_the_wizard(client, tenant)

    first = client.get(response.url).content.decode()
    second = client.get(response.url).content.decode()

    assert "Envoyer le formulaire à l&#x27;organisateur ?" in first or (
        "Envoyer le formulaire à l'organisateur ?" in first
    )
    assert "Plus tard" in first
    assert "Plus tard" not in second


def test_the_offer_is_not_made_when_the_organiser_already_answered(client):
    from django.utils import timezone

    from apps.addressbook import services as addressbook_services

    tenant = _login(client)
    show = ShowFactory(tenant=tenant)
    promoter = PromoterFactory(tenant=tenant)
    venue = VenueFactory(tenant=tenant)
    invitation = addressbook_services.create_invitation(promoter, None)
    invitation.completed_at = timezone.now()
    invitation.save()
    client.post(reverse("gigs:wizard-show"), {"mode": "existing", "show": show.pk})
    client.post(reverse("gigs:wizard-promoter"), {"mode": "existing", "promoter": promoter.pk})
    client.post(reverse("gigs:wizard-venue"), {"mode": "existing", "venue": venue.pk})
    client.post(
        reverse("gigs:wizard-details"),
        {
            "date": (datetime.date.today() + datetime.timedelta(days=10)).isoformat(),
            "price": "800.00",
        },
    )
    response = client.post(reverse("gigs:wizard-recap"))

    assert "Plus tard" not in client.get(response.url).content.decode()


def test_sending_the_form_from_the_date_page_comes_back_to_the_date(client):
    tenant = _login(client)
    response, promoter = _create_gig_through_the_wizard(client, tenant)
    gig = Gig.objects.get(tenant=tenant)

    sent = client.post(
        reverse("addressbook:promoter-invite", args=[promoter.pk]),
        {"gig": gig.pk, "back": "detail"},
    )

    assert sent.url == reverse("gigs:detail", args=[gig.pk])
    page = client.get(sent.url).content.decode()
    assert "Le formulaire de l&#x27;organisateur est actif" in page or "est actif jusqu" in page
