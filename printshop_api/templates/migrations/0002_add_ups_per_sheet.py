# Generated manually for imposition support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("templates", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="printtemplate",
            name="ups_per_sheet",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Imposition: how many finished units fit on one sheet (N-Up). Used for sheets_needed calculation.",
                null=True,
                verbose_name="units per sheet",
            ),
        ),
    ]
