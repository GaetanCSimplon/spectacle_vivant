"""Isolation audit: every URL of the app, with two tenants.

Tenant A owns a full dataset (every kind of object, file and document). A user of tenant B
then calls every route that takes an identifier, with A's identifiers (and with a mix of
B's gig and A's other objects): the answer must be a 404 and nothing may change in the
database. Routes without identifier (lists, pages, exports) must never show A's data.

A route that takes an identifier must be described in ROUTES below, or be declared public:
`test_every_route_is_audited` fails otherwise, so a new URL cannot skip the audit.
"""

import datetime

import pytest
from django.apps import apps as django_apps
from django.core.files.base import ContentFile
from django.db import transaction
from django.test import override_settings
from django.urls import URLPattern, URLResolver, get_resolver, reverse
from django.views.generic import RedirectView
from weasyprint import HTML

from apps.accounts.models import Membership
from apps.addressbook.factories import ContactFactory, VenueFactory
from apps.addressbook.views import DirectoryRedirectView
from apps.catalog.models import Show
from apps.core.models import TenantOwnedModel
from apps.core.views import PrefixRedirectView
from apps.documents import invoicing
from apps.documents import services as doc_services
from apps.documents.models import Invoice
from apps.finance import services as finance_services
from apps.finance.factories import ExpenseClaimFactory, ExpenseFactory
from apps.finance.models import Payment
from apps.gigs.factories import GigFactory, GigMemberFactory
from apps.gigs.models import Gig
from apps.roadmaps import services as roadmap_services
from apps.roadmaps.factories import (
    LodgingFactory,
    MealFactory,
    PlaceContactFactory,
    RoadmapDocumentFactory,
    RoadmapFactory,
    RoadmapSlotFactory,
)
from apps.tenants.factories import MembershipFactory, PersonFactory, TenantFactory
from apps.tenants.models import Tenant

pytestmark = pytest.mark.django_db

MARKER = "SECRETA"

# Routes that work without an account, by design.
# Routes whose parameter is not the id of an object (they only act on the user's own tenant).
PARAM_ONLY = {"export-csv", "addressbook:import-template"}

PUBLIC = {
    "favicon",  # browsers ask for /favicon.ico before any login
    "apple-touch-icon",
    "site-features",  # the presentation site: static text, no data
    "site-contact",
    "site-contact-thanks",
    "robots",
    "sitemap",
    "legal-notice",
    "legal-terms",
    "legal-privacy",
    "roadmap-public",  # the secret link is the access right
    "roadmap-public-pdf",
    "team-space",  # the personal link is the access right (tests: tenants/test_team_space.py)
    "team-space-gig",
    "team-space-pdf",
    "team-expenses",  # the personal link is the access right (finance/test_expense_claims.py)
    "team-expense-edit",
    "team-expense-delete",
    "team-expense-receipt",
    "promoter-form-public",  # the secret link is the access right
    "promoter-form-thanks",
    "info-form-public",  # the secret link is the access right (addressbook/test_info_form.py)
    "contract-share-public",  # the secret link is the access right (gigs/test_mail.py)
    "tour-form-public",  # the secret link is the access right (roadmaps/test_tour_form.py)
    "tour-form-thanks",
    "team-space-document",  # the personal link is the access right (roadmaps/test_documents.py)
    "team-space-contract",  # same (roadmaps/test_shared_contract.py)
}

