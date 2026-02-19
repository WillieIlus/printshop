"""
Template price calculation service.

Uses STRATEGY 1: base_price as starting point with deltas for options/finishings.
Public demo calculator - no shop-specific pricing.
"""

from decimal import Decimal
from typing import Any

from ..models import PrintTemplate, TemplateFinishing, TemplateOption


# Duplex multiplier: duplex is ~1.4x simplex (not 2x) for realistic pricing
DUPLEX_MULTIPLIER = Decimal("1.4")

# GSM price factor: each +50gsm above default adds this % to material component
GSM_FACTOR_PER_50 = Decimal("0.05")  # 5% per 50gsm

# Default sheet size when template doesn't specify
DEFAULT_SHEET_SIZE = "A4"

# Paper type choices (align with pricing.PaperPrice)
PAPER_TYPES = ("GLOSS", "MATTE", "BOND", "ART")

# Large format material types
MATERIAL_TYPES = ("BANNER", "VINYL", "REFLECTIVE")


def _format_kes(amount: Decimal) -> str:
    """Format amount as KES string."""
    return f"KES {amount:,.2f}"


def _get_duplex_multiplier(template: PrintTemplate, print_sides: str) -> Decimal:
    """
    Duplex is ~1.4x simplex (not 2x).
    base_price is for template.default_print_sides.
    """
    default = template.default_print_sides or "DUPLEX"
    if print_sides == default:
        return Decimal("1")
    if print_sides == "DUPLEX":
        return DUPLEX_MULTIPLIER  # 1.4x when upgrading to duplex
    return Decimal("1") / DUPLEX_MULTIPLIER  # ~0.714 when downgrading to simplex


def _get_gsm_factor(template: PrintTemplate, gsm: int) -> Decimal:
    """Each +50gsm above default adds 5% to material."""
    default_gsm = template.default_gsm or 300
    gsm_diff = max(0, gsm - default_gsm)
    steps = gsm_diff // 50
    return Decimal("1") + (GSM_FACTOR_PER_50 * steps)


def _calculate_digital_printing(
    template: PrintTemplate,
    quantity: int,
    print_sides: str,
    unit_price: Decimal,
) -> tuple[Decimal, dict]:
    """
    Calculate printing component for digital (sheet-based).
    Duplex uses 1.4x multiplier, not 2x.
    """
    sides = 2 if print_sides == "DUPLEX" else 1
    mult = _get_duplex_multiplier(template, print_sides)
    # Printing is ~60% of unit price
    print_portion = unit_price * Decimal("0.6")
    printing_total = print_portion * mult * quantity
    details = {
        "sides": sides,
        "print_sides": print_sides,
        "quantity": quantity,
        "duplex_multiplier": str(mult),
    }
    return printing_total, details


def _calculate_digital_material(
    template: PrintTemplate,
    quantity: int,
    gsm: int,
    unit_price: Decimal,
) -> tuple[Decimal, dict]:
    """
    Calculate material (paper) component.
    GSM above default adds price factor.
    """
    gsm_factor = _get_gsm_factor(template, gsm)
    default_gsm = template.default_gsm or 300
    # Material is ~40% of base
    material_per_sheet = unit_price * Decimal("0.4") * gsm_factor
    material_total = material_per_sheet * quantity
    details = {
        "gsm": gsm,
        "default_gsm": default_gsm,
        "gsm_factor": str(gsm_factor),
        "quantity": quantity,
    }
    return material_total, details


def _calculate_finishing(
    template: PrintTemplate,
    quantity: int,
    selected_finishing_ids: list[int],
) -> tuple[Decimal, list[dict]]:
    """
    Calculate finishing costs.
    Mandatory finishings always included.

    TemplateFinishing uses price_adjustment as per-sheet cost.
    """
    total = Decimal("0")
    items = []

    # Mandatory finishings (always included)
    mandatory = template.finishing_options.filter(is_mandatory=True)
    for fin in mandatory:
        cost = fin.price_adjustment * quantity
        total += cost
        items.append({
            "id": fin.id,
            "name": fin.name,
            "is_mandatory": True,
            "unit_type": "PER_SHEET",
            "price_per_unit": str(fin.price_adjustment),
            "quantity": quantity,
            "total": str(cost),
        })

    # Optional selected finishings
    if selected_finishing_ids:
        optional = template.finishing_options.filter(
            id__in=selected_finishing_ids,
            is_mandatory=False,
        )
        for fin in optional:
            cost = fin.price_adjustment * quantity
            total += cost
            items.append({
                "id": fin.id,
                "name": fin.name,
                "is_mandatory": False,
                "unit_type": "PER_SHEET",
                "price_per_unit": str(fin.price_adjustment),
                "quantity": quantity,
                "total": str(cost),
            })

    return total, items


