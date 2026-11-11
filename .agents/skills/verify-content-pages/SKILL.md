---
name: verify-content-pages
description: Drive the growth-theme content pages (FAQs, custom/policy pages, Shipping & Payment with its cities dialog, bank copy buttons, mobile cards) in headless Chrome against the local storefront and keep evidence. Use after changing templates/faqs, templates/page, templates/shipping_payment, components/shipping-payment or assets/js/shipping-payment.js, and before opening a PR that touches them.
---

# verify-content-pages

Runnable verification for the `content-pages` group of `zidsa/growth-theme`. It loads the
pages the way a shopper does, compares what the theme rendered with vitrin's `/api/v1/*` data
for the same store, and exercises the browser JS (`assets/js/shipping-payment.js`).

Covers: `components/shipping-payment/` (shipping-table, shipping-cards-mobile, payment-methods,
bank-accounts, cities-dialog), `assets/js/shipping-payment.js`, `templates/faqs.jinja`,
`templates/page.jinja`, `templates/shipping_payment.jinja`.

## Routes (vitrin, not guessed)

| Template | URL on the storefront | Data |
|---|---|---|
| `templates/faqs.jinja` | `/faqs` (`/pages/faqs` redirects to it) | `/api/v1/pages/faqs` |
| `templates/page.jinja` | `/pages/{slug}` (policy slugs `privacy-policy`, `terms-and-conditions`, or a custom page slug) | `/api/v1/pages/{slug}` |
| `templates/shipping_payment.jinja` | **`/shipping-and-payment`** (`/shipping-payment` is not a route and 404s on every store) | `/api/v1/shipping-and-payment` |

Source: `zidsa/vitrin` `storefront/routes.py` (`faqs`, `page_details`, `shipping_payment`), read at sha `dfd3386b`.
Store 1 has data for all three: 10 FAQs, two policy pages (no custom page: the header links to `/pages/35`,
`/pages/bbb` and `/pages/None` all 404), 22 shipping methods, 13 payment methods, 23 bank accounts. No Jinja harness
substitution was needed for page rendering; one is used only where live data cannot reach a branch (below).

## Launch and doctor: see verify-growth-theme

The storefront (vitrin rendering this checkout, assets on a second port) is started and stopped by
`.agents/skills/verify-growth-theme/SKILL.md`; do not repeat that here. Check it, then drive one journey at a
time from the repo root (default port 8995):

```bash
bash .agents/skills/verify-growth-theme/scripts/storefront.sh doctor
uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py content-pages-faqs
# list: ... drive.py --list | grep content-pages
```

Exit 0 = passed, 1 = failed (reason in `summary.json`). `content-pages-cities-country-escaped` replays a finding and is in `KNOWN` (`journeys.py`): `drive.py` exits 0 for a journey listed in its skill's `KNOWN` table only while it fails exactly the recorded `failed_checks` (prints `FINDING`); any other failure, a crash, or the bug no longer reproducing exits 1 with `CHANGED`. Evidence goes to `~/.cache/verify-growth-theme/evidence/<stamp>-<journey>/`.
Read-only against store 1: no cart writes, no forms, no OTP, nothing to clean up.

## Journeys

| Journey | What the shopper does | Pass condition |
|---|---|---|
| `content-pages-faqs` | Opens `/faqs`, reads the first answer, opens the second, closes the first; visits `/pages/faqs` | Rendered questions equal the API list in order; first open and rest closed on load; the clicked item opens and the first closes (panel really visible/hidden); `/pages/faqs` lands on `/faqs`; no theme console errors |
| `content-pages-page-content` | Opens `/pages/privacy-policy` and `/pages/terms-and-conditions`, then a slug that does not exist | `h1`, breadcrumb current item and `<title>` equal the API title; Home breadcrumb link points at `/`; API body text appears in the prose block; unknown slug is 404 |
| `content-pages-shipping-payment` | Opens `/shipping-and-payment` (desktop), opens Payment then Bank accounts, closes Shipping; also requests `/shipping-payment` | Legacy path 404; one table row per API method in API order; cost and COD text match the API; a "+N more" button exactly for methods with more than 3 areas; default open/closed state shipping/payment/banks = open/closed/closed; payment icons = API icons; 23 bank cards with IBAN and name from the API; copy buttons = one per account number and IBAN; sections open and close |
| `content-pages-shipping-mobile` | Same page at 390 px, taps "+N more" on the first card, closes the dialog with the footer button | Cards (not the table) are visible, one per method in API order; mobile triggers match the API; the dialog opens with that method's cities and closes |
| `content-pages-cities-dialog` | Opens the largest method's area list (397 areas), searches, clears, closes, opens another method | Title is the method name; every API city is a tag; header "(397 cities)"; case-insensitive substring search narrows to exactly the matching cities; a nonsense term shows the empty state and no tags; clearing restores all; reopening a different method resets search and list |
| `content-pages-cities-countries` | Same dialog with every other city assigned a different country (see Gotchas), collapses and re-expands a country, searches by country name | Two country sections, all open at first; collapsing hides only that section and unrotates its icon; re-expand works; searching a country name leaves only that country |
| `content-pages-cities-country-escaped` | Same multi-country dialog with a country named `<img id=... onerror=...>` | The text is shown as text, no element is injected, no handler runs. **Fails today (finding), see Recorded run** |
| `content-pages-copy-bank` | Opens Bank accounts, clicks the IBAN copy button, then the account-number copy button | Clipboard holds exactly the IBAN, the button shows the success icon, reverts after 2 s; the account button copies the account number |