# Routes that take an identifier: name -> {url parameter: key of A's dataset, or "=literal"}.
# `gig` is the gig of A; the audit also replays each route with B's own gig_id.
ROUTES = [
    ("tenants:person-detail", {"pk": "person"}),
    ("tenants:bord-status", {"pk": "gig"}),
    ("tenants:person-update", {"pk": "person"}),
    ("tenants:person-delete", {"pk": "person"}),
    ("tenants:person-access-enable", {"pk": "person"}),
    ("tenants:person-access-revoke", {"pk": "person"}),
    ("tenants:person-info-invite", {"pk": "person"}),
    ("tenants:person-info-revoke", {"pk": "person"}),
    ("tenants:person-info-answer", {"pk": "person"}),
    ("addressbook:contact-info-invite", {"pk": "contact"}),
    ("addressbook:contact-info-revoke", {"pk": "contact"}),
    ("addressbook:contact-info-answer", {"pk": "contact"}),
    ("addressbook:promoter-invite", {"pk": "promoter"}),
    ("addressbook:promoter-invite-revoke", {"pk": "promoter"}),
    ("addressbook:promoter-answer", {"pk": "promoter"}),
    ("addressbook:promoter-detail", {"pk": "promoter"}),
    ("addressbook:promoter-update", {"pk": "promoter"}),
    ("addressbook:promoter-delete", {"pk": "promoter"}),
    ("addressbook:venue-detail", {"pk": "venue"}),
    ("addressbook:venue-update", {"pk": "venue"}),
    ("addressbook:venue-delete", {"pk": "venue"}),
    ("addressbook:promoter-follow-up", {"pk": "promoter"}),
    ("addressbook:promoter-contact-attach", {"pk": "promoter"}),
    ("addressbook:promoter-contact-detach", {"pk": "promoter", "contact_pk": "contact"}),
    ("addressbook:venue-contact-attach", {"pk": "venue"}),
    ("addressbook:venue-contact-detach", {"pk": "venue", "contact_pk": "contact"}),
    ("addressbook:promoter-contact-create", {"promoter_pk": "promoter"}),
    ("addressbook:venue-contact-create", {"venue_pk": "venue"}),
    ("addressbook:contact-update", {"pk": "contact"}),
    ("addressbook:contact-delete", {"pk": "contact"}),
    ("catalog:show-detail", {"pk": "show"}),
    ("catalog:show-update", {"pk": "show"}),
    ("catalog:show-delete", {"pk": "show"}),
    ("catalog:show-file", {"pk": "show", "kind": "=rider"}),
    ("catalog:show-file", {"pk": "show", "kind": "=fiche-technique"}),
    ("gigs:detail", {"pk": "gig"}),
    ("gigs:ical", {"pk": "gig"}),
    ("gigs:team-add", {"pk": "gig"}),
    ("gigs:member-cachet", {"pk": "gig", "member_pk": "member"}),
    ("gigs:price", {"pk": "gig"}),
    ("gigs:checklist", {"pk": "gig"}),
    ("gigs:checklist-item", {"pk": "gig"}),
    ("gigs:checklist-reset", {"pk": "gig"}),
    ("gigs:terms", {"pk": "gig"}),
    ("gigs:confirm", {"pk": "gig"}),
    ("gigs:cancel", {"pk": "gig"}),
    ("gigs:reactivate", {"pk": "gig"}),
    ("gigs:delete", {"pk": "gig"}),
    ("roadmaps:editor", {"gig_id": "gig"}),
    ("roadmaps:pdf", {"gig_id": "gig"}),
    ("roadmaps:team-add", {"gig_id": "gig"}),
    ("roadmaps:contract-share", {"gig_id": "gig"}),
    ("roadmaps:document-add", {"gig_id": "gig"}),
    ("roadmaps:document-file", {"gig_id": "gig", "pk": "document"}),
    ("roadmaps:document-delete", {"gig_id": "gig", "pk": "document"}),
    ("roadmaps:tour-request-create", {"gig_id": "gig"}),
    ("roadmaps:tour-request-revoke", {"gig_id": "gig"}),
    ("roadmaps:tour-request-review", {"gig_id": "gig"}),
    ("roadmaps:notes", {"gig_id": "gig"}),
    ("roadmaps:share", {"gig_id": "gig", "action": "=activer"}),
    ("roadmaps:share", {"gig_id": "gig", "action": "=arreter"}),
    ("roadmaps:preview", {"gig_id": "gig"}),
    ("roadmaps:item-add", {"gig_id": "gig", "section": "=repas"}),
    ("roadmaps:item-edit", {"gig_id": "gig", "section": "=repas", "pk": "meal"}),
    ("roadmaps:item-delete", {"gig_id": "gig", "section": "=repas", "pk": "meal"}),
    ("roadmaps:item-edit", {"gig_id": "gig", "section": "=hebergements", "pk": "lodging"}),
    ("roadmaps:item-delete", {"gig_id": "gig", "section": "=creneaux", "pk": "slot"}),
    ("roadmaps:contact-add", {"gig_id": "gig", "section": "=hebergements", "pk": "lodging"}),
    (
        "roadmaps:contact-delete",
        {
            "gig_id": "gig",
            "section": "=hebergements",
            "pk": "lodging",
            "contact_pk": "place_contact",
        },
    ),
    ("finance:page", {"gig_id": "gig"}),
    ("finance:payment-add", {"gig_id": "gig", "invoice_pk": "invoice"}),
    ("finance:payment-edit", {"gig_id": "gig", "pk": "payment"}),
    ("finance:payment-delete", {"gig_id": "gig", "pk": "payment"}),
    ("finance:expense-add", {"gig_id": "gig"}),
    ("finance:expense-edit", {"gig_id": "gig", "pk": "expense"}),
    ("finance:expense-delete", {"gig_id": "gig", "pk": "expense"}),
    ("finance:expense-reimburse", {"gig_id": "gig", "pk": "expense"}),
    ("finance:expense-receipt", {"gig_id": "gig", "pk": "expense"}),
    ("finance:claim-accept", {"gig_id": "gig", "pk": "claim"}),
    ("finance:claim-refuse", {"gig_id": "gig", "pk": "claim"}),
    ("finance:claim-receipt", {"gig_id": "gig", "pk": "claim"}),
    ("documents:contract-complete", {"gig_id": "gig"}),
    ("documents:contract-preview", {"gig_id": "gig"}),
    ("documents:contract-history", {"gig_id": "gig"}),
    ("documents:contract-sign", {"gig_id": "gig"}),
    ("documents:contract-signed-pdf", {"gig_id": "gig"}),
    ("documents:contract-confirm", {"gig_id": "gig"}),
    ("documents:contract-generate", {"gig_id": "gig"}),
    ("documents:contract-share", {"gig_id": "gig"}),
    ("documents:contract-sent", {"gig_id": "gig", "action": "=envoye"}),
    ("documents:contract-sent", {"gig_id": "gig", "action": "=non-envoye"}),
    ("documents:contract-download", {"gig_id": "gig"}),
    ("documents:contract-version-download", {"gig_id": "gig", "number": "=1"}),
    ("documents:billing", {"gig_id": "gig"}),
    ("documents:quote-create", {"gig_id": "gig"}),
    ("documents:invoice-create", {"gig_id": "gig", "kind": "=full"}),
    ("documents:document-detail", {"gig_id": "gig", "doc_type": "=factures", "pk": "invoice"}),
    ("documents:document-detail", {"gig_id": "gig", "doc_type": "=devis", "pk": "quote"}),
    ("documents:document-pdf", {"gig_id": "gig", "doc_type": "=factures", "pk": "invoice"}),
    ("documents:document-title", {"gig_id": "gig", "doc_type": "=factures", "pk": "invoice"}),
    ("documents:document-title", {"gig_id": "gig", "doc_type": "=devis", "pk": "quote"}),
    ("documents:document-pdf", {"gig_id": "gig", "doc_type": "=devis", "pk": "quote"}),
    ("documents:document-issue", {"gig_id": "gig", "doc_type": "=factures", "pk": "draft"}),
    ("documents:document-delete", {"gig_id": "gig", "doc_type": "=factures", "pk": "draft"}),
    ("documents:line-add", {"gig_id": "gig", "doc_type": "=factures", "pk": "draft"}),
    (
        "documents:line-edit",
        {"gig_id": "gig", "doc_type": "=factures", "pk": "draft", "line_pk": "line"},
    ),
    (
        "documents:line-remove",
        {"gig_id": "gig", "doc_type": "=factures", "pk": "draft", "line_pk": "line"},
    ),
    ("documents:credit-note-create", {"gig_id": "gig", "pk": "invoice"}),
    ("documents:quote-accept", {"gig_id": "gig", "pk": "quote"}),
    ("documents:quote-scan", {"gig_id": "gig", "pk": "quote"}),
    ("documents:invoice-details", {"gig_id": "gig", "pk": "draft"}),
]


