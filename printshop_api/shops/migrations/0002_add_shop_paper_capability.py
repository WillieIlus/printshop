# Generated manually for ShopPaperCapability

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shops", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShopPaperCapability",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="created at")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="updated at")),
                (
                    "sheet_size",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("A5", "A5"),
                            ("A4", "A4"),
                            ("A3", "A3"),
                            ("SRA3", "SRA3"),
                        ],
                        verbose_name="sheet size",
                    ),
                ),
                (
                    "max_gsm",
                    models.PositiveIntegerField(
                        help_text="Maximum paper weight this shop can handle for this size",
                        verbose_name="maximum GSM",
                    ),
                ),
                (
                    "min_gsm",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Optional minimum paper weight",
                        null=True,
                        verbose_name="minimum GSM",
                    ),
                ),
                (
                    "shop",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="paper_capabilities",
                        to="shops.shop",
                    ),
                ),
            ],
            options={
                "verbose_name": "shop paper capability",
                "verbose_name_plural": "shop paper capabilities",
            },
        ),
        migrations.AddConstraint(
            model_name="shoppapercapability",
            constraint=models.UniqueConstraint(
                fields=("shop", "sheet_size"),
                name="unique_shop_sheet_size_capability",
            ),
        ),
    ]
