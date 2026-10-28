"""Step 1 of 3: a contact can work for several organisers and venues, a venue for several organisers.

The old single links keep working until step 3; they only give up the name `contacts` (taken by
the new many-to-many links) and become `legacy_contacts`.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("addressbook", "0012_venue_map_point"),
    ]

    operations = [
        # The "one or the other" rule goes first: a contact may now have no link at all.
        migrations.RemoveConstraint(
            model_name="contact",
            name="contact_belongs_to_promoter_or_venue",
        ),
        migrations.AlterField(
            model_name="contact",
            name="promoter",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="legacy_contacts",
                to="addressbook.promoter",
            ),
        ),
        migrations.AlterField(
            model_name="contact",
            name="venue",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="legacy_contacts",
                to="addressbook.venue",
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="promoters",
            field=models.ManyToManyField(
                blank=True,
                related_name="contacts",
                to="addressbook.promoter",
                verbose_name="organisateurs",
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="venues",
            field=models.ManyToManyField(
                blank=True,
                related_name="contacts",
                to="addressbook.venue",
                verbose_name="lieux",
            ),
        ),
        migrations.AddField(
            model_name="venue",
            name="promoters",
            field=models.ManyToManyField(
                blank=True,
                help_text="Les organisateurs qui font des dates dans ce lieu (facultatif).",
                related_name="venues",
                to="addressbook.promoter",
                verbose_name="organisateurs",
            ),
        ),
    ]
