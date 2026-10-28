"""Import contacts, venues or organisers from a CSV file (our export or a spreadsheet's).

Three steps: `read_file` (decode, check the size, cut into rows), `analyse` (what each row would do,
nothing is saved), `apply` (the confirmed import, in one transaction). Everything lands in the
tenant of the user, whatever the file says. A name of organiser or venue that does not exist is
reported and ignored, never created behind the user's back. Venues are created without looking
their address up: `geocode_places` does that later, so an import never waits for a map service.
"""

import csv
import io
import unicodedata
from dataclasses import dataclass, field

from django import forms
from django.db import transaction
from django.db.models import Q

from apps.finance.exports import FORMULA_STARTS

from .exports import SEPARATOR
from .models import Contact, Promoter, Venue

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000


class ImportFileError(Exception):
    """The file cannot be read at all: the message (French) is shown to the user."""


def _plain(header):
    """ "Téléphone " -> "telephone", to recognise a column whatever its accents or case."""
    text = unicodedata.normalize("NFKD", header.strip().lower())
    return "".join(c for c in text if not unicodedata.combining(c))


# Column titles (without accents, lower case) -> the key used here. Unknown columns are ignored.
COMMON = {"nom": "name", "telephone": "phone", "tel": "phone", "ville": "city"}
COLUMNS = {
    "contacts": {
        **COMMON,
        "fonction": "role",
        "e-mail": "email",
        "email": "email",
        "mail": "email",
        "organisateurs": "promoters",
        "lieux": "venues",
    },
    "lieux": {
        **COMMON,
        "adresse": "address",
        "code postal": "postal_code",
        "jauge": "capacity",
        "organisateurs": "promoters",
    },
    "organisateurs": {
        **COMMON,
        "statut": "follow_up",
        "type": "kinds",
        "siret": "siret",
        "adresse": "billing_address",
        "code postal": "postal_code",
        "e-mail": "email",
        "email": "email",
        "mail": "email",
    },
}


class ContactRow(forms.Form):
    name = forms.CharField(max_length=255)
    role = forms.CharField(max_length=255, required=False)
    email = forms.EmailField(max_length=254, required=False)
    phone = forms.CharField(max_length=30, required=False)


class VenueRow(forms.Form):
    name = forms.CharField(max_length=255)
    address = forms.CharField(max_length=1000, required=False)
    postal_code = forms.CharField(max_length=5, required=False)
    city = forms.CharField(max_length=100, required=False)
    capacity = forms.IntegerField(min_value=0, max_value=1_000_000, required=False)
    phone = forms.CharField(max_length=30, required=False)


class PromoterRow(forms.Form):
    name = forms.CharField(max_length=255)
    siret = forms.CharField(max_length=14, required=False)
    billing_address = forms.CharField(max_length=1000, required=False)
    postal_code = forms.CharField(max_length=5, required=False)
    city = forms.CharField(max_length=100, required=False)
    email = forms.EmailField(max_length=254, required=False)
    phone = forms.CharField(max_length=30, required=False)


ROW_FORMS = {"contacts": ContactRow, "lieux": VenueRow, "organisateurs": PromoterRow}
MODELS = {"contacts": Contact, "lieux": Venue, "organisateurs": Promoter}


def _clean_cell(value):
    """A cell as text; the apostrophe our own export puts before a formula is taken off."""
    value = (value or "").strip()
    if value.startswith("'") and value[1:2] and value[1:2] in "".join(FORMULA_STARTS):
        value = value[1:]
    return value


def read_file(upload, kind):
    """The rows of an uploaded CSV as `[(line number, {key: text})]`, and the ignored columns."""
    if upload.size > MAX_BYTES:
        raise ImportFileError("Ce fichier est trop gros (2 Mo au plus).")
    raw = upload.read()
    if b"\x00" in raw:
        raise ImportFileError("Ce fichier n'est pas un fichier CSV.")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = raw.decode("cp1252")  # what Excel writes for a French "CSV"
        except UnicodeDecodeError:
            raise ImportFileError("Ce fichier n'est pas un fichier CSV lisible.") from None
    first_line = content.split("\n", 1)[0]
    delimiter = max(";,\t", key=first_line.count)
    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    try:
        header = next(reader)
    except (StopIteration, csv.Error):
        raise ImportFileError("Ce fichier est vide.") from None
    columns = COLUMNS[kind]
    keys = [columns.get(_plain(title)) for title in header]
    if "name" not in keys:
        raise ImportFileError("Il manque la colonne « Nom » sur la première ligne du fichier.")
    ignored = [
        title.strip()
        for title, key in zip(header, keys, strict=False)
        if key is None and title.strip()
    ]
    rows = []
    try:
        for number, cells in enumerate(reader, start=2):
            if not any(cell.strip() for cell in cells):
                continue
            if len(rows) >= MAX_ROWS:
                raise ImportFileError(
                    f"Ce fichier a plus de {MAX_ROWS} lignes : coupez-le en deux."
                )
            row = {}
            for key, cell in zip(keys, cells, strict=False):
                if key:
                    row[key] = _clean_cell(cell)
            rows.append((number, row))
    except csv.Error:
        raise ImportFileError("Ce fichier n'est pas un fichier CSV lisible.") from None
    if not rows:
        raise ImportFileError("Ce fichier ne contient aucune ligne à importer.")
    return rows, ignored


