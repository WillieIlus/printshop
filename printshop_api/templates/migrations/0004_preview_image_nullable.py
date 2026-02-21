# Generated manually for shop-owned templates gallery

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('templates', '0003_add_shop_and_gsm_constraints'),
    ]

    operations = [
        migrations.AlterField(
            model_name='printtemplate',
            name='preview_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='templates/previews/',
                verbose_name='preview image',
            ),
        ),
    ]
