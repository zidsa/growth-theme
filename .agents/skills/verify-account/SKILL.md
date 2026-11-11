---
name: verify-account
description: Drive growth-theme's account-group browser JS (the phone input in js/features/phone-input.js and the wishlist toggle in js/features/wishlist.js) on the live local storefront as a guest, and keep evidence. Use after changing either module, components/ui/phone-input.jinja or components/products/wishlist-button.jinja, and before opening a growth-theme PR that touches them.
---

# verify-account

Runnable verification for the **account** group of `zidsa/growth-theme`: the shopper-side phone
number field and the wishlist heart. Launch, doctor, evidence and cleanup are in
[verify-growth-theme](../verify-growth-theme/SKILL.md); this skill only adds journeys.

## What the group covers

| Module (under `assets/`) | What it does |
|---|---|
| `js/features/phone-input.js` | Phone field: dial-code popover with search, number grouping as you type, `phone:change` / `phone:country-change` events, `PhoneInput` API (`validate`, `isValid`, `setDialCode`, ...). Rendered by `components/ui/phone-input.jinja`; the live page that shows it is the notify-me dialog on an out-of-stock product. |
| `js/features/wishlist.js` | `window.wishlistManager`: syncs the shopper's wishlist from `window.zid.account`, toggles `[data-wishlist-btn]` buttons (heart, spinner), sends guests to `/auth/login?redirect_to=<path>`. Buttons come from `components/products/wishlist-button.jinja`. |

## Launch and doctor: see verify-growth-theme

Use the already-running instance (port 8995) or `storefront.sh up` as described there; `doctor` must
end `doctor: healthy` before any journey. Drive from the repo root:

```bash
uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py --list
uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py account-phone-format
uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py account-phone-country
uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py account-wishlist-guest
uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py account-wishlist-toggle
```

Run them one at a time. Nothing here submits the notify-me form, sends an OTP or writes account data.

## Journeys

| Journey | What the shopper does | Pass condition |
|---|---|---|
| `account-phone-format` | Opens an out-of-stock product, opens the notify-me dialog, types a number key by key, pastes a formatted one, edits in the middle, calls the `PhoneInput` API | Digits are never lost or reordered (1-13 digits); `512 345 678` grouping; hidden full value is `+966` + digits after every key; letters and `-` never enter the value; caret stays after the edited digit; every key fires `phone:change` with matching `fullValue`; `validate()` returns `TOO_SHORT` / `TOO_LONG` / `EMPTY` / `undefined` correctly; no theme.js console error. A trailing space at exactly 10 digits and Arabic-Indic digits are recorded as observations, not failures (see formal-account). |
| `account-phone-country` | Opens the country popover, searches in Arabic, English, padded/upper-case, ISO and dial-code forms, uses arrow keys and Enter, reopens, presses Escape, calls `setDialCode` | 199 options; every query form finds Egypt; nonsense shows "No country found" and clearing restores 199; Up/Down wrap inside the visible list; Enter selects, closes the popover, returns focus to the number field and updates display, hidden code, full value, `aria-selected` and fires one `phone:country-change` (`EG`, `+20`); reopening highlights the selected country; `setDialCode('+971')` updates the value. The Escape side effect on the surrounding dialog is recorded in the checks, not asserted. |
| `account-wishlist-guest` | Opens `/products` as a guest, lets the real `wishlist.js` run, clicks the heart | `wishlistManager` initialised, `zid` SDK ready, `isLoggedIn` false (SDK answers 401 to `wishlists()`); guest buttons show the empty heart, label `Add to wishlist`, enabled; a button with no product id is inert; clicking the heart's SVG navigates to `/auth/login?redirect_to=%2Fproducts`; no theme.js console error. |
| `account-wishlist-toggle` | Same page with the SDK's three account calls replaced by held promises, then clicks hearts | After sync: wished product is filled and labelled `Remove from wishlist`, the other is empty; click shows spinner (`Loading`, disabled) until the call settles; add success fills, remove success empties; a failed add stays empty and out of the set; a failed remove stays filled and in the set; SDK is called with `{product_ids:[id]}` and `{showErrorNotification:true}` / `(id, {showErrorNotification:true})`; no real wishlist write leaves the browser. |

## Coverage

| Module | Driven by | Notes |
|---|---|---|
| `js/features/phone-input.js` | `account-phone-format`, `account-phone-country`; formal-account `phone-*` | Live path = notify-me dialog on an out-of-stock product (store 1 has them; the journeys pick one through `/api/v1/products`). |
| `js/features/wishlist.js` (guest) | `account-wishlist-guest` | Real module, real guest state from the testing SDK. |
| `js/features/wishlist.js` (signed-in toggle) | `account-wishlist-toggle` (SDK calls stubbed); formal-account `wishlist-states`, `wishlist-sync`, `wishlist-sdk-wait` | **Cannot be driven live**: nobody can log in on store 1 here, so `wishlists()`, `addToWishlists()` and `removeFromWishlist()` are stubbed on a copy of `window.zid`; the module under test is the real built `theme.js`. |
| Wishlist buttons on the live store | formal-account `wishlist-template`, `wishlist-callers` | **Cannot be driven live**: store 1 does not enable `store.settings.products.wishlist_enabled`, so the template renders no heart on any page (`account-wishlist-guest` records `live_buttons_rendered: 0`). The journeys inject the button markup the template emits; the template itself is rendered by the formal checks with the flag on and off. |

## Recorded run

2026-11-11, theme `2b1c67d` (`2b1c67df1fb4f69637887f375d22099b90dafeb5`), vitrin `dfd3386b`, store 1 on
`testing-api.zid.sa`, headless Chrome ar-SA 1280x900. `doctor: healthy`.

| Journey | Result | Evidence |
|---|---|---|
| `account-phone-format` | passed | `<proof>/verify-account/20261111T131625Z-account-phone-format` |
| `account-phone-country` | passed | `.../20261111T131637Z-account-phone-country` |
| `account-wishlist-guest` | passed | `.../20261111T131650Z-account-wishlist-guest` |
| `account-wishlist-toggle` | passed | `.../20261111T131657Z-account-wishlist-toggle` |

## Evidence

drive.py writes `summary.json` (every value in `checks`), screenshots, `network.log` and `console.log`
under `~/.cache/verify-growth-theme/evidence/<UTC stamp>-<journey>/`. Keep copies outside this skill dir.
The full drive.py stdout of the recorded run is `<proof>/verify-account/run.txt`.

## Gotchas

- The phone input only exists on the live site inside the notify-me dialog of an **out-of-stock** product; journeys fetch one from `/api/v1/products?availability=out_of_stock` and skip products with options.
- `window.zid.account` is frozen: stubbing a method in place silently does nothing. `account-wishlist-toggle` replaces `window.zid` with a copy.
- Store 1's hidden `wishlist_enabled` means "no heart on the page" is the correct live state, not a bug in the journey.
- Never `networkidle`: the chat widget polls. The journeys wait for selectors or `window.wishlistManager.isInitialized`.
- Known recorded defects (phone number grouping at 10 digits, non-Latin numerals, Escape also closing the dialog, wishlist label language) are asserted by formal-account, not here.
