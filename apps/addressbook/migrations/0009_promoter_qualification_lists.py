from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1/3: the new multiple-choice criteria (the old fields are converted in step 2)."""

    dependencies = [
        ("addressbook", "0008_promoter_code_ape_promoter_vat_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="promoter",
            name="kinds",
            field=models.JSONField(blank=True, default=list, verbose_name="type d'organisateur"),
        ),
        migrations.AddField(
            model_name="promoter",
            name="event_types",
            field=models.JSONField(blank=True, default=list, verbose_name="type d'évènement"),
        ),
        migrations.AddField(
            model_name="promoter",
            name="aesthetics",
            field=models.JSONField(
                blank=True, default=list, verbose_name="esthétique / discipline"
            ),
        ),
        migrations.AddField(
            model_name="promoter",
            name="formats",
            field=models.JSONField(blank=True, default=list, verbose_name="format / jauge"),
        ),
        migrations.AddField(
            model_name="promoter",
            name="usual_periods",
            field=models.JSONField(blank=True, default=list, verbose_name="période habituelle"),
        ),
        migrations.AddField(
            model_name="promoter",
            name="event_roles",
            field=models.JSONField(
                blank=True, default=list, verbose_name="rôle dans l'évènement"
            ),
        ),
        migrations.AddField(
            model_name="promoter",
            name="indicative_capacity",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="jauge indicative"
            ),
        ),
        migrations.AddField(
            model_name="promoter",
            name="qualification_other",
            field=models.CharField(blank=True, max_length=255, verbose_name="autres précisions"),
        ),
        migrations.AddField(
            model_name="venue",
            name="configuration",
            field=models.CharField(
                blank=True,
                help_text="Par exemple : assis, debout, plein air.",
                max_length=255,
                verbose_name="configuration",
            ),
        ),
    ]
