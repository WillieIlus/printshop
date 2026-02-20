# Phase 1: Discovery Report

## 1) Existing Apps and Models

### accounts (User/Profile)
- **User**: email, first_name, last_name, is_staff, is_active, date_joined (AUTH_USER_MODEL)
- **Profile**: user (1:1), bio, avatar, website, location, birth_date
- **SocialLink**: profile FK, platform, url, username, is_primary

### shops
- **Shop**: owner FK, name, slug, description, business_email, phone_number, address_line, city, state, zip_code, country, latitude, longitude, is_verified, is_active
- **ShopMember**: shop FK, user FK, role (OWNER/MANAGER/STAFF/DESIGNER), is_active
- **OpeningHours**: shop FK, weekday, from_hour, to_hour, is_closed
- **ShopSocialLink**: shop FK, platform, url, username
- **ShopClaim**: user FK, shop FK (nullable), business_name, business_email, status, token

### inventory
- **Machine**: shop FK, name, machine_type (DIGITAL/LARGE_FORMAT/OFFSET/FINISHING), max_paper_width, max_paper_height, is_active
- **PaperStock**: shop FK, sheet_size, gsm, paper_type, width_mm, height_mm, quantity_in_stock, reorder_level, buying_price_per_sheet, is_active
- **MachineCapability** (legacy): machine FK, feed_type, max_width, max_height
- **Note**: `Material` and `MaterialStock` are aliases for `PaperStock`; MaterialViewSet/MaterialStockViewSet reference fields (name, type, label, width, height, current_stock_level) that do not exist on PaperStock — likely broken/legacy.

### pricing
- **PrintingPrice**: shop FK, machine FK, sheet_size, color_mode, selling_price_per_side, selling_price_duplex_per_sheet, buying_price_per_side, is_active
- **PaperPrice**: shop FK, sheet_size, gsm, paper_type, buying_price, selling_price, is_active
- **MaterialPrice**: shop FK, material_type, unit, selling_price, buying_price, is_active
- **FinishingService**: shop FK, name, category, charge_by, buying_price, selling_price, is_default, is_active
- **VolumeDiscount**: shop FK, name, min_quantity, discount_percent, is_active
- **Default*Template** models for seeding new shops

### templates
- **TemplateCategory**: name, slug, icon_svg_path, description, display_order, is_active (global, no shop FK)
- **PrintTemplate**: category FK, title, slug, description, base_price, min_quantity, final_width, final_height, default_gsm, default_print_sides, ups_per_sheet, preview_image, dimensions_label, weight_label, is_popular, is_best_value, is_new, is_active (global, no shop FK)
- **TemplateFinishing**: template FK, name, description, is_mandatory, is_default, price_adjustment, display_order
- **TemplateOption**: template FK, option_type, label, value, price_modifier, is_default, display_order
- **Gap**: No `min_gsm`, `max_gsm` on PrintTemplate; templates are global, not shop-scoped.

---

## 2) Current DRF Endpoints and Permissions

