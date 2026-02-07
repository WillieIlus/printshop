# Generated migration for simplified pricing models
from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0001_initial'),
        ('inventory', '0001_initial'),
        ('pricing', '0004_finishingprice_description_and_more'),
    ]

    operations = [
        # Create new PrintingPrice model
        migrations.CreateModel(
            name='PrintingPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sheet_size', models.CharField(choices=[('A5', 'A5'), ('A4', 'A4'), ('A3', 'A3'), ('SRA3', 'SRA3')], default='A4', max_length=20, verbose_name='paper size')),
                ('color_mode', models.CharField(choices=[('BW', 'Black & White'), ('COLOR', 'Full Color')], default='COLOR', max_length=20, verbose_name='color')),
                ('selling_price_per_side', models.DecimalField(decimal_places=2, help_text='Price customer pays per printed side', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='selling price per side')),
                ('buying_price_per_side', models.DecimalField(blank=True, decimal_places=2, help_text='Your cost per side (optional, for tracking profit)', max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='buying price per side')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='printing_prices', to='shops.shop')),
                ('machine', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='printing_prices', to='inventory.machine')),
            ],
            options={
                'verbose_name': 'printing price',
                'verbose_name_plural': 'printing prices',
                'ordering': ['sheet_size', 'color_mode'],
            },
        ),
        migrations.AddConstraint(
            model_name='printingprice',
            constraint=models.UniqueConstraint(fields=('shop', 'machine', 'sheet_size', 'color_mode'), name='unique_printing_price'),
        ),
        
        # Create new PaperPrice model
        migrations.CreateModel(
            name='PaperPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sheet_size', models.CharField(choices=[('A5', 'A5'), ('A4', 'A4'), ('A3', 'A3'), ('SRA3', 'SRA3')], default='A3', max_length=20, verbose_name='paper size')),
                ('gsm', models.PositiveIntegerField(help_text='Paper weight: 80, 130, 150, 200, 300, etc.', validators=[django.core.validators.MinValueValidator(60), django.core.validators.MaxValueValidator(500)], verbose_name='GSM (weight)')),
                ('paper_type', models.CharField(choices=[('GLOSS', 'Gloss'), ('MATTE', 'Matte'), ('BOND', 'Bond'), ('ART', 'Art Paper')], default='GLOSS', max_length=20, verbose_name='paper type')),
                ('buying_price', models.DecimalField(decimal_places=2, help_text='What YOU pay per sheet', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='buying price')),
                ('selling_price', models.DecimalField(decimal_places=2, help_text='What CUSTOMER pays per sheet', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='selling price')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='paper_prices', to='shops.shop')),
            ],
            options={
                'verbose_name': 'paper price',
                'verbose_name_plural': 'paper prices',
                'ordering': ['sheet_size', 'gsm'],
            },
        ),
        migrations.AddConstraint(
            model_name='paperprice',
            constraint=models.UniqueConstraint(fields=('shop', 'sheet_size', 'gsm', 'paper_type'), name='unique_paper_price'),
        ),
        
        # Create new FinishingService model  
        migrations.CreateModel(
            name='FinishingService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(help_text='e.g., Matt Lamination A3, Spiral Binding', max_length=100, verbose_name='service name')),
                ('category', models.CharField(choices=[('LAMINATION', 'Lamination'), ('BINDING', 'Binding'), ('CUTTING', 'Cutting'), ('FOLDING', 'Folding'), ('OTHER', 'Other')], default='OTHER', max_length=20, verbose_name='category')),
                ('charge_by', models.CharField(choices=[('PER_SHEET', 'Per Sheet'), ('PER_PIECE', 'Per Piece/Item'), ('PER_JOB', 'Per Job (Flat Fee)')], default='PER_SHEET', max_length=20, verbose_name='charge by')),
                ('buying_price', models.DecimalField(decimal_places=2, default=Decimal('0'), help_text='Your cost (if any)', max_digits=10, verbose_name='buying price')),
                ('selling_price', models.DecimalField(decimal_places=2, help_text='Price customer pays', max_digits=10, verbose_name='selling price')),
                ('is_default', models.BooleanField(default=False, help_text='Pre-select this option for customers', verbose_name='selected by default')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finishing_services', to='shops.shop')),
            ],
            options={
                'verbose_name': 'finishing service',
                'verbose_name_plural': 'finishing services',
                'ordering': ['category', 'name'],
            },
        ),
        migrations.AddConstraint(
            model_name='finishingservice',
            constraint=models.UniqueConstraint(fields=('shop', 'name'), name='unique_finishing_service'),
        ),
        
        # Remove old models that are no longer needed
        migrations.DeleteModel(name='PricingEngine'),
        migrations.DeleteModel(name='FinishingOption'),
        migrations.DeleteModel(name='RawMaterial'),
        migrations.DeleteModel(name='PricingVariable'),
        migrations.DeleteModel(name='PricingTier'),
        migrations.DeleteModel(name='MaterialPrice'),
        migrations.DeleteModel(name='PaperGSMPrice'),
        
        # Update VolumeDiscount to simplified structure
        migrations.RemoveField(model_name='volumediscount', name='discount_type'),
        migrations.RemoveField(model_name='volumediscount', name='discount_value'),
        migrations.RemoveField(model_name='volumediscount', name='applies_to_print'),
        migrations.RemoveField(model_name='volumediscount', name='applies_to_material'),
        migrations.RemoveField(model_name='volumediscount', name='applies_to_finishing'),
        migrations.RemoveField(model_name='volumediscount', name='minimum_quantity'),
        migrations.RemoveField(model_name='volumediscount', name='maximum_quantity'),
        migrations.AddField(
            model_name='volumediscount',
            name='min_quantity',
            field=models.PositiveIntegerField(default=100, help_text='Minimum sheets/items to qualify', verbose_name='minimum quantity'),
        ),
        migrations.AddField(
            model_name='volumediscount',
            name='discount_percent',
            field=models.DecimalField(decimal_places=2, default=Decimal('10'), help_text='Percentage discount (e.g., 10 for 10%)', max_digits=5, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('100'))], verbose_name='discount %'),
        ),
    ]
