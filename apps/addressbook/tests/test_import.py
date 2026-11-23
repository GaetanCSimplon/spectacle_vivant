"""CSV import into the address book: preview first, nothing saved until the user confirms."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.tenants.factories import MembershipFactory

from .. import imports
from ..factories import ContactFactory, PromoterFactory, VenueFactory
from ..models import Contact, Promoter, Venue
from .helpers import directory_url

pytestmark = pytest.mark.django_db

UPLOAD = "addressbook:import"
CONFIRM = "addressbook:import-confirm"


@pytest.fixture
def tenant(client):
    membership = MembershipFactory()
    client.force_login(membership.user)
    return membership.tenant


def _file(text, name="annuaire.csv", encoding="utf-8"):
    return SimpleUploadedFile(name, text.encode(encoding), content_type="text/csv")


def _preview(client, kind, text, **options):
    return client.post(reverse(UPLOAD), {"kind": kind, "file": _file(text, **options)})


def _import(client, kind, text, duplicates="ignore", **options):
    _preview(client, kind, text, **options)
    return client.post(reverse(CONFIRM), {"duplicates": duplicates})


CONTACTS = "Nom;Fonction;E-mail;Téléphone;Organisateurs;Lieux\r\n"


# --- the preview saves nothing ---------------------------------------------------------------


def test_the_preview_counts_new_rows_duplicates_and_errors_and_saves_nothing(client, tenant):
    ContactFactory(tenant=tenant, promoter=None, venue=None, name="Déjà Là", email="la@ex.org")
    text = (
        CONTACTS + "Léa Durand;Accueil;lea@ex.org;0601020304;;\r\n"
        "Déjà Là;;la@ex.org;;;\r\n"
        "Sans mail correct;;pas-un-mail;;;\r\n"
    )

    response = _preview(client, "contacts", text)

    assert response.status_code == 200
    assert response.context["counts"] == {"new": 1, "duplicate": 1, "error": 1}
    assert Contact.objects.filter(tenant=tenant).count() == 1
    page = response.content.decode()
    assert "Rien n'est encore enregistré" in page and "Ligne 4" in page


def test_the_confirmation_creates_the_contacts_in_this_structure(client, tenant):
    text = CONTACTS + "Léa Durand;Accueil;lea@ex.org;0601020304;;\r\nPaul Roux;;;;;\r\n"

    response = _import(client, "contacts", text)

    assert response.url == directory_url("contact")
    lea = Contact.objects.get(name="Léa Durand")
    assert lea.tenant == tenant and lea.role == "Accueil" and lea.email == "lea@ex.org"
    assert Contact.objects.filter(tenant=tenant).count() == 2


def test_confirming_without_a_file_in_the_session_does_nothing(client, tenant):
    response = client.post(reverse(CONFIRM))

    assert response.url == reverse(UPLOAD)
    assert not Contact.objects.exists()


def test_the_file_can_only_be_confirmed_once(client, tenant):
    _import(client, "contacts", CONTACTS + "Léa;;;;;\r\n")

    client.post(reverse(CONFIRM))

    assert Contact.objects.filter(tenant=tenant).count() == 1


# --- reading the file ------------------------------------------------------------------------


def test_an_excel_file_in_windows_1252_with_commas_is_read(client, tenant):
    text = "Nom,Fonction\r\nRené Bézier,Régisseur\r\n"

    _import(client, "contacts", text, encoding="cp1252")

    assert Contact.objects.get(tenant=tenant).name == "René Bézier"


def test_column_titles_are_recognised_without_looking_at_accents_or_case(client, tenant):
    text = "NOM;TELEPHONE;e-mail;Colonne inconnue\r\nAnna;0102030405;a@ex.org;x\r\n"

    response = _preview(client, "contacts", text)

    assert response.context["ignored_columns"] == ["Colonne inconnue"]
    client.post(reverse(CONFIRM))
    anna = Contact.objects.get(tenant=tenant)
    assert anna.phone == "0102030405" and anna.email == "a@ex.org"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("", "vide"),
        ("Fonction;E-mail\r\nAccueil;a@ex.org\r\n", "colonne « Nom »"),
        ("Nom;Fonction\r\n", "aucune ligne"),
    ],
)
def test_an_unusable_file_is_explained(client, tenant, content, message):
    response = _preview(client, "contacts", content)

    assert response.status_code == 200 and message in response.content.decode()
    assert "import_preview" not in [t.name for t in response.templates if t.name]


def test_a_file_that_is_not_csv_is_refused(client, tenant):
    pdf = SimpleUploadedFile("a.csv", b"%PDF-1.4\x00\x01binary")
    text = client.post(reverse(UPLOAD), {"kind": "contacts", "file": pdf}).content.decode()
    other_extension = client.post(
        reverse(UPLOAD), {"kind": "contacts", "file": _file(CONTACTS, name="liste.xlsx")}
    ).content.decode()

    assert "n&#x27;est pas un fichier CSV" in text or "pas un fichier CSV" in text
    assert "Seuls les fichiers .csv" in other_extension


def test_a_file_over_2_mb_or_1000_rows_is_refused(client, tenant):
    big = CONTACTS + ("A;;;;;\r\n" * 1001)
    heavy = "Nom\r\n" + ("x" * 100 + "\r\n") * 25000

    too_long = _preview(client, "contacts", big).content.decode()
    too_big = _preview(client, "contacts", heavy).content.decode()

    assert "plus de 1000 lignes" in too_long
    assert "trop gros" in too_big
    assert imports.MAX_ROWS == 1000 and imports.MAX_BYTES == 2 * 1024 * 1024
    assert not Contact.objects.exists()


def test_the_import_needs_a_login(client):
    for name in (UPLOAD, CONFIRM):
        response = client.get(reverse(name)) if name == UPLOAD else client.post(reverse(name))
        assert response.status_code == 302 and response.url.startswith(reverse("account_login"))
    template = client.get(reverse("addressbook:import-template", args=["contacts"]))
    assert template.status_code == 302


# --- duplicates -------------------------------------------------------------------------------


def test_duplicates_are_ignored_by_default_and_nothing_changes(client, tenant):
    old = ContactFactory(tenant=tenant, promoter=None, venue=None, name="Léa", email="lea@ex.org")

    _import(client, "contacts", CONTACTS + "Léa Nouvelle;Régie;LEA@ex.org;;;\r\n")

    old.refresh_from_db()
    assert old.name == "Léa" and old.role == "" and Contact.objects.count() == 1


def test_duplicates_can_be_updated_with_the_filled_cells_only(client, tenant):
    old = ContactFactory(
        tenant=tenant, promoter=None, venue=None, name="Léa", email="lea@ex.org", phone="0102"
    )

    response = _import(
        client, "contacts", CONTACTS + "Léa;Régie;lea@ex.org;;;\r\n", duplicates="update"
    )

    old.refresh_from_db()
    assert old.role == "Régie" and old.phone == "0102"  # the empty cell kept the old value
    assert Contact.objects.count() == 1 and response.status_code == 302


def test_a_contact_without_email_is_a_duplicate_when_the_name_is_the_same(client, tenant):
    ContactFactory(tenant=tenant, promoter=None, venue=None, name="Paul Roux")

    response = _preview(client, "contacts", CONTACTS + "paul roux;;;;;\r\n")

    assert response.context["counts"]["duplicate"] == 1


def test_the_same_person_twice_in_the_file_is_created_once(client, tenant):
    _import(client, "contacts", CONTACTS + "Léa;;lea@ex.org;;;\r\nLéa;;lea@ex.org;;;\r\n")

    assert Contact.objects.filter(tenant=tenant).count() == 1


# --- links ------------------------------------------------------------------------------------


def test_contacts_are_attached_to_existing_organisers_and_venues_by_name(client, tenant):
    mairie = PromoterFactory(tenant=tenant, name="Mairie de Sète")
    festival = PromoterFactory(tenant=tenant, name="Festival Été")
    arenes = VenueFactory(tenant=tenant, name="Salle des Arènes")

    _import(
        client,
        "contacts",
        CONTACTS + "Léa;;;;mairie de sète | Festival Été;Salle des Arènes\r\n",
    )

    lea = Contact.objects.get(tenant=tenant)
    assert set(lea.promoters.all()) == {mairie, festival} and list(lea.venues.all()) == [arenes]


def test_an_unknown_name_is_reported_and_never_created(client, tenant):
    text = CONTACTS + "Léa;;;;Inconnu;Salle fantôme\r\n"

    response = _preview(client, "contacts", text)
    client.post(reverse(CONFIRM))

    assert "Organisateur inconnu" in response.content.decode()
    assert "Lieu inconnu" in response.content.decode()
    lea = Contact.objects.get(tenant=tenant)
    assert lea.attachments == []
    assert not Promoter.objects.exists() and not Venue.objects.exists()


def test_another_structures_organiser_is_never_found_by_name(client, tenant):
    PromoterFactory(name="Mairie étrangère")

    _import(client, "contacts", CONTACTS + "Léa;;;;Mairie étrangère;\r\n")

    assert Contact.objects.get(tenant=tenant).attachments == []


def test_an_existing_object_of_another_structure_is_not_a_duplicate(client, tenant):
    ContactFactory(promoter=None, venue=None, name="Léa", email="lea@ex.org")

    response = _preview(client, "contacts", CONTACTS + "Léa;;lea@ex.org;;;\r\n")

    assert response.context["counts"]["new"] == 1


# --- venues and organisers --------------------------------------------------------------------


def test_venues_are_imported_with_their_organisers_and_without_a_map_lookup(
    client, tenant, monkeypatch
):
    mairie = PromoterFactory(tenant=tenant, name="Mairie")

    def no_lookup(*args, **kwargs):
        raise AssertionError("an import never asks the map service")

    monkeypatch.setattr("apps.core.models.geocode", no_lookup)
    text = (
        "Nom;Adresse;Code postal;Ville;Jauge;Téléphone;Organisateurs\r\n"
        "Halle;1 rue des Lilas;34200;Sète;300;0467000000;Mairie\r\n"
    )

    _import(client, "lieux", text)

    halle = Venue.objects.get(tenant=tenant)
    assert halle.city == "Sète" and halle.capacity == 300 and halle.latitude is None
    assert list(halle.promoters.all()) == [mairie]


def test_a_venue_with_the_same_name_in_another_city_is_not_a_duplicate(client, tenant):
    VenueFactory(tenant=tenant, name="Salle polyvalente", city="Nîmes")

    response = _preview(client, "lieux", "Nom;Ville\r\nSalle polyvalente;Sète\r\n")

    assert response.context["counts"] == {"new": 1, "duplicate": 0, "error": 0}


def test_a_bad_capacity_or_postal_code_is_an_error_on_that_line_only(client, tenant):
    text = (
        "Nom;Jauge;Code postal\r\nBonne;100;34200\r\nMauvaise;beaucoup;34200\r\nTrop;1;3420099\r\n"
    )

    response = _preview(client, "lieux", text)

    assert response.context["counts"] == {"new": 1, "duplicate": 0, "error": 2}


def test_organisers_are_imported_with_status_and_type_by_label(client, tenant):
    text = (
        "Nom;Statut;Type;SIRET;Adresse;Code postal;Ville;E-mail;Téléphone;Contacts\r\n"
        "Mairie de Sète;Client actif;Collectivité | Festival;12345678900012;1 quai;34200;Sète;"
        "m@ex.org;0467;Quelqu'un\r\n"
        "Autre;Statut bizarre;Type bizarre;;;;;;;\r\n"
    )

    response = _import(client, "organisateurs", text)

    mairie = Promoter.objects.get(name="Mairie de Sète")
    assert mairie.tenant == tenant and mairie.follow_up == "active"
    assert set(mairie.kinds) == {"municipality", "festival"}
    assert mairie.billing_address == "1 quai" and mairie.siret == "12345678900012"
    autre = Promoter.objects.get(name="Autre")
    assert autre.follow_up == "" and autre.kinds == []
    assert response.status_code == 302


def test_what_the_export_writes_can_be_imported_again(client, tenant):
    promoter = PromoterFactory(tenant=tenant, name="Mairie")
    ContactFactory(tenant=tenant, promoter=promoter, venue=None, name="Léa", role="Accueil")
    exported = client.get(reverse("addressbook:contact-export")).content.decode("utf-8-sig")
    Contact.objects.all().delete()

    _import(client, "contacts", exported)

    lea = Contact.objects.get(tenant=tenant)
    assert lea.role == "Accueil" and list(lea.promoters.all()) == [promoter]


# --- safety -----------------------------------------------------------------------------------


def test_a_formula_is_stored_as_text_and_the_apostrophe_of_our_export_is_removed(client, tenant):
    _import(client, "contacts", CONTACTS + "=HYPERLINK(1);;;;;\r\n'=Autre;;;;;\r\n")

    names = set(Contact.objects.values_list("name", flat=True))
    assert names == {"=HYPERLINK(1)", "=Autre"}


def test_names_are_escaped_in_the_preview(client, tenant):
    response = _preview(client, "contacts", CONTACTS + "<script>alert(1)</script>;;;;;\r\n")

    page = response.content.decode()
    assert "<script>alert(1)" not in page and "&lt;script&gt;" in page


def test_a_tenant_cannot_be_chosen_by_the_file(client, tenant):
    other = MembershipFactory().tenant

    _import(client, "contacts", f"Nom;Tenant;tenant_id\r\nLéa;{other.pk};{other.pk}\r\n")

    assert Contact.objects.get().tenant == tenant


def test_the_template_is_an_empty_file_with_the_columns(client, tenant):
    response = client.get(reverse("addressbook:import-template", args=["lieux"]))

    assert response["Content-Disposition"].startswith("attachment")
    assert response.content.decode("utf-8-sig").strip() == (
        "Nom;Adresse;Code postal;Ville;Jauge;Téléphone;Organisateurs"
    )
    assert client.get(reverse("addressbook:import-template", args=["x"])).status_code == 404


def test_each_tab_links_to_the_import_for_its_own_kind(client, tenant):
    for name, kind in (
        ("promoter", "organisateurs"),
        ("venue", "lieux"),
        ("contact", "contacts"),
    ):
        page = client.get(directory_url(name)).content.decode()
        assert f"{reverse(UPLOAD)}?type={kind}" in page
