from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_contract_versions_and_sequence"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="contract",
            name="generated_at",
        ),
        migrations.RemoveField(
            model_name="contract",
            name="pdf_file",
        ),
    ]