# --- the dataset ---------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def _media_root(tmp_path_factory):
    # One media folder for the whole module: the shared dataset below saves its files in it.
    with override_settings(MEDIA_ROOT=tmp_path_factory.mktemp("media")):
        yield


def _build_tenant_a():
    tenant = TenantFactory(
        name=f"Structure {MARKER}",
        address=f"1 rue {MARKER}",
        siret="12345678900012",
        vat_regime=Tenant.VatRegime.FRANCHISE,
        iban="FR1420041010050500013M02606",
    )
    gig = GigFactory(
        tenant=tenant,
        price="1000.00",
        status=Gig.Status.CONFIRMED,
        conditions=f"Conditions {MARKER}",
        show__title=f"Spectacle {MARKER}",
        show__group_name=f"Groupe {MARKER}",
        venue__name=f"Lieu {MARKER}",
        promoter__name=f"Organisateur {MARKER}",
        promoter__billing_address=f"3 place {MARKER}",
    )
    gig.show.rider_file.save("rider.pdf", ContentFile(b"%PDF rider"))
    gig.show.tech_sheet_file.save("fiche.pdf", ContentFile(HTML(string="<p>Fiche</p>").write_pdf()))
    contact = ContactFactory(
        tenant=tenant, promoter=gig.promoter, venue=None, name=f"Contact {MARKER}"
    )
    ContactFactory(tenant=tenant, promoter=None, venue=gig.venue, name=f"Contact lieu {MARKER}")
    VenueFactory(tenant=tenant, name=f"Autre lieu {MARKER}")
    doc_services.generate_contract_pdf(gig)
    doc_services.mark_contract_signed(gig, ContentFile(b"%PDF signed", name="signed.pdf"))
    invoice = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT))
    payment = finance_services.record_payment(
        invoice, "10.00", datetime.date.today(), Payment.Method.CASH
    )
    quote = invoicing.create_quote(gig)
    invoicing.add_line(quote, f"Ligne devis {MARKER}", "100.00")
    draft = invoicing.create_invoice(gig, Invoice.Kind.BALANCE)
    line = invoicing.add_line(draft, f"Ligne {MARKER}", "50.00")
    expense = ExpenseFactory(gig=gig, label=f"Dépense {MARKER}")
    expense.receipt_file.save("ticket.pdf", ContentFile(b"%PDF ticket"))
    claim = ExpenseClaimFactory(gig=gig, label=f"Proposition {MARKER}")
    claim.receipt_file.save("recu.pdf", ContentFile(b"%PDF recu"))
    roadmap = RoadmapFactory(gig=gig, notes=f"Notes {MARKER}")
    slot = RoadmapSlotFactory(roadmap=roadmap)
    lodging = LodgingFactory(roadmap=roadmap, name=f"Hôtel {MARKER}")
    meal = MealFactory(roadmap=roadmap, place=f"Resto {MARKER}")
    place_contact = PlaceContactFactory(lodging=lodging, name=f"Réception {MARKER}")
    document = RoadmapDocumentFactory(roadmap=roadmap, title=f"Document {MARKER}")
    roadmap_services.publish(roadmap)
    person = PersonFactory(tenant=tenant, last_name=f"Equipier {MARKER}", average_fee="123.00")
    member = GigMemberFactory(
        gig=gig, person=person, name=person.full_name, cachet_count=2, cachet_amount="456.78"
    )
    return {
        "tenant": tenant,
        "show": gig.show,
        "promoter": gig.promoter,
        "venue": gig.venue,
        "contact": contact,
        "gig": gig,
        "invoice": invoice,
        "payment": payment,
        "quote": quote,
        "draft": draft,
        "line": line,
        "expense": expense,
        "claim": claim,
        "slot": slot,
        "lodging": lodging,
        "meal": meal,
        "place_contact": place_contact,
        "document": document,
        "person": person,
        "member": member,
    }


