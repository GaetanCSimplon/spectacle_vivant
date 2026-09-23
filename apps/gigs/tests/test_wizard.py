import datetime

import pytest
from django.urls import reverse

from apps.addressbook.factories import PromoterFactory, VenueFactory
from apps.catalog.factories import ShowFactory
from apps.organizations.factories import MembershipFactory

from ..models import Gig

pytestmark = pytest.mark.django_db


def _login(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.organization


def test_wizard_show_step_requires_login(client):
    response = client.get(reverse("gigs:wizard-show"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_full_wizard_creates_a_gig(client):
    organization = _login(client)
    show = ShowFactory(organization=organization)
    promoter = PromoterFactory(organization=organization)
    venue = VenueFactory(organization=organization)

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

    gig = Gig.objects.get(organization=organization)
    assert gig.show == show
    assert gig.promoter == promoter
    assert gig.venue == venue
    assert gig.date == gig_date
    assert str(gig.price) == "800.00"
    assert gig.conditions == "Loge chauffée"
    assert "gig_wizard" not in client.session


def test_wizard_quick_create_attaches_objects_to_the_current_organization(client):
    organization = _login(client)

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

    gig = Gig.objects.get(organization=organization)
    assert gig.show.title == "Concert acoustique"
    assert gig.show.organization == organization
    assert gig.promoter.name == "Salle des fêtes de Yville"
    assert gig.promoter.organization == organization
    assert gig.venue.name == "La Grange"
    assert gig.venue.organization == organization


def test_details_step_rejects_invalid_price(client):
    organization = _login(client)
    show = ShowFactory(organization=organization)
    promoter = PromoterFactory(organization=organization)
    venue = VenueFactory(organization=organization)
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


def test_wizard_show_step_only_lists_shows_from_the_current_organization(client):
    organization = _login(client)
    own_show = ShowFactory(organization=organization)
    other_show = ShowFactory()

    response = client.get(reverse("gigs:wizard-show"))

    content = response.content.decode()
    assert own_show.title in content
    assert other_show.title not in content


def test_wizard_cannot_reuse_another_organizations_show(client):
    organization = _login(client)
    other_show = ShowFactory()
    promoter = PromoterFactory(organization=organization)
    venue = VenueFactory(organization=organization)

    response = client.post(reverse("gigs:wizard-show"), {"mode": "existing", "show": other_show.pk})

    assert response.status_code == 200
    assert Gig.objects.count() == 0

    # Even if a show_id from another organization ended up in the session,
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
