"""Step 2 of 3: every contact keeps exactly the organiser or venue it was attached to."""

from django.db import migrations


def copy_forward(apps, schema_editor):
    Contact = apps.get_model("addressbook", "Contact")
    for contact in Contact.objects.exclude(promoter=None).iterator():
        contact.promoters.add(contact.promoter_id)
    for contact in Contact.objects.exclude(venue=None).iterator():
        contact.venues.add(contact.venue_id)


def copy_back(apps, schema_editor):
    """Undoing: the first link goes back to the single field.

    The old schema cannot hold a contact that works for nobody, and deleting it silently would
    lose data: the undo stops with a clear message until each of them has an organiser or a venue.
    """
    Contact = apps.get_model("addressbook", "Contact")
    orphans = Contact.objects.filter(promoters=None, venues=None).count()
    if orphans:
        raise RuntimeError(
            f"{orphans} contact(s) sans rattachement : rattachez-les à un organisateur ou à un "
            "lieu avant de revenir en arrière (l'ancien schéma l'exige)."
        )
    for contact in Contact.objects.iterator():
        first_promoter = contact.promoters.order_by("pk").first()
        first_venue = contact.venues.order_by("pk").first()
        if first_promoter:
            contact.promoter_id, contact.venue_id = first_promoter.pk, None
        elif first_venue:
            contact.promoter_id, contact.venue_id = None, first_venue.pk
        contact.save(update_fields=["promoter", "venue"])


class Migration(migrations.Migration):
    dependencies = [
        ("addressbook", "0013_contact_many_links"),
    ]

    operations = [
        migrations.RunPython(copy_forward, copy_back),
    ]
