from django.db import migrations, models


def set_variant(apps, schema_editor):
    """Old versions get the variant their structure's VAT regime would choose today."""
    ContractVersion = apps.get_model("documents", "ContractVersion")
    ContractVersion.objects.exclude(tenant__vat_regime="taxable").update(variant="no_vat")


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0015_contract_checks"),
    ]

    operations = [
        migrations.AddField(
            model_name="contractversion",
            name="fiscal_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="contractversion",
            name="parties_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="contractversion",
            name="variant",
            field=models.CharField(
                choices=[("vat", "Avec TVA"), ("no_vat", "Sans TVA")],
                default="vat",
                max_length=10,
                verbose_name="variante",
            ),
        ),
        migrations.RunPython(set_variant, migrations.RunPython.noop),
        migrations.RemoveField(model_name="contract", name="template"),
        migrations.RemoveField(model_name="contractversion", name="template"),
    ]
