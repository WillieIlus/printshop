"""
GSM validation for template price calculation.
Enforces template min/max/allowed_gsm_values and shop capability limits.
"""

from typing import Optional

from shops.models import Shop, ShopPaperCapability
from .pricing import DEFAULT_SHEET_SIZE


def validate_gsm_for_calculation(
    template,
    shop: Shop,
    gsm: Optional[int],
    sheet_size: Optional[str],
) -> Optional[str]:
    """
    Validate GSM for price calculation.
    - If template has allowed_gsm_values: gsm must be in list
    - Else: enforce template min_gsm/max_gsm if set
    - Also enforce shop capability min/max for the sheet_size

    Returns error message string if invalid, None if valid.
    """
    # Resolve gsm: use provided or template default
    resolved_gsm = gsm if gsm is not None else template.default_gsm
    if resolved_gsm is None:
        resolved_gsm = 300  # fallback

    size = sheet_size or DEFAULT_SHEET_SIZE

    # Template: allowed_gsm_values takes precedence
    if template.allowed_gsm_values:
        if not isinstance(template.allowed_gsm_values, list):
            return "Template has invalid allowed_gsm_values configuration."
        allowed = [int(x) for x in template.allowed_gsm_values if isinstance(x, (int, float))]
        if resolved_gsm not in allowed:
            return f"GSM {resolved_gsm} is not allowed. Choose from: {allowed}"
    else:
        # Template min/max
        if template.min_gsm is not None and resolved_gsm < template.min_gsm:
            return f"GSM {resolved_gsm} is below template minimum ({template.min_gsm})"
        if template.max_gsm is not None and resolved_gsm > template.max_gsm:
            return f"GSM {resolved_gsm} exceeds template maximum ({template.max_gsm})"

    # Shop capability for this sheet size
    try:
        capability = ShopPaperCapability.objects.get(
            shop=shop,
            sheet_size=size,
        )
    except ShopPaperCapability.DoesNotExist:
        return None  # No capability = no restriction

    if capability.min_gsm is not None and resolved_gsm < capability.min_gsm:
        return f"GSM {resolved_gsm} is below shop minimum for {size} ({capability.min_gsm})"
    if resolved_gsm > capability.max_gsm:
        return f"GSM {resolved_gsm} exceeds shop maximum for {size} ({capability.max_gsm})"

    return None
