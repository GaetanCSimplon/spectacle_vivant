from django.urls import reverse

TYPES = {"promoter": "organisateurs", "venue": "lieux", "contact": "personnes"}


def directory_url(kind):
    """The address-book page of a kind: "promoter", "venue" or "contact"."""
    return f"{reverse('addressbook:directory')}?type={TYPES[kind]}"


def list_get(client, kind, data=None, **extra):
    """GET the list of a kind with filters (a data dict would replace the `?type=` otherwise)."""
    return client.get(
        reverse("addressbook:directory"), {"type": TYPES[kind], **(data or {})}, **extra
    )
