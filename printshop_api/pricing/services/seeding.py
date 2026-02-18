"""
Shop pricing seeding service.

Seeds shop pricing from default templates.
"""

from decimal import Decimal

from django.db import transaction

from shops.models import Shop
from inventory.models import Machine
from pricing.models import (
    PrintingPrice,
    PaperPrice,
    MaterialPrice,
    FinishingService,
    DefaultPrintingPriceTemplate,
    DefaultPaperPriceTemplate,
    DefaultMaterialPriceTemplate,
    DefaultFinishingServiceTemplate,
)


def seed_shop_pricing(
    shop: Shop,
    machine_ids: list[int] | None = None,
    overwrite: bool = False,
) -> dict:
    """
    Seed shop pricing from default templates.

    - Printing: For each shop machine (or filtered by machine_ids), map to template
      by machine_category (machine.machine_type); clone template rows into PrintingPrice
      if missing.
    - Paper: Clone DefaultPaperPriceTemplate into PaperPrice for shop if missing.
    - Materials: Clone DefaultMaterialPriceTemplate into MaterialPrice for shop if missing.
    - Finishing: Clone DefaultFinishingServiceTemplate into FinishingService for shop if missing.

    If overwrite=True: update existing seeded rows (is_default_seeded=True) back to template
    prices. Safe rule: DO NOT overwrite rows where needs_review=False (user has reviewed/edited).

    Returns dict with counts: created, updated, skipped.
    """
    result = {"printing": {"created": 0, "updated": 0}, "paper": {"created": 0, "updated": 0},
              "material": {"created": 0, "updated": 0}, "finishing": {"created": 0, "updated": 0}}

    with transaction.atomic():
        # Printing
        machines = Machine.objects.filter(shop=shop, is_active=True)
        if machine_ids:
            machines = machines.filter(id__in=machine_ids)

        for machine in machines:
            cat = machine.machine_type
            templates = DefaultPrintingPriceTemplate.objects.filter(machine_category=cat)
            for tpl in templates:
                existing = PrintingPrice.objects.filter(
                    shop=shop,
                    machine=machine,
                    sheet_size=tpl.sheet_size,
                    color_mode=tpl.color_mode,
                ).first()

                if existing:
                    if overwrite and existing.is_default_seeded and existing.needs_review:
                        existing.selling_price_per_side = tpl.selling_price_per_side
                        existing.selling_price_duplex_per_sheet = tpl.selling_price_duplex_per_sheet
                        existing.buying_price_per_side = None
                        existing.save(update_fields=[
                            "selling_price_per_side",
                            "selling_price_duplex_per_sheet",
                            "buying_price_per_side",
                            "updated_at",
                        ])
                        result["printing"]["updated"] += 1
                else:
                    PrintingPrice.objects.create(
                        shop=shop,
                        machine=machine,
                        sheet_size=tpl.sheet_size,
                        color_mode=tpl.color_mode,
                        selling_price_per_side=tpl.selling_price_per_side,
                        selling_price_duplex_per_sheet=tpl.selling_price_duplex_per_sheet,
                        buying_price_per_side=None,
                        is_default_seeded=True,
                        needs_review=True,
                    )
                    result["printing"]["created"] += 1

        # Paper
        for tpl in DefaultPaperPriceTemplate.objects.all():
            existing = PaperPrice.objects.filter(
                shop=shop,
                sheet_size=tpl.sheet_size,
                paper_type=tpl.paper_type,
                gsm=tpl.gsm,
            ).first()

            if existing:
                if overwrite and existing.is_default_seeded and existing.needs_review:
                    existing.selling_price = tpl.selling_price
                    existing.buying_price = tpl.buying_price or Decimal("0")
                    existing.save(update_fields=["selling_price", "buying_price", "updated_at"])
                    result["paper"]["updated"] += 1
            else:
                PaperPrice.objects.create(
                    shop=shop,
                    sheet_size=tpl.sheet_size,
                    paper_type=tpl.paper_type,
                    gsm=tpl.gsm,
                    selling_price=tpl.selling_price,
                    buying_price=tpl.buying_price or Decimal("0"),
                    is_default_seeded=True,
                    needs_review=True,
                )
                result["paper"]["created"] += 1

        # Material
        for tpl in DefaultMaterialPriceTemplate.objects.all():
            existing = MaterialPrice.objects.filter(
                shop=shop,
                material_type=tpl.material_type,
                unit=tpl.unit,
            ).first()

            if existing:
                if overwrite and existing.is_default_seeded and existing.needs_review:
                    existing.selling_price = tpl.selling_price
                    existing.buying_price = tpl.buying_price
                    existing.save(update_fields=["selling_price", "buying_price", "updated_at"])
                    result["material"]["updated"] += 1
            else:
                MaterialPrice.objects.create(
                    shop=shop,
                    material_type=tpl.material_type,
                    unit=tpl.unit,
                    selling_price=tpl.selling_price,
                    buying_price=tpl.buying_price,
                    is_default_seeded=True,
                    needs_review=True,
                )
                result["material"]["created"] += 1

        # Finishing
        for tpl in DefaultFinishingServiceTemplate.objects.all():
            existing = FinishingService.objects.filter(
                shop=shop,
                name=tpl.name,
            ).first()

            if existing:
                if overwrite and existing.is_default_seeded and existing.needs_review:
                    existing.charge_by = tpl.unit_type
                    existing.selling_price = tpl.selling_price
                    existing.buying_price = tpl.buying_price or Decimal("0")
                    existing.save(update_fields=["charge_by", "selling_price", "buying_price", "updated_at"])
                    result["finishing"]["updated"] += 1
            else:
                FinishingService.objects.create(
                    shop=shop,
                    name=tpl.name,
                    category="OTHER",
                    charge_by=tpl.unit_type,
                    selling_price=tpl.selling_price,
                    buying_price=tpl.buying_price or Decimal("0"),
                    is_default_seeded=True,
                    needs_review=True,
                )
                result["finishing"]["created"] += 1

    return result