def calculate_template_price(
    template: PrintTemplate,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate template price using STRATEGY 1 (base_price + deltas).

    Supports:
    - Digital mode: quantity, sheet_size, print_sides, gsm, paper_type,
      selected_option_ids, selected_finishing_ids
    - Large format mode: unit=SQM, width_m, height_m (or area_sqm),
      quantity, material_type

    Returns breakdown dict with printing, material, finishing, subtotal, total.
    """
    notes = ["Demo estimate only - actual price may vary"]

    # Detect mode: large format if area/width/height/material_type present
    is_large_format = (
        input_data.get("unit") == "SQM"
        or input_data.get("area_sqm") is not None
        or (input_data.get("width_m") is not None and input_data.get("height_m") is not None)
        or input_data.get("material_type") is not None
    )

    if is_large_format:
        return _calculate_large_format_price(template, input_data, notes)
    return _calculate_digital_price(template, input_data, notes)


def _calculate_large_format_price(
    template: PrintTemplate,
    input_data: dict[str, Any],
    notes: list[str],
) -> dict[str, Any]:
    """Calculate price for large format (area-based)."""
    quantity = input_data["quantity"]
    material_type = input_data.get("material_type", "BANNER")

    # Area: from area_sqm or width_m * height_m
    area_sqm = input_data.get("area_sqm")
    if area_sqm is None:
        width_m = input_data.get("width_m") or Decimal("1")
        height_m = input_data.get("height_m") or Decimal("1")
        area_sqm = Decimal(str(width_m)) * Decimal(str(height_m))
    else:
        area_sqm = Decimal(str(area_sqm))

    # Large format: base_price is per sqm, total = base_price * area_sqm * quantity
    material_total = template.base_price * area_sqm * quantity

    # Finishing for large format (per piece)
    finishing_total, finishing_items = _calculate_finishing(
        template, quantity, input_data.get("selected_finishing_ids", [])
    )

    subtotal = material_total + finishing_total
    total = subtotal

    return {
        "printing": {
            "amount": _format_kes(Decimal("0")),
            "details": {"note": "Bundled with material for large format"},
        },
        "material": {
            "amount": _format_kes(material_total),
            "details": {
                "area_sqm": str(area_sqm),
                "quantity": quantity,
                "material_type": material_type,
            },
        },
        "finishing": {
            "amount": _format_kes(finishing_total),
            "items": finishing_items,
        },
        "subtotal": _format_kes(subtotal),
        "total": _format_kes(total),
        "notes": notes,
    }


def _calculate_digital_price(
    template: PrintTemplate,
    input_data: dict[str, Any],
    notes: list[str],
) -> dict[str, Any]:
    """Calculate price for digital (sheet-based)."""
    quantity = input_data["quantity"]
    print_sides = input_data.get("print_sides") or template.default_print_sides or "DUPLEX"
    gsm = input_data.get("gsm") or template.default_gsm or 300

    # Unit price per sheet at default config (base_price is for min_quantity)
    min_qty = max(1, template.min_quantity)
    unit_price = template.base_price / min_qty

    # Option modifiers (total add-on for selected options)
    selected_option_ids = input_data.get("selected_option_ids", [])
    option_modifiers = Decimal("0")
    if selected_option_ids:
        options = TemplateOption.objects.filter(
            id__in=selected_option_ids,
            template=template,
        )
        option_modifiers = sum(opt.price_modifier for opt in options)

    # Printing and material components
    printing_total, printing_details = _calculate_digital_printing(
        template, quantity, print_sides, unit_price
    )
    material_total, material_details = _calculate_digital_material(
        template, quantity, gsm, unit_price
    )

    # Finishing
    finishing_total, finishing_items = _calculate_finishing(
        template, quantity, input_data.get("selected_finishing_ids", [])
    )

    # Subtotal = printing + material + finishing + options
    subtotal = printing_total + material_total + finishing_total + option_modifiers
    total = subtotal

    response = {
        "printing": {
            "amount": _format_kes(printing_total),
            "details": {
                **printing_details,
                "sheet_size": input_data.get("sheet_size", DEFAULT_SHEET_SIZE),
            },
        },
        "material": {
            "amount": _format_kes(material_total),
            "details": material_details,
        },
        "finishing": {
            "amount": _format_kes(finishing_total),
            "items": finishing_items,
        },
        "subtotal": _format_kes(subtotal),
        "total": _format_kes(total),
        "notes": notes,
    }
    if option_modifiers != 0:
        response["options"] = {
            "amount": _format_kes(option_modifiers),
            "details": {"selected_option_ids": selected_option_ids},
        }
    return response
