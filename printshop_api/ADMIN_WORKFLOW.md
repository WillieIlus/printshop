# Admin Workflow

**Admin workflow: Create shop → add machines → add pricing → add templates**

1. **Create shop** – Django Admin → Shops → Add Shop (set owner, name, slug, contact, address)
2. **Add machines** – Edit the shop and add machines in the Machines inline, or go to Inventory → Machines
3. **Add pricing** – Pricing → Printing prices, Paper prices, Material prices (filter by shop)
4. **Add templates** – Templates → Template categories (create shop-scoped categories), then Print templates

Shop owners can also manage their shop via the API: `/api/shops/{slug}/machines/`, `/api/shops/{slug}/pricing/`, `/api/shops/{slug}/templates/`.

---

# API Authentication (Dual Auth)

The API supports **two authentication methods**:

| Method | Use case | How |
|--------|----------|-----|
| **Session** | Browsable API, admin/testing in browser | Log in at `/api-auth/login/` (or Django admin), then browse protected endpoints. CSRF token is sent automatically with forms. |
| **JWT Bearer** | Frontend (SPA, mobile) | Obtain token via `/api/auth/token/` (or your auth endpoint), then send `Authorization: Bearer <token>` header. |

**Test in browser:**
1. Go to `/api-auth/login/` and log in with email/password.
2. Browse protected endpoints (e.g. `/api/shops/my-shops/`). You should see 200, not 401.
3. POST/PATCH work with CSRF; DRF includes the token in forms.

**Test with JWT:**
1. `POST /api/auth/token/` with `{"email": "...", "password": "..."}` (or your token endpoint).
2. Use `Authorization: Bearer <access_token>` on requests.
3. Frontend continues to work as before; no regression.

---

# Onboarding API (Postman-style)

**1. Create shop**
```
POST /api/shops/
Authorization: Bearer <token>  (or session cookie)
Content-Type: application/json

{"name": "My Print Shop", "business_email": "shop@example.com", "address_line": "123 Main St", "city": "Nairobi", "zip_code": "00100", "country": "Kenya"}
→ 201, returns {id, slug, name, ...}
```

**2. Add machines**
```
POST /api/shops/<slug>/machines/
{"name": "Xerox Versant 80", "machine_type": "DIGITAL"}
→ 201, returns {id, name, machine_type, ...}
```

**3. Add printing prices**
```
POST /api/shops/<slug>/pricing/printing-prices/
{"machine": <machine_id>, "sheet_size": "A4", "color_mode": "COLOR", "selling_price_per_side": "15.00", "selling_price_duplex_per_sheet": "25.00"}
→ 201, returns {id, machine, sheet_size, color_mode, selling_price_per_side, selling_price_duplex_per_sheet, ...}
```

**4. Add paper prices**
```
POST /api/shops/<slug>/pricing/paper-prices/
{"sheet_size": "A4", "gsm": 300, "paper_type": "GLOSS", "buying_price": "10.00", "selling_price": "18.00"}
→ 201
```

**5. Add material prices**
```
POST /api/shops/<slug>/pricing/material-prices/
{"material_type": "BANNER", "unit": "SQM", "selling_price": "500.00"}
→ 201
```

**6. Setup status (checklist)**
```
GET /api/shops/<slug>/setup-status/
→ 200, {"has_machines": true, "has_printing_prices": true, "has_paper_prices": true, "has_material_prices": false, "has_templates": false}
```
