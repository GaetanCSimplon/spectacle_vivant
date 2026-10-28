"""Step 3 of 3: the single links are gone (their "one or the other" rule went in step 1)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("addressbook", "0014_copy_contact_links"),
    ]

    operations = [
        migrations.RemoveField(model_name="contact", name="promoter"),
        migrations.RemoveField(model_name="contact", name="venue"),
        migrations.AlterModelOptions(name="contact", options={"ordering": ["name"]}),
    ]