@dataclass
class Row:
    line: int
    data: dict = field(default_factory=dict)
    links: dict = field(default_factory=dict)  # {"promoters": [objects], "venues": [objects]}
    status: str = "new"  # "new", "duplicate" or "error"
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def name(self):
        return self.data.get("name", "")


def _by_name(queryset):
    found = {}
    for obj in queryset.order_by("pk"):
        found.setdefault(obj.name.casefold(), obj)
    return found


def _names(text):
    return [name.strip() for name in text.split(SEPARATOR.strip()) if name.strip()]


def _choice_codes(labels_text, choices, warnings, what):
    """ "Salle | Festival" -> ["venue", "festival"]; a label we do not know is reported."""
    by_label = {_plain(str(label)): code for code, label in choices.choices}
    codes = []
    for label in _names(labels_text):
        code = by_label.get(_plain(label))
        if code:
            codes.append(code)
        else:
            warnings.append(f"{what} inconnu : « {label} » (ignoré).")
    return codes


def find_existing(tenant, kind, data):
    """The object of this tenant that the row is about, if any."""
    model = MODELS[kind]
    queryset = model.objects.filter(tenant=tenant)
    if kind == "contacts" and data.get("email"):
        return queryset.filter(email__iexact=data["email"]).order_by("pk").first()
    queryset = queryset.filter(name__iexact=data["name"])
    if kind != "contacts" and data.get("city"):
        queryset = queryset.filter(Q(city__iexact=data["city"]) | Q(city=""))
    return queryset.order_by("pk").first()


def analyse(tenant, kind, raw_rows):
    """What each row would do. Nothing is saved."""
    promoters = _by_name(Promoter.objects.filter(tenant=tenant))
    venues = _by_name(Venue.objects.filter(tenant=tenant))
    seen = set()
    result = []
    for line, cells in raw_rows:
        row = Row(line=line)
        form = ROW_FORMS[kind](cells)
        if not form.is_valid():
            for name, problems in form.errors.items():
                title = "Nom" if name == "name" else name
                row.errors.append(f"{title} : {' '.join(problems)}")
            row.data = {"name": cells.get("name", "")}
            row.status = "error"
            result.append(row)
            continue
        row.data = {
            key: value for key, value in form.cleaned_data.items() if value not in ("", None)
        }
        row.data.setdefault("name", form.cleaned_data["name"])
        if kind == "organisateurs":
            statuses = _choice_codes(
                cells.get("follow_up", ""), Promoter.FollowUp, row.warnings, "Statut"
            )
            if statuses:
                row.data["follow_up"] = statuses[0]
            kinds = _choice_codes(cells.get("kinds", ""), Promoter.Kind, row.warnings, "Type")
            if kinds:
                row.data["kinds"] = kinds
        wanted = {"promoters": promoters, "venues": venues}
        for key, known in wanted.items():
            row.links[key] = []
            for name in _names(cells.get(key, "")) if key in cells else []:
                obj = known.get(name.casefold())
                if obj:
                    row.links[key].append(obj)
                else:
                    kind_word = "Organisateur" if key == "promoters" else "Lieu"
                    row.warnings.append(f"{kind_word} inconnu : « {name} » (non rattaché).")
        key = data_key(kind, row.data)
        if find_existing(tenant, kind, row.data) or key in seen:
            row.status = "duplicate"
        seen.add(key)
        result.append(row)
    return result


def data_key(kind, data):
    if kind == "contacts" and data.get("email"):
        return ("email", data["email"].casefold())
    return ("name", data["name"].casefold(), data.get("city", "").casefold())


def summary(rows):
    return {
        "new": sum(row.status == "new" for row in rows),
        "duplicate": sum(row.status == "duplicate" for row in rows),
        "error": sum(row.status == "error" for row in rows),
    }


@transaction.atomic
def apply(tenant, kind, raw_rows, update=False):
    """Do the import: returns how many were created, updated and ignored."""
    counts = {"created": 0, "updated": 0, "ignored": 0}
    model = MODELS[kind]
    for row in analyse(tenant, kind, raw_rows):
        if row.status == "error":
            counts["ignored"] += 1
            continue
        existing = find_existing(tenant, kind, row.data)
        if existing and not update:
            counts["ignored"] += 1
            continue
        if existing:
            model.objects.filter(pk=existing.pk).update(**row.data)  # no map lookup here
            target = existing
            counts["updated"] += 1
        else:
            target = model(tenant=tenant, **row.data)
            # Not `save()`: a venue would ask the map service for its place, row after row.
            model.objects.bulk_create([target])
            counts["created"] += 1
        for key, objects in row.links.items():
            if objects:
                getattr(target, key).add(*objects)
    return counts