## Coverage

| Module | Driven by |
|---|---|
| `templates/faqs.jinja` | `content-pages-faqs` |
| `templates/page.jinja` | `content-pages-page-content` |
| `templates/shipping_payment.jinja` | `content-pages-shipping-payment`, `content-pages-shipping-mobile` |
| `components/shipping-payment/shipping-table.jinja` | `content-pages-shipping-payment` (rows, cost, COD, triggers), `content-pages-cities-dialog` |
| `components/shipping-payment/shipping-cards-mobile.jinja` | `content-pages-shipping-mobile` |
| `components/shipping-payment/payment-methods.jinja` | `content-pages-shipping-payment` (icon count; the `payment_description` branch is only checked in `formal-content-pages`) |
| `components/shipping-payment/bank-accounts.jinja` | `content-pages-shipping-payment`, `content-pages-copy-bank` |
| `components/shipping-payment/cities-dialog.jinja` | `content-pages-cities-dialog`, `content-pages-shipping-mobile`, `content-pages-cities-countries` |
| `assets/js/shipping-payment.js` | `content-pages-cities-dialog` (single-country render, search, reset), `content-pages-cities-countries` (accordion), `content-pages-cities-country-escaped` (innerHTML), `content-pages-copy-bank` (clipboard) |

Not driven live, with the reason: a custom (non-policy) page slug, because store 1 has none (the template is the same
and is exercised through the two policy slugs and by `formal-content-pages`); `country_name` (flat) city shape and a
real multi-country method, because store 1's cities have no country (shown under "Other"); empty FAQ / no-banks /
no-shipping states, because store 1 always has data (covered by `formal-content-pages`); Arabic RTL (the store renders
English here; titles are Arabic and checked as text).

## Recorded run

2026-11-11, theme `2b1c67d`, vitrin `dfd3386b` (store 1, testing API), Chrome headless, one journey at a time.

| Journey | Result |
|---|---|
| `content-pages-faqs` | passed (10 FAQs) |
| `content-pages-page-content` | passed (2 pages, unknown slug 404) |
| `content-pages-shipping-payment` | passed (22 rows, 13 payment methods / 22 icons, 23 banks, 45 copy buttons) |
| `content-pages-shipping-mobile` | passed (22 cards) |
| `content-pages-cities-dialog` | passed (397 areas, search "بقع" = 2) |
| `content-pages-cities-countries` | passed (2 sections, 397 tags) |
| `content-pages-cities-country-escaped` | **failed, real finding**: `injected_element_in_dom: true`, `handler_ran: true`. `renderCities` writes the country name with `innerHTML` |
| `content-pages-copy-bank` | passed |

Transcript `<proof>/verify-content-pages/run.txt`; evidence dirs beside it.

## Evidence

Each run writes `summary.json` (every `checks` value) and screenshots (`1-...png` per step) to
`~/.cache/verify-growth-theme/evidence/<UTC stamp>-<journey>/`. Copy the dir you cite out of the cache; do not put
evidence in this skill directory.

## Gotchas

- Wait for `load` plus a selector. `/shipping-and-payment` is ready when `#shipping-methods-data` exists; never `networkidle` (chat widget polls).
- Console errors from `landbot`/`chatbot.com` (third-party chat widget) and failed resource loads are filtered by `_own_errors`; anything else fails the journey.
- A site script rewrites the currency code in prices to a symbol after load, so cost/COD checks compare the number (`_amount`) not "21.01 SAR".
- The table and the card list are both in the DOM; at 1280 px the cards are `md:hidden`. Locators are scoped to `.hidden.md\:block` (table). Use `text_content()` for names: the table uppercases them with CSS and `inner_text()` returns the transformed text.
- Store 1's cities carry no country. `content-pages-cities-countries` and `...-country-escaped` therefore register an init script that rewrites the embedded `#shipping-methods-data` JSON on `DOMContentLoaded` (before the theme's own listener). Template, CSS and the real `shipping-payment.js` are untouched. `page.route()` is not used: intercepting the document makes the cross-origin theme-script request fail CORS.
- `/shipping-and-payment` shows only methods the store has enabled; counts change if someone edits store 1 in the testing dashboard. The journeys compare against the API at run time, not hard-coded counts.
- Clipboard: the copy journey grants `clipboard-read/write` for the origin; plain `http://127.0.0.1` is a secure context, a deployed http store is not (the theme logs and shows nothing there).
- `/pages/faqs` also resolves through vitrin's `/api/v1/pages/faqs`; the theme's `page.jinja` is never rendered for it.
