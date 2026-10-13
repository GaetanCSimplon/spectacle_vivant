import unicodedata

from django.db import migrations

# Old single-choice "type d'organisateur" -> new value. The bar is a venue; "other" stays.
KIND_MAP = {
    "municipality": "municipality",
    "festival": "festival",
    "venue": "venue",
    "association": "association",
    "bar": "venue",
    "other": "other",
}

# Free texts are matched with the labels of the new lists (no case, no accent), plus the few
# old proposals that clearly mean one of them. Anything else goes to the notes.
EVENT_TYPES = {
    "concert": "concert",
    "festival": "festival",
    "saison culturelle": "cultural_season",
    "evenement municipal": "municipal_event",
    "evenement prive": "private_event",
    "salon": "trade_show",
    "action culturelle": "cultural_action",
    "fete locale": "municipal_event",
    "soiree privee": "private_event",
}
AESTHETICS = {
    "chanson": "chanson",
    "musiques actuelles": "contemporary_music",
    "jazz": "jazz",
    "classique": "classical",
    "musique classique": "classical",
    "theatre": "theatre",
    "danse": "dance",
    "cirque": "circus",
    "arts de la rue": "street_arts",
    "pluridisciplinaire": "multidisciplinary",
}


def _plain(text):
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


def convert(apps, schema_editor):
    Promoter = apps.get_model("addressbook", "Promoter")
    for promoter in Promoter.objects.exclude(kind="", event_type="", aesthetic="").iterator():
        lost = []
        if promoter.kind in KIND_MAP:
            promoter.kinds = [KIND_MAP[promoter.kind]]
        for old, new, mapping, title in (
            (promoter.event_type, "event_types", EVENT_TYPES, "Type d'évènement"),
            (promoter.aesthetic, "aesthetics", AESTHETICS, "Esthétique"),
        ):
            if not old:
                continue
            value = mapping.get(_plain(old))
            if value:
                setattr(promoter, new, [value])
            else:
                lost.append(f"{title} : {old}")
        if lost:
            promoter.notes = "\n".join(filter(None, [promoter.notes, *lost]))
        promoter.save(update_fields=["kinds", "event_types", "aesthetics", "notes"])


class Migration(migrations.Migration):
    """Step 2/3: carry the existing values over to the new lists, without losing any."""

    dependencies = [
        ("addressbook", "0009_promoter_qualification_lists"),
    ]

    operations = [
        migrations.RunPython(convert, migrations.RunPython.noop),
    ]
