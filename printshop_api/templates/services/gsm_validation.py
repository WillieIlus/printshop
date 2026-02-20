"""
GSM constraint validation for template price calculation.

Enforces:
- Template constraints: allowed_gsm_values, min_gsm, max_gsm
- Shop capability constraints: max_gsm (and optional min_gsm) per sheet_size
- Effective range = intersection(template range, shop capability range)
"""

from shops.models import Shop, ShopPaperCapability


def validate_gsm_for_calculation(
    template,
    gsm: int,
    sheet_size: str,
    shop=None,
) -> None:
    """
    Validate GSM against template and shop constraints.
    Raises ValueError with a clear message on violation.
    """
    # Resolve effective shop: use provided shop or template's created_by_shop
    effective_shop = shop or (template.created_by_shop if template.created_by_shop_id else None)

    # Template constraints
    if template.allowed_gsm_values:
        allowed = template.allowed_gsm_values
        if not isinstance(allowed, list):
            allowed = list(allowed) if allowed else []
        if gsm not in allowed:
            values_str = ", ".join(str(v) for v in sorted(allowed))
            raise ValueError(f"This template only allows GSM: {values_str}")
    else:
        # Use min/max if provided
        t_min = template.min_gsm
        t_max = template.max_gsm
        if t_min is not None and gsm < t_min:
            if t_max is not None:
                raise ValueError(f"This template requires {t_min}–{t_max}gsm")
            raise ValueError(f"This template requires at least {t_min}gsm")
        if t_max is not None and gsm > t_max:
            if t_min is not None:
                raise ValueError(f"This template requires {t_min}–{t_max}gsm")
            raise ValueError(f"This template allows up to {t_max}gsm")

    # Shop capability constraints (when shop is specified)
    if effective_shop:
        capability = ShopPaperCapability.objects.filter(
            shop=effective_shop,
            sheet_size=sheet_size,
        ).first()
        if capability:
            if gsm > capability.max_gsm:
                raise ValueError(
                    f"This shop supports up to {capability.max_gsm}gsm for {sheet_size}"
                )
            if capability.min_gsm is not None and gsm < capability.min_gsm:
                raise ValueError(
                    f"This shop requires at least {capability.min_gsm}gsm for {sheet_size}"
                )
