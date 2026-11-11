---
name: verify-cart
description: Drive the growth-theme cart page (templates/cart.jinja, components/cart/*, assets/js/cart/*, the gifting / loyalty / qty-input features) in headless Chrome against a local vitrin storefront and keep evidence. Use when a change touches the cart, coupon, gifting, loyalty, badge, quantity or cart-refresh code.
---

# verify-cart

The cart group: the cart page and the JavaScript that keeps it in step with the
platform's cart. This skill launches nothing of its own — it drives the storefront
that `verify-growth-theme` runs (`templates/` from this checkout, `assets/dist/*.js`
from the local asset server), adds a line to the cart through the API, exercises the
page the way a shopper does, and leaves a pass/fail with evidence for every journey.

Read `../verify-growth-theme/SKILL.md` first for launch, doctor and the shared-store
rules. Group index is there too.

## Modules and what proves them

| Module | Owns | Proved by |
|---|---|---|
| `templates/cart.jinja` | page shell, cart-controller boot, empty vs populated | `cart-page`, `cart-empty` |
| `components/cart/order-summary.jinja` | totals rows, discount rows, items count | `cart-page` |
| `components/cart/coupon-code.jinja` | applied chip vs apply form | `cart-page`, `cart-coupon` |
| `components/cart/loyalty-program.jinja` | earn card, guest login link, redemption controls | `cart-loyalty-guest` |
| `components/cart/gift-order.jinja` | "Make it a gift" button + gift card partial | `cart-gift-guest` |
| `components/cart/gift-card-display.jinja` | gift card summary line | `cart-page` (renders with empty gift details); the filled state needs a gift order, see Guest-only limits |
| `components/cart/shipping-progress.jinja` | free-shipping message, bar and truck | rendered by `cart-page` (the live page emits `width: 202%`); the `[0,100]` bound is asserted by `formal-cart` > ProgressWidth |
| `components/cart/checkout-buttons.jinja` | checkout link / closed-store notice | `cart-page` |
| `components/cart/empty-state.jinja` | empty-cart state | `cart-empty` |
| `assets/js/cart/controller.js` | `CartPage` bootstrap, action delegation, init guard | `cart-page`, `cart-coupon` |
| `assets/js/cart/refresh.js` | AJAX section swap, `zidcart:*` listeners, reload fallback | `cart-quantity`, `cart-refresh-race` |
| `assets/js/cart/totals.js` | totals rows, payment widgets, free-shipping bar, loyalty display | `cart-page` |
| `assets/js/cart/quantity.js` | `qty:change` / `qty:remove` → `zid.cart.updateProduct` / `removeProduct` | `cart-quantity` |
| `assets/js/features/qty-input.js` | ± buttons, clamping, `qty:change` dispatch | `cart-quantity` |
| `assets/js/cart/coupon.js` | enable-on-input, apply/remove, busy + focus restore | `cart-coupon` |
| `assets/js/cart/badge.js` | header `[data-cart-badge]` count | `cart-badge` |
| `assets/js/cart/loyalty.js` | redemption select, apply/remove, earn display | `cart-loyalty-guest` (guest half only) |
| `assets/js/cart/gift.js` | gift dialog open, delete, display update | `cart-gift-guest` |
| `assets/js/features/gifting.js` | header "send a gift?" hint after an add | `cart-gift-popup` |
| `assets/js/cart/add-to-cart.js` | PDP/card add buttons, cart sync | `cart-gift-popup` (adds a line) |
| `assets/js/features/loyalty-rewards.js` | floating rewards button | **not drivable here**: `layout.jinja` loads it only outside `cart_page`, and `window.loyaltyConfig` is undefined on the cart, so the module returns without doing anything |

`formal-cart` verifies the same modules offline, including the paths a guest cannot
drive live (coupon submit success, loyalty redemption, gift submit — with `window.zid`
stubbed, so they prove the theme's side only) and the timing property behind
`cart-refresh-race`.

## Run

```bash
cd <growth-theme checkout>                  # the worktree with .agents/skills/
S=.agents/skills/verify-growth-theme/scripts
$S/storefront.sh doctor                             # must end "doctor: healthy"
# No healthy instance? Only then start one, and stop it when you are done:
#   $S/storefront.sh up ; ... ; $S/storefront.sh down
# On a shared machine a card may already run one on 8995: reuse it, never restart it.
DRIVE="uv run --no-project --with playwright python -I $S/drive.py"
$DRIVE --list                                       # every journey, base + group
$DRIVE cart-page
```

`drive.py` writes `summary.json`, screenshots, `network.log` and `console.log` to
`~/.cache/verify-growth-theme/evidence/<stamp>-<journey>/`; `VERIFY_HOME` moves that
root (the `<stamp>-<journey>` directory is appended to it). Never point it inside the
repo: evidence is not committed. The recorded runs' evidence and stdout are in the
verification transcripts attached to the PR that last changed this skill.

## Journeys

| Journey | Shopper does | Passes when | Today |
|---|---|---|---|
| `cart-page` | opens `/cart` with one line in the cart | line renders with its `[data-qty-input]`; `[data-cart-totals]` has one direct child per `totals[]` entry and the `total` row is last and the only bold one; every total's amount appears (numbers, not `value_string`: vitrin swaps the currency word for an inline riyal SVG); no double sign; `[data-checkout-buttons] a[href="/checkout"]`; `dist/cart-controller.js` loaded from the asset server and `window.CartPage.init` is a function | **passes** |
| `cart-empty` | opens `/cart` with nothing in it | `.cart-empty` visible, no `[data-cart-totals]`, no `[data-coupon-section]`, no checkout button, header badge hidden, controller still loads | **passes** |
| `cart-quantity` | clicks `+`, then `−`, then the row trash on the cart page | each click sends exactly one `PATCH`/`DELETE` to `/api/v1/cart/items/<cart line id>`, the DOM reaches the API quantity after the swap, and removing the last line lands on the empty state | **passes** |
| `cart-badge` | removes one of two lines, stays on the page | DOM holds one line, `/api/v1/cart` `products_count` is 1, header `[data-cart-badge]` reads 1 | **fails — badge stays 2** (finding 1) |
| `cart-coupon` | types a code, clears it, retypes and submits an invalid code | submit disabled on empty input; exactly one `POST /api/v1/cart/coupons` per click *after `CartPage.init` is called a second time*; a rejected code re-enables the button, hides the spinner, refocuses the input, no navigation | **passes** |
| `cart-loyalty-guest` | opens `/cart` as a guest | `[data-loyalty-section]` + earn card render, login link carries `redirect_to=/cart`, redemption section stays hidden for a guest | **passes** |
| `cart-gift-guest` | clicks "Make it a gift" as a guest | `[data-gift-order-section]` renders and the click opens a dialog without leaving `/cart` | **passes** |
| `cart-gift-popup` | adds a product from the PDP | `[data-gift-cart-popup]` becomes visible after the add and hides again ~4 s later | **passes** |
| `cart-refresh-race` | changes the cart after the response body is composed but before it is swapped in | once the swap lands the page must reach `/api/v1/cart` within 1 s (`stale_window.ms`); a `zidcart:updated` sent during a refresh may not be dropped | **fails — `stale_window` timed out at 12 s, qty 1 against API 3** (finding 2) |

Two journeys replay open defects. They are listed in `KNOWN` at the bottom of
`journeys.py`: `drive.py` exits 0 for a journey listed in its skill's `KNOWN` table only while it fails exactly the recorded `failed_checks` (prints `FINDING`); any other failure, a crash, or the bug no longer reproducing exits 1 with `CHANGED`. When a fix lands, drop the entry from `KNOWN` and the
Findings section; do not edit the journey to pass.

## Findings these journeys replay

1. **Header badge goes stale** (`js/cart/badge.js`, `js/cart/refresh.js`). After a
   cart change the theme re-renders the sections but never re-runs `refreshBadge`:
   it calls `window.cartManager.refreshBadge()` if the platform defines it, and on
   this storefront `window.cartManager` is `undefined`. `cart-badge` removes one of
   two lines and the header still reads 2 while the cart holds 1.
2. **A refresh requested during a refresh is dropped** (`js/cart/refresh.js`). The
   `isRefreshing` guard returns early instead of remembering that another refresh is
   needed, so a cart change that lands while the (4–6 s) AJAX swap is in flight is
   never re-rendered. `cart-refresh-race` holds the first response at its
   request-time body, changes the cart, and shows the DOM stuck at the old quantity
   until a further event arrives.

`formal-cart` carries the same two as `RefreshConverges` / `BadgeOnRefresh` plus three
the browser cannot show here: the free-shipping bar width (`ProgressWidth`), cart-string
escaping (`TotalsTextEscaping` / `CartTextEscaping`) and the quantity field drifting from
its reported value (`QuantityMirrorsDisplay`).

## Recorded run

- **Date** 2026-11-11 (UTC), one storefront on `127.0.0.1:8995` (assets 8996), testing API,
  store 1, guest session, `ar-SA` at 1280×900.
- **Theme** `2b1c67d`. **Vitrin** `dfd3386b` (recorded because vitrin renders these
  templates and the run is only meaningful with both).
- **Evidence** `<proof>/verify-cart/`, one
  directory per journey, all stdout concatenated in `run.txt` beside it.

| Journey | Result | Evidence dir |
|---|---|---|
| `cart-page` | pass | `20261111T120402Z-cart-page` |
| `cart-empty` | pass | `20261111T120416Z-cart-empty` |
| `cart-quantity` | pass | `20261111T120428Z-cart-quantity` |
| `cart-badge` | **fail** — badge 2, API `products_count` 1 (finding 1) | `20261111T120456Z-cart-badge` |
| `cart-coupon` | pass (404 from the coupon API, UI recovered) | `20261111T120520Z-cart-coupon` |
| `cart-loyalty-guest` | pass | `20261111T120550Z-cart-loyalty-guest` |
| `cart-gift-guest` | pass | `20261111T120626Z-cart-gift-guest` |
| `cart-gift-popup` | pass | `20261111T120700Z-cart-gift-popup` |
| `cart-refresh-race` | **fail** — `stale_window` 12000 ms, qty 1 against API 3 (finding 2) | `20261111T120743Z-cart-refresh-race` |

## Guest-only limits

The storefront has no logged-in customer, so these cannot be driven here and are
covered by the formal harness instead:

- applying a coupon *successfully* (needs a valid code for store 1 — none is issued
  to agents), gift-card redemption, loyalty redemption and gift submit;
- `loyalty-rewards.js` (not loaded on `cart_page`) and the authenticated half of
  `gift.js`/`loyalty.js` (`data-auth-user` sections stay hidden; `initAuthVisibility`
  removes them).
- `updateCartTotals` / `cartProductsHtmlChanged` — the platform calls that callback
  only when it rewrites cart HTML itself, which the UI paths here do not trigger.

## Store discipline

- Cart writes are allowed; every journey empties the cart in a `finally`
  (`DELETE /api/v1/cart/items`). Never check out, never touch account data.
- The listing API returns dashed UUIDs; the cart line's `product_id` is the same UUID
  without dashes, and its `id` is a numeric cart-line id. Send the **cart line id** to
  `PATCH`/`DELETE /api/v1/cart/items/<id>`; compare products by `replace("-", "")`.
- `/cart` polls a chat widget: wait for `load` plus a selector, never `networkidle`.
- The AJAX swap takes 4–6 s on this machine. Poll with `wait_for_function` /
  `wait_for_selector` (30 s); never `wait_for_timeout` a fixed guess before asserting.
- Third-party console noise is normal (Landbot CORS, 401 `auth/login-status`,
  `products/gifting/settings` 400). Judge only `dist/cart-controller.js` /
  `dist/theme.js` errors.

## Evidence

Keep the `<stamp>-<journey>/` evidence directory and the drive stdout for every
journey you cite. A PR claim names the journey, `summary.json` `passed`, and the path.