| Endpoint | Methods | Permission |
|----------|---------|------------|
| **Shops** | | |
| `/api/shops/` | GET | AllowAny |
| `/api/shops/` | POST | IsAuthenticated |
| `/api/shops/{slug}/` | GET | AllowAny |
| `/api/shops/{slug}/` | PUT/PATCH | IsShopManagerOrOwner |
| `/api/shops/{slug}/` | DELETE | IsShopOwner |
| `/api/shops/my-shops/` | GET | IsAuthenticated |
| `/api/shops/{slug}/transfer-ownership/` | POST | IsShopOwner |
| `/api/shops/{slug}/members/` | GET, POST | IsShopMember / CanManageShopMembers |
| `/api/shops/{slug}/members/{id}/` | GET, PUT, PATCH, DELETE | IsShopMember / CanManageShopMembers |
| `/api/shops/{slug}/hours/` | GET | AllowAny; POST/PUT/DELETE | IsShopManagerOrOwner |
| `/api/shops/{slug}/social-links/` | GET | AllowAny; POST/PUT/DELETE | IsShopManagerOrOwner |
| `/api/shops/{slug}/rate-card/` | GET | AllowAny |
| `/api/shops/{slug}/calculate-price/` | POST | AllowAny |
| **Machines** | | |
| `/api/shops/{slug}/machines/` | CRUD | IsShopMember (list/retrieve), IsShopManagerOrOwner (create/update/delete) |
| **Pricing** | | |
| `/api/shops/{slug}/pricing/printing/` | CRUD | IsShopMember |
| `/api/shops/{slug}/pricing/paper/` | CRUD | IsShopMember |
| `/api/shops/{slug}/pricing/material/` | CRUD | IsShopMember |
| `/api/shops/{slug}/pricing/finishing/` | CRUD | IsShopMember |
| `/api/shops/{slug}/pricing/discounts/` | CRUD | IsShopOwner |
| `/api/shops/{slug}/pricing/seed-defaults/` | POST | IsShopOwner |
| `/api/shops/{slug}/pricing/status/` | GET | IsShopMember |
| **Templates** (global gallery) | | |
| `/api/templates/` | GET | AllowAny |
| `/api/templates/{slug}/` | GET | AllowAny |
| `/api/templates/{slug}/calculate-price/` | POST | AllowAny |
| `/api/templates/{slug}/create-quote/` | POST | IsAuthenticated |
| `/api/templates/categories/` | GET | AllowAny |
| **Gaps**: No shop-scoped template CRUD; no `/api/shops/{slug}/templates/` or `/api/shops/{slug}/templates/categories/`. |

---

## 3) Current Django Admin Registrations

| Model | Admin | list_display | Inlines | list_editable |
|-------|-------|--------------|---------|---------------|
| **User** | UserAdmin | email, first_name, last_name, is_staff, is_active, date_joined | ProfileInline | — |
| **Profile** | ProfileAdmin | user, location, website, birth_date | SocialLinkInline | — |
| **Shop** | ShopAdmin | name, slug, owner_email, city, state, country, is_verified, is_active, member_count, created_at | ShopMemberInline, OpeningHoursInline, ShopSocialLinkInline, ShopClaimInline | — |
| **Machine** | MachineAdmin | shop, name, machine_type, max_size_display, is_active | None | is_active |
| **PrintingPrice** | PrintingPriceAdmin | shop, machine, sheet_size, color_mode, selling_price_display, buying_price_display, profit_display, is_active | None | is_active |
| **PaperPrice** | PaperPriceAdmin | shop, sheet_size, gsm, paper_type, buying_price, selling_price, profit_display, margin_display, is_active | None | buying_price, selling_price, is_active |
| **MaterialPrice** | MaterialPriceAdmin | shop, material_type, unit, selling_price, buying_price_display, is_active | None | selling_price, is_active |
| **FinishingService** | FinishingServiceAdmin | shop, name, category, charge_by, selling_price, buying_price_display, profit_display, is_default, is_active | None | selling_price, is_default, is_active |
| **TemplateCategory** | TemplateCategoryAdmin | name, slug, display_order, template_count, is_active, created_at | None | display_order, is_active |
| **PrintTemplate** | PrintTemplateAdmin | title, category, base_price_display, dimensions_label, weight_label, badges_display, is_active, created_at | TemplateFinishingInline, TemplateOptionInline | is_active |

**Gaps** (addressed in implementation):
- Shop admin: no Machines inline; no readonly counts for pricing/templates → **FIXED**: MachineInline, machine_count, pricing_count, template_count
- Machine admin: no PrintingPrice inline → **FIXED**: PrintingPriceInline
- PrintingPrice: duplex field in fieldsets but not in list_display; no machine filter → **FIXED**: list_display includes duplex, list_filter includes machine
- PaperPrice: no gsm filter → **FIXED**: gsm in list_filter
- MaterialPrice: no material_type filter in list_filter (has it) → already present
- PrintTemplate: no shop (templates are global); no min_quantity, min_gsm, max_gsm → **FIXED**: shop FK added (nullable), min_gsm, max_gsm added, list_display updated
- TemplateCategory: no shop (global) → **FIXED**: shop FK added (nullable)

**NEW**: Shop-scoped template CRUD at `/api/shops/{slug}/templates/` and `/api/shops/{slug}/templates/categories/`. IsShopOwner permission.
