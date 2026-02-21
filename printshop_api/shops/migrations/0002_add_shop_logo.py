# Generated manually for shop-owned templates gallery

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='shop',
            name='logo',
            field=models.ImageField(
                blank=True,
                help_text='Shop logo for gallery display.',
                null=True,
                upload_to='shops/logos/',
                verbose_name='logo',
            ),
        ),
    ]
