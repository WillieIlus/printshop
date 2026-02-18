# API Endpoint Audit: UI ↔ Backend Alignment

This document maps every endpoint the UI calls to the backend implementation. All endpoints below exist and are aligned as of the audit.

## Auth + Password Reset (Must-Have for Launch)

| UI Call | Full Path | Backend | Status |
|---------|-----------|---------|--------|
| `API.auth.login` | `POST /api/auth/api-auth/login/` | `accounts.views.LoginView` | ✅ |
| `API.auth.refresh` | `POST /api/auth/api-auth/token/refresh/` | `TokenRefreshView` | ✅ |
| `API.auth.register` | `POST /api/auth/register/` | `accounts.views.RegisterView` | ✅ |
| `API.auth.forgotPassword` | `POST /api/auth/api-auth/password/reset/` | `PasswordResetRequestView` | ✅ |
| `API.auth.resetConfirm` | `POST /api/auth/api-auth/password/reset/confirm/` | `PasswordResetConfirmView` | ✅ |

**Body alignment:**
- Password reset request: `{ email }` ✅
- Password reset confirm: `{ uid, token, new_password, new_password_confirmation }` ✅ (UI updated to send both)

## Shops Nearby (Public Feature)

| UI Call | Full Path | Backend | Status |
|---------|-----------|---------|--------|
| `API.shopsNearby()` | `GET /api/shops-nearby/?lat=&lng=&radius=` | `shops.views.NearbyShopsView` | ✅ |

Query params: `lat`, `lng`, `radius` (km, default 10). UI passes `radius: 25`.

## Pricing Calculation (Core Value Prop)

| UI Call | Full Path | Backend | Status |
|---------|-----------|---------|--------|
| `API.shopRateCard(slug)` | `GET /api/shops/{slug}/rate-card/` | `pricing.views.RateCardView` | ✅ |
| `API.shopCalculatePrice(slug)` | `POST /api/shops/{slug}/calculate-price/` | `pricing.views.CalculatePriceView` | ✅ |

**Calculate-price body:** `{ sheet_size, gsm, quantity, sides?, paper_type?, finishing_ids? }` ✅

**Response (PriceCalculationResult):** `total_printing`, `total_paper`, `total_finishing`, `grand_total`, `finishing_breakdown`, `price_per_sheet`, etc. ✅

## Other UI Endpoints (Verified Present)

- `API.users()`, `API.userMe()` → `/api/users/`, `/api/users/me/`
- `API.profiles()`, `API.profileMe()` → `/api/profiles/`, `/api/profiles/me/`
- `API.shops()`, `API.shopsMyShops()`, `API.shopDetail(slug)` → shops router
- `API.shopsNearby()` → `shops-nearby/`
- `API.shopCalculatePrice(slug)`, `API.shopRateCard(slug)` → pricing (public)
- Shop nested: members, hours, social-links, quotes, product-templates, pricing CRUD, machines, materials, paper-stock
- `API.claims()`, `API.claimVerify()`, `API.claimReview()`
- `API.templates()`, `API.myQuotes()`
- `API.plans()`, `API.shopSubscription()`, `API.shopStkPush()`, `API.paymentStatus()`

## Changes Made (This Audit)

1. **Password reset confirm:** UI now sends `new_password_confirmation` (backend required it; UI was only sending `new_password`).
2. **Signup:** UI now uses `auth/register/` instead of `users/`; maps `password_confirm` → `password_confirmation`; no auto-login (backend creates inactive user until email confirmation).