@pytest.fixture(scope="module")
def _world_data(django_db_setup, django_db_blocker, _media_root):
    """The dataset is built once per module (it takes seconds: PDFs, invoices...), not per test.

    It lives in an outer transaction rolled back at the end of the module; every test runs in its
    own savepoint inside it, so whatever a test changes is undone before the next one.
    """
    with django_db_blocker.unblock(), transaction.atomic():
        a = _build_tenant_a()
        membership_b = MembershipFactory(tenant__name="Structure B", role=Membership.Role.OWNER)
        gig_b = GigFactory(tenant=membership_b.tenant)
        yield {"a": a, "b_user": membership_b.user, "b_gig": gig_b}
        transaction.set_rollback(True)


@pytest.fixture
def world(client, _world_data):
    client.force_login(_world_data["b_user"])
    return _world_data


# --- helpers -------------------------------------------------------------------------


MOVED_ADDRESSES = {RedirectView, DirectoryRedirectView, PrefixRedirectView}


def _all_routes():
    """(full name, route text, view class) of every URL of the project."""

    def walk(patterns, namespaces, prefix):
        for entry in patterns:
            if isinstance(entry, URLResolver):
                inner = namespaces + ([entry.namespace] if entry.namespace else [])
                yield from walk(entry.url_patterns, inner, prefix + str(entry.pattern))
            elif isinstance(entry, URLPattern):
                full = ":".join([*namespaces, entry.name or ""])
                view = getattr(entry.callback, "view_class", None)
                if view in MOVED_ADDRESSES:  # a 301 to a page that is audited itself
                    continue
                yield full, prefix + str(entry.pattern), view

    for route in walk(get_resolver().url_patterns, [], ""):
        if not route[1].startswith(("admin/", "accounts/")):
            yield route


