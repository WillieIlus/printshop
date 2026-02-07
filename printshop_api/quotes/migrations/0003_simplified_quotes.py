# Generated migration for simplified quotes models
from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


def clear_finishing_data(apps, schema_editor):
    """Clear existing finishing data before schema change."""
    QuoteItemFinishing = apps.get_model('quotes', 'QuoteItemFinishing')
    QuoteItemFinishing.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0005_simplified_pricing'),
        ('inventory', '0002_simplified_inventory'),
        ('quotes', '0002_alter_producttemplate_options_alter_quote_options_and_more'),
    ]

    operations = [
        # Update QuoteItemPart - remove old ForeignKeys and add new ones
        migrations.RemoveField(model_name='quoteitempart', name='material'),
        migrations.RemoveField(model_name='quoteitempart', name='preferred_stock'),
        
        migrations.AddField(
            model_name='quoteitempart',
            name='paper_stock',
            field=models.ForeignKey(blank=True, help_text='Paper to use from stock', null=True, on_delete=django.db.models.deletion.PROTECT, to='inventory.paperstock'),
        ),
        migrations.AddField(
            model_name='quoteitempart',
            name='paper_gsm',
            field=models.PositiveIntegerField(blank=True, help_text='Paper weight if not using stock', null=True, verbose_name='paper GSM'),
        ),
        
        # Update print_sides choices
        migrations.AlterField(
            model_name='quoteitempart',
            name='print_sides',
            field=models.CharField(choices=[('SINGLE', 'Single-sided'), ('DOUBLE', 'Double-sided')], default='SINGLE', max_length=10, verbose_name='print sides'),
        ),
        
        # Allow machine to be null
        migrations.AlterField(
            model_name='quoteitempart',
            name='machine',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='inventory.machine'),
        ),
        
        # Clear existing finishing data first
        migrations.RunPython(clear_finishing_data, migrations.RunPython.noop),
        
        # Update QuoteItemFinishing to use FinishingService
        migrations.RemoveField(model_name='quoteitemfinishing', name='finishing_price'),
        migrations.AddField(
            model_name='quoteitemfinishing',
            name='finishing_service',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='pricing.finishingservice'),
            preserve_default=False,
        ),
    ]
