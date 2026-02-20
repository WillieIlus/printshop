# Generated manually for shop ownership and GSM constraints

import django.db.models.deletion
from django.db import migrations, models


def assign_templates_to_default_shop(apps, schema_editor):
    """Assign existing templates to first active shop, or create one."""
    PrintTemplate = apps.get_model("templates", "PrintTemplate")
    Shop = apps.get_model("shops", "Shop")
    User = apps.get_model("accounts", "User")

    if PrintTemplate.objects.filter(shop__isnull=True).exists():
        shop = Shop.objects.filter(is_active=True).first()
        if shop is None:
            # Create default shop with a system user
            user = User.objects.filter(is_superuser=True).first()
            if user is None:
                user = User.objects.first()
            if user is None:
                user = User.objects.create_user(
                    email="migration@system.local",
                    password="migration_temp_password",
                )
            shop = Shop.objects.create(
                owner=user,
                name="Default Shop",
                slug="default-shop",
                business_email="default@shop.local",
                address_line="Migration default",
                city="Default",
                zip_code="00000",
                country="Default",
                is_active=True,
            )
        PrintTemplate.objects.filter(shop__isnull=True).update(shop=shop)


class Migration(migrations.Migration):

    dependencies = [
        ("shops", "0001_initial"),
        ("templates", "0001_initial"),
    ]

    operations = [
        # Step 1: Add shop FK nullable
        migrations.AddField(
            model_name="printtemplate",
            name="shop",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="templates",
                to="shops.shop",
                help_text="The shop that owns this template",
            ),
        ),
        # Step 2: Add GSM constraint fields
        migrations.AddField(
            model_name="printtemplate",
            name="min_gsm",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="minimum GSM",
                help_text="Minimum allowed paper weight",
            ),
        ),
        migrations.AddField(
            model_name="printtemplate",
            name="max_gsm",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="maximum GSM",
                help_text="Maximum allowed paper weight",
            ),
        ),
        migrations.AddField(
            model_name="printtemplate",
            name="allowed_gsm_values",
            field=models.JSONField(
                blank=True,
                null=True,
                verbose_name="allowed GSM values",
                help_text="Optional list of allowed GSM values (e.g. [200, 300, 350])",
            ),
        ),
        # Step 3: Assign existing templates to default shop
        migrations.RunPython(assign_templates_to_default_shop, migrations.RunPython.noop),
        # Step 4: Make shop required
        migrations.AlterField(
            model_name="printtemplate",
            name="shop",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="templates",
                to="shops.shop",
                help_text="The shop that owns this template",
            ),
        ),
        # Step 5: Change slug from unique to unique per shop
        migrations.AlterField(
            model_name="printtemplate",
            name="slug",
            field=models.SlugField(
                blank=True,
                max_length=200,
                verbose_name="slug",
            ),
        ),
        migrations.AddConstraint(
            model_name="printtemplate",
            constraint=models.UniqueConstraint(
                fields=("shop", "slug"),
                name="unique_template_slug_per_shop",
            ),
        ),
    ]