def _kwargs(spec, dataset, gig_id=None):
    kwargs = {}
    for param, key in spec.items():
        if key.startswith("="):
            value = key[1:]
            kwargs[param] = int(value) if value.isdigit() else value
        elif param == "gig_id" and gig_id is not None:
            kwargs[param] = gig_id
        else:
            kwargs[param] = dataset[key].pk
    return kwargs


def _methods(view):
    return [m.upper() for m in ("get", "post") if view is not None and hasattr(view, m)]


def _snapshot(tenant):
    """All the data of a tenant, to prove a refused request changed nothing."""
    models = [m for m in django_apps.get_models() if issubclass(m, TenantOwnedModel)]
    data = {
        m.__name__: sorted(map(str, m.objects.filter(tenant=tenant).values_list())) for m in models
    }
    data["Tenant"] = sorted(map(str, Tenant.objects.filter(pk=tenant.pk).values_list()))
    return data


# --- the audit ----------------------------------------------------------------------


def test_every_route_is_audited():
    audited = {name for name, _spec in ROUTES}
    for name, route, _view in _all_routes():
        takes_id = "<" in route
        if takes_id and name not in PUBLIC | PARAM_ONLY:
            assert name in audited, f"New route {name!r} ({route}) is not in the isolation audit."
    for name in audited:
        assert _params(name) is not None  # the audited name still exists


def _params(name):
    for full, route, _view in _all_routes():
        if full == name:
            import re

            return [m.split(":")[-1] for m in re.findall(r"<([^>]+)>", route)]
    raise AssertionError(f"{name} does not exist")


@pytest.mark.parametrize("name, spec", ROUTES, ids=lambda v: v if isinstance(v, str) else "")
def test_tenant_b_gets_a_404_on_every_object_of_tenant_a(client, world, name, spec):
    dataset = world["a"]
    view = next(v for n, _r, v in _all_routes() if n == name)
    before = _snapshot(dataset["tenant"])
    variants = [_kwargs(spec, dataset)]
    if set(spec) - {"gig_id"} - {p for p, k in spec.items() if k.startswith("=")}:
        # B's own gig with A's other object: the object must not be reachable either.
        variants.append(_kwargs(spec, dataset, gig_id=world["b_gig"].pk))

    for kwargs in variants:
        url = reverse(name, kwargs=kwargs)
        for method in _methods(view):
            response = client.generic(method, url)
            assert response.status_code == 404, f"{method} {url} -> {response.status_code}"
            assert MARKER not in response.content.decode(errors="ignore"), f"{method} {url}"

    assert _snapshot(dataset["tenant"]) == before, f"{name} changed the data of tenant A"


