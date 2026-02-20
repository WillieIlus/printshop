# Discovery Report: Template Price Calculation Endpoint

## 1. Endpoint URL Patterns

| Endpoint | Method | View | URL |
|----------|--------|------|-----|
| Template calculate-price | POST | `PrintTemplateViewSet.calculate_price` | `/api/templates/{slug}/calculate-price/` |
| Shop calculate-price | POST | `CalculatePriceView` | `/api/shops/{slug}/calculate-price/` |

Template router: `router.register(r"", PrintTemplateViewSet, basename="template")` under `api/templates/`.

## 2. Request Payload Fields (TemplatePriceCalculationSerializer)

**Common:**
- `quantity` (required, int, min_value=1)

**Digital mode:**
- `sheet_size` (optional: A5, A4, A3, SRA3)
- `print_sides` (optional: SIMPLEX, DUPLEX)
- `gsm` (optional, 60-500)
- `paper_type` (optional: GLOSS, MATTE, BOND, ART)
- `machine_id` (optional)

**Large format mode:**
- `unit` (optional: SHEET, SQM)
- `width_m`, `height_m`, `area_sqm` (optional decimals)
- `material_type` (optional: BANNER, VINYL, REFLECTIVE)

**Options:**
- `selected_option_ids` (optional list of ints)
- `selected_finishing_ids` (optional list of ints)

**Note:** No `shop_id` in current serializer.

## 3. Response Structure (from calculate_template_price)

```json
{
  "printing": { "amount": "KES ...", "details": {...} },
  "material": { "amount": "KES ...", "details": {...} },
  "finishing": { "amount": "KES ...", "items": [...] },
  "subtotal": "KES ...",
  "total": "KES ...",
  "notes": ["Demo estimate only - actual price may vary"]
}
```

Optional: `options` when option_modifiers != 0.

## 4. Shop-Scoped vs Global

- **Template endpoint** (`/api/templates/{slug}/calculate-price/`): **GLOBAL** – no shop in URL or payload. Uses STRATEGY 1: `base_price` + deltas (public demo, no shop-specific pricing).
- **Shop endpoint** (`/api/shops/{slug}/calculate-price/`): **SHOP-SCOPED** – shop from URL. Uses `PriceCalculator` with shop's pricing.

## 5. Models

- **PrintTemplate**: Has `base_price`, `min_quantity`, `final_width`, `final_height`, `default_gsm`, `default_print_sides`. **No `ups_per_sheet` or imposition fields.**
- **TemplateCategory**: Category for templates.
- **QuoteCalculator.calculate_imposition()**: Exists in `quotes/services.py` – computes items per sheet from part dimensions and stock dimensions.

## 6. Serializer Used by Calculate Endpoint

`TemplatePriceCalculationSerializer` – validates request. Response is built directly by `calculate_template_price()` in `templates/services/pricing.py`.
