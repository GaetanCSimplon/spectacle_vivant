""" "Mot de passe oublié", end to end: ask, receive the link, choose a new password, sign in."""

import re

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

from apps.accounts.models import SignupInvitation, User
from apps.tenants.factories import MembershipFactory

pytestmark = pytest.mark.django_db

OLD = "ancien-mot-de-passe-solide"
NEW = "nouveau-mot-de-passe-solide"


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user():
    membership = MembershipFactory()
    member = membership.user
    member.set_password(OLD)
    member.save()
    EmailAddress.objects.create(user=member, email=member.email, verified=True, primary=True)
    return member


def _ask(client, email):
    return client.post(reverse("account_reset_password"), {"email": email}, follow=True)


def _link(message):
    return re.search(r"https?://[^\s]+/password/reset/key/[^\s]+", message.body).group(0)


def _path(link):
    return "/" + link.split("/", 3)[3]


def _login(client, email, password):
    return client.post(reverse("account_login"), {"login": email, "password": password})


def test_the_whole_flow_from_the_login_page_to_a_new_password(client, user):
    assert (
        reverse("account_reset_password") in client.get(reverse("account_login")).content.decode()
    )

    page = _ask(client, user.email)
    assert page.status_code == 200
    assert page.redirect_chain[-1][0] == reverse("account_reset_password_done")
    assert len(mail.outbox) == 1 and mail.outbox[0].to == [user.email]

    key_page = client.get(_path(_link(mail.outbox[0])), follow=True)
    assert key_page.status_code == 200 and 'name="password1"' in key_page.content.decode()

    done = client.post(
        key_page.redirect_chain[-1][0], {"password1": NEW, "password2": NEW}, follow=True
    )
    assert done.status_code == 200

    assert _login(client, user.email, NEW).status_code == 302
    client.logout()
    assert _login(client, user.email, OLD).status_code == 200  # the old one no longer works


def test_the_e_mail_is_in_french_and_carries_a_link_of_the_site(client, user):
    from django.contrib.sites.models import Site

    Site.objects.update_or_create(pk=1, defaults={"domain": "bordpro.example", "name": "Bòrd Pro"})
    _ask(client, user.email)

    message = mail.outbox[0]
    link = _link(message)

    assert message.subject.startswith("[Bòrd Pro]")
    assert "mot de passe" in message.body.lower()
    assert "Prenez le contrôle de votre tournée" in message.body
    # the link uses the host the visitor came from (the host check keeps it to our own domains)
    assert link.startswith("http") and "/accounts/password/reset/key/" in link


def test_an_unknown_address_gets_the_same_page_and_no_e_mail(client, user):
    """No e-mail either: allauth's default one would invite to sign up, which is closed."""
    known = _ask(client, user.email)
    mail.outbox.clear()
    cache.clear()

    unknown = _ask(client, "inconnu@example.org")

    assert unknown.status_code == 200 and not mail.outbox
    assert unknown.redirect_chain == known.redirect_chain  # nothing tells the two cases apart
    assert not User.objects.filter(email="inconnu@example.org").exists()


def test_the_link_works_once_only(client, user):
    _ask(client, user.email)
    path = _path(_link(mail.outbox[0]))
    key_page = client.get(path, follow=True)
    client.post(key_page.redirect_chain[-1][0], {"password1": NEW, "password2": NEW}, follow=True)
    client.logout()

    again = client.get(path, follow=True)

    assert 'name="password1"' not in again.content.decode()
    assert "mot de passe" in again.content.decode().lower()


def test_a_tampered_link_is_refused(client, user):
    _ask(client, user.email)
    path = _path(_link(mail.outbox[0]))

    page = client.get(path[:-6] + "zzzzz/", follow=True)

    assert 'name="password1"' not in page.content.decode()


def test_a_weak_or_mismatched_password_is_refused_and_the_old_one_stays(client, user):
    _ask(client, user.email)
    key_page = client.get(_path(_link(mail.outbox[0])), follow=True)
    url = key_page.redirect_chain[-1][0]

    short = client.post(url, {"password1": "abc", "password2": "abc"})
    different = client.post(url, {"password1": NEW, "password2": NEW + "x"})

    assert short.status_code == 200 and different.status_code == 200
    client.logout()
    assert _login(client, user.email, OLD).status_code == 302  # unchanged


def test_after_the_reset_the_account_is_still_reachable_and_isolated(client, user):
    _ask(client, user.email)
    key_page = client.get(_path(_link(mail.outbox[0])), follow=True)
    client.post(key_page.redirect_chain[-1][0], {"password1": NEW, "password2": NEW})
    client.logout()

    _login(client, user.email, NEW)

    assert client.get(reverse("home")).status_code == 200


def test_the_invitation_list_does_not_block_a_password_reset(client, user, settings):
    """It limits who can create an account, not who can get back into theirs."""
    settings.SIGNUP_REQUIRES_INVITATION = True
    assert not SignupInvitation.objects.filter(email=user.email).exists()

    _ask(client, user.email)

    assert len(mail.outbox) == 1


def test_asking_too_often_for_the_same_address_is_limited(client, user):
    statuses = [_ask(client, user.email).status_code for _attempt in range(6)]

    assert statuses[:5] == [200] * 5 and statuses[5] == 429
    assert len(mail.outbox) == 5  # allauth allows 5 per minute for one address


def test_a_reset_never_creates_an_account(client):
    _ask(client, "nouveau@example.org")

    assert not User.objects.filter(email="nouveau@example.org").exists()


def test_the_reset_page_asks_for_an_address_and_needs_no_login(client):
    page = client.get(reverse("account_reset_password"))

    assert page.status_code == 200 and 'name="email"' in page.content.decode()
