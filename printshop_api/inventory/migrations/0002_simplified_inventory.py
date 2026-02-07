# Generated migration for simplified inventory models
from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0001_initial'),
        ('inventory', '0001_initial'),
    ]

    operations = [
        # Simplify Machine model
        migrations.RemoveField(model_name='machine', name='type'),
        migrations.AddField(
            model_name='machine',
            name='machine_type',
            field=models.CharField(choices=[('DIGITAL', 'Digital Printer'), ('LARGE_FORMAT', 'Large Format'), ('OFFSET', 'Offset Press'), ('FINISHING', 'Finishing Equipment')], default='DIGITAL', max_length=20, verbose_name='type'),
        ),
        migrations.AddField(
            model_name='machine',
            name='max_paper_width',
            field=models.PositiveIntegerField(blank=True, help_text='Maximum paper width this machine can handle', null=True, verbose_name='max width (mm)'),
        ),
        migrations.AddField(
            model_name='machine',
            name='max_paper_height',
            field=models.PositiveIntegerField(blank=True, help_text='Maximum paper height this machine can handle', null=True, verbose_name='max height (mm)'),
        ),
        
        # Create PaperStock model
        migrations.CreateModel(
            name='PaperStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sheet_size', models.CharField(choices=[('A5', 'A5 (148 × 210 mm)'), ('A4', 'A4 (210 × 297 mm)'), ('A3', 'A3 (297 × 420 mm)'), ('SRA3', 'SRA3 (320 × 450 mm)'), ('SRA4', 'SRA4 (225 × 320 mm)')], default='SRA3', max_length=20, verbose_name='paper size')),
                ('gsm', models.PositiveIntegerField(help_text='Paper weight: 80, 130, 150, 200, 300, etc.', verbose_name='GSM (weight)')),
                ('paper_type', models.CharField(choices=[('GLOSS', 'Gloss'), ('MATTE', 'Matte'), ('BOND', 'Bond'), ('ART', 'Art Paper')], default='GLOSS', max_length=20, verbose_name='paper type')),
                ('width_mm', models.PositiveIntegerField(help_text='Width in millimeters', verbose_name='width (mm)')),
                ('height_mm', models.PositiveIntegerField(help_text='Height in millimeters', verbose_name='height (mm)')),
                ('quantity_in_stock', models.PositiveIntegerField(default=0, help_text='Number of sheets currently in stock', verbose_name='quantity in stock')),
                ('reorder_level', models.PositiveIntegerField(default=100, help_text='Order more when stock falls below this level', verbose_name='reorder level')),
                ('buying_price_per_sheet', models.DecimalField(blank=True, decimal_places=2, help_text='Your cost per sheet', max_digits=10, null=True, verbose_name='buying price per sheet')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='paper_stock', to='shops.shop')),
            ],
            options={
                'verbose_name': 'paper stock',
                'verbose_name_plural': 'paper stocks',
                'ordering': ['sheet_size', 'gsm'],
            },
        ),
        migrations.AddConstraint(
            model_name='paperstock',
            constraint=models.UniqueConstraint(fields=('shop', 'sheet_size', 'gsm', 'paper_type'), name='unique_paper_stock'),
        ),
    ]
