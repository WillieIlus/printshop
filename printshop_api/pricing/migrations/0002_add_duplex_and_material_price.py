# Generated manually for duplex override and MaterialPrice

import django.core.validators
from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0001_initial'),
        ('pricing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='printingprice',
            name='selling_price_duplex_per_sheet',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Optional: Price for duplex (both sides) per sheet. If set, overrides 2× per-side for duplex jobs.',
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                verbose_name='selling price duplex per sheet'
            ),
        ),
        migrations.CreateModel(
            name='MaterialPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('material_type', models.CharField(
                    choices=[('BANNER', 'Banner'), ('VINYL', 'Vinyl'), ('REFLECTIVE', 'Reflective'), ('PAPER', 'Paper')],
                    max_length=20,
                    verbose_name='material type'
                )),
                ('unit', models.CharField(
                    choices=[('SHEET_A4', 'Sheet A4'), ('SHEET_A3', 'Sheet A3'), ('SHEET_SRA3', 'Sheet SRA3'), ('SQM', 'Per Square Metre')],
                    max_length=20,
                    verbose_name='unit'
                )),
                ('selling_price', models.DecimalField(
                    decimal_places=2,
                    help_text='What CUSTOMER pays per unit',
                    max_digits=10,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                    verbose_name='selling price'
                )),
                ('buying_price', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text='What YOU pay per unit (optional)',
                    max_digits=10,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                    verbose_name='buying price'
                )),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('shop', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='material_prices',
                    to='shops.shop'
                )),
            ],
            options={
                'verbose_name': 'material price',
                'verbose_name_plural': 'material prices',
                'ordering': ['material_type', 'unit'],
            },
        ),
        migrations.AddConstraint(
            model_name='materialprice',
            constraint=models.UniqueConstraint(
                fields=('shop', 'material_type', 'unit'),
                name='unique_material_price'
            ),
        ),
    ]
