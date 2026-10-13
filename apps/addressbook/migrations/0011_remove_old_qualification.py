from django.db import migrations


class Migration(migrations.Migration):
    """Step 3/3: the old single-value fields are no longer used."""

    dependencies = [
        ("addressbook", "0010_convert_qualification"),
    ]

    operations = [
        migrations.RemoveField(model_name="promoter", name="kind"),
        migrations.RemoveField(model_name="promoter", name="event_type"),
        migrations.RemoveField(model_name="promoter", name="aesthetic"),
    ]