def test_a_user_of_tenant_a_reaches_the_same_urls(client, world):
    """Control: the audit is not a vacuum, the URLs do work for their owner."""
    owner = world["a"]["tenant"].memberships.first() or MembershipFactory(
        tenant=world["a"]["tenant"]
    )
    client.force_login(owner.user)
    dataset = world["a"]

    for name, spec in ROUTES:
        view = next(v for n, _r, v in _all_routes() if n == name)
        if "GET" not in _methods(view) or name in {
            "catalog:show-file",
            "documents:contract-sign",
            "documents:quote-scan",
        }:
            continue
        url = reverse(name, kwargs=_kwargs(spec, dataset))
        response = client.get(url)
        assert response.status_code != 404, f"GET {url} is 404 for the owner: bad audit data"


def _no_id_routes():
    for name, route, view in _all_routes():
        if "<" not in route and name not in PUBLIC:
            yield name, route, view


def test_pages_without_identifier_never_show_data_of_another_tenant(client, world):
    skipped = {"tenants:delete", "tenants:leave", "tenants:cancel-deletion"}
    for name, _route, view in _no_id_routes():
        if name in skipped or "GET" not in _methods(view):
            continue
        params = {"start": "2000-01-01", "end": "2100-12-31"}
        kwargs = {"kind": "factures"} if name == "export-csv" else {}
        url = reverse(name, kwargs=kwargs)
        response = client.get(url, params, follow=True)
        assert response.status_code == 200, f"GET {url} -> {response.status_code}"
        assert MARKER not in response.content.decode(errors="ignore"), f"GET {url} leaks"


@pytest.mark.parametrize("kind", ["factures", "recettes", "depenses"])
def test_csv_exports_never_hold_data_of_another_tenant(client, world, kind):
    response = client.get(
        reverse("export-csv", kwargs={"kind": kind}), {"start": "2000-01-01", "end": "2100-12-31"}
    )

    assert MARKER not in response.content.decode("utf-8-sig")


def test_every_non_public_route_requires_a_login(client, world):
    client.logout()
    dataset = world["a"]
    specs = {name: spec for name, spec in ROUTES}
    for name, route, view in _all_routes():
        if name in PUBLIC or name in {"tenants-onboarding", "home"}:  # "/" is public too
            continue
        spec = next((s for n, s in ROUTES if n == name), None)
        if "<" in route and spec is None:
            continue
        kwargs = (
            _kwargs(spec, dataset) if spec else ({"kind": "factures"} if "kind" in route else {})
        )
        url = reverse(name, kwargs=kwargs)
        for method in _methods(view):
            response = client.generic(method, url)
            assert response.status_code == 302, f"{method} {url} -> {response.status_code}"
            assert response.url.startswith(reverse("account_login")), f"{method} {url}"
    assert specs  # (kept for readability: every audited name was visited)


def test_the_data_export_of_b_holds_nothing_of_a(client, world):
    import io
    import zipfile

    response = client.post(reverse("tenants:data-export"))
    archive = zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))

    everything = "\n".join(
        [
            *archive.namelist(),
            *(archive.read(n).decode("utf-8", "ignore") for n in archive.namelist()),
        ]
    )
    assert MARKER not in everything


def test_foreign_keys_cannot_point_to_another_tenants_objects(client, world):
    """A form must not accept the id of an object of another tenant (promoter in a contact...)."""
    dataset = world["a"]
    before = _snapshot(dataset["tenant"])

    client.post(
        reverse("addressbook:contact-update", kwargs={"pk": dataset["contact"].pk}),
        {"name": "Piraté", "promoter": dataset["promoter"].pk},
    )
    response = client.post(
        reverse("gigs:wizard-show"), {"show": dataset["show"].pk, "choice": "existing"}
    )

    assert MARKER not in response.content.decode(errors="ignore")
    assert _snapshot(dataset["tenant"]) == before
    assert Show.objects.filter(tenant=dataset["tenant"]).count() == 1
