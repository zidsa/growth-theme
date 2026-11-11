---
name: formal-account
description: Formal property checks for growth-theme's account group (js/features/phone-input.js, js/features/wishlist.js and the templates that feed them). Bounded-exhaustive checks over the real modules in headless Chrome plus Jinja render checks; asserts the recorded outcome of each property, including seven known defects. Use after changing either module, components/ui/phone-input.jinja or components/products/wishlist-button.jinja.
sync-commit: 2b1c67df1fb4f69637887f375d22099b90dafeb5
---

# formal-account

sync-commit: `2b1c67df1fb4f69637887f375d22099b90dafeb5` (growth-theme, branch chore/verification_coverage).

Run: `bash .agents/skills/formal-account/check.sh` (≈50 s). Exit 0 = every property matched
`props/expected.txt`; exit 1 prints `CHANGED <property>`. Needs `uv`, Google Chrome, network for the first
`uv run` to fetch `jinja2` and `playwright`. No repo dependency is added.

Tools: **Browser** = the real `assets/js/features/*.js` served unbuilt to headless Chrome by request
interception (no server, no bundle), with the real `phone-input.jinja` output as DOM and a scripted
`window.zid.account`. **Jinja** = plain Jinja2 over the real templates, no autoescape (as vitrin's
`.jinja` environment). Both fit because these modules only misbehave in a DOM and the templates only
misbehave for data combinations.

## Properties

Modules: P = `js/features/phone-input.js`, W = `js/features/wishlist.js`.

| Property | Promise (plain) | Harm if broken | Tool, why |
|---|---|---|---|
| `phone-digits` (P) | Typing or pasting 0-14 digits never loses, reorders or invents a digit in the field. | A shopper's number is silently altered and the stock alert goes to the wrong number. | Browser, 150 generated numbers (every length, ten digit patterns incl. leading zeros). |
| `phone-spacing` (P) | The grouped number has no leading, trailing or double space. | Stray trailing space at 10 digits; visible, and a padded value if the field is read directly. **Finding.** | Browser, same inputs. |
| `phone-full-value` (P) | The hidden value is `<dial code><digits>` after every edit, empty when there are no digits. | The form posts a different number than the one shown. | Browser. |
| `phone-idempotent` (P) | Re-formatting a formatted value changes nothing. | Typing flickers or grows spaces. | Browser, lengths 1-14. |
| `phone-caret` (P) | Inserting a digit anywhere keeps the caret right after it. | Caret jumps to the end while correcting a typo. | Browser, 104 insert positions. |
| `phone-numerals` (P) | Arabic-Indic, Persian and full-width digits are kept (or converted), not discarded. | An Arabic-keyboard shopper types a whole number and the field stays empty. **Finding.** | Browser, three scripts × 10 digits. |
| `phone-filter` (P) | Every country is found by its English name (any case, padded), Arabic name, dial code and ISO code; nonsense shows "No country found"; clearing restores all. | A shopper cannot find their country. | Browser, all 199 countries × 6-8 queries. |
| `phone-select` (P) | Choosing any country sets display, hidden code, full value, `aria-selected`, fires one `phone:country-change` with that country, closes the popover and refocuses the number field. | Wrong dial code submitted. | Browser, all 199 countries by click. |
| `phone-dial-collision` (P) | Choosing one country marks only that country selected. | `+1` (US/CA) and `+7` (RU/KZ) both show a check; the code is right, the selection is ambiguous. **Finding.** | Browser. |
| `phone-validate` (P) | `validate()` / `isValid()` agree with the country table for every country and length 0-20. | Wrong "valid" verdict lets bad numbers through or blocks good ones. | Browser, 4137 cases. |
| `phone-escape` (P) | In a modal `<dialog>`, Escape in the country search closes only the popover and focuses the trigger. | One Escape closes the notify-me dialog too; typed data and focus are lost. **Finding.** | Browser with a `<dialog>`, as notify-me renders it. |
| `phone-wiring` (P, template) | Every `data-*` hook the script queries exists exactly once in `phone-input.jinja` for every option combination; popover id matches its trigger; `data-all-countries` iff `all_countries`. | The field renders but does nothing. | Jinja, 48 option combinations. |
| `wishlist-template` (W, template) | `wishlist-button.jinja` renders exactly one `[data-wishlist-btn]` with the product id iff `wishlist_enabled` is boolean true (not `"true"`, missing, null). | A heart on a store that disabled wishlists, or none where it is enabled. | Jinja, 6 flag values + 3 id shapes. |
| `wishlist-callers` (W, template) | Every include of the button is inside a `with product_id=…` block and nothing hand-writes `data-wishlist-btn`. | A heart with an empty product id that does nothing. | Jinja/source scan over all templates. |
| `wishlist-states` (W) | For every sequence (≤4 steps) of clicks on two buttons, call success and failure: label, disabled flag, icon and set membership agree; never two writes in flight for a product; no spinner survives. | A wishlist that shows the wrong state or double-writes. | Browser, 340 sequences; async state machine → exhaustive interleavings are cheaper than a TLA+ model of two buttons. |
| `wishlist-refresh-midflight` (W) | A `products-updated` event (every filter/pagination render) keeps the spinner of a request still in flight. | The re-render re-enables the button; a second click sends a second write. **Finding.** | Browser. |
| `wishlist-duplicates` (W) | When a product has two buttons (card + quick view), both show the same state and the clicked one shows the spinner. | The spinner appears on the wrong button, a second click is not blocked, buttons disagree afterwards. **Finding.** | Browser. |
| `wishlist-guest-redirect` (W) | A guest click calls no SDK write and goes to `/auth/login?redirect_to=<encoded pathname>` on the same origin, for odd paths (`%2F%2Fevil`, quotes, `&`). | Open redirect or lost return path. | Browser, 8 paths. |
| `wishlist-sync` (W) | Wishlist responses (`results` objects, plain id array, empty, null, unknown shape) map to the right filled/empty set; 401/403/500/unknown errors leave a guest. | Hearts filled for products not on the wishlist. | Browser, 5 shapes + 4 errors. |
| `wishlist-sdk-wait` (W) | The SDK is found whenever it appears within 20 waits (delays capped at 2000 ms); later it gives up as guest and `refresh()` recovers. | Wishlist stays dead on slow SDK load. | Browser with the timer collapsed, SDK appearing at wait 0/1/5/19/20/25. |
| `wishlist-label-language` (W) | A server-rendered translated `aria-label` is not replaced by English. | Arabic storefront announces English labels to screen readers. **Finding.** | Browser (Arabic page). |

## Current findings

All asserted by `check.sh`: exit 0 while the counterexample still reproduces (a loud `FINDING:` line), exit 1 with
`CHANGED <property>` the moment any of them flips (fixed or changed).

- **`phone-spacing`**: `formatPhone` (phone-input.js:21) groups 10 digits as `3-3-4-""`: `digits.slice(10)` is empty so the template `slice(6,10) + " " + slice(10)` appends a space → `"512 345 6789 "`.
- **`phone-numerals`**: `handlePhoneInput` strips with `/\D/g`, which removes every non-ASCII digit, so `٠١٢٣٤٥٦٧٨٩` becomes `""` and the full value stays empty.
- **`phone-dial-collision`**: options with the same dial code (`+1`: US, CA; `+7`: RU, KZ) are all marked selected because selection is by dial code, not country code.
- **`phone-escape`**: the keydown handler for `Escape` calls `popover.hidePopover()` and `countryTrigger.focus()` but not `preventDefault()`; the same Escape reaches the modal `<dialog>`, which cancels (closes) and focus falls to the body.
- **`wishlist-refresh-midflight`**: `updateAllButtons()` (bound to `products-updated` and `content:loaded`) re-derives every button from `wishlistProductIds`, so an in-flight "loading" button becomes "empty"/"filled" and enabled again.
- **`wishlist-duplicates`**: `getButton()` is `querySelector`, the first match only; a second button for the same product never gets the spinner or the new state, and the second click is not blocked.
- **`wishlist-label-language`**: labels come from `window.wishlistConfig?.labels`, which no template, schema or script in the repo defines, so `setButtonState` writes the English fallbacks over the translated `aria-label`.

Also seen, not asserted: `formatPhone` keeps at most 14 digits (`slice(10, 14)`); the longest `phoneLengths` entry in `countries.js` is 13, so 15+ typed digits are cut off silently.

## How to run

```bash
bash .agents/skills/formal-account/check.sh                    # ROOT defaults to this repo
ROOT=/path/to/other/checkout bash .agents/skills/formal-account/check.sh
```

Individual halves (print `PROPERTY <id> <ok|finding> <signature>` plus the first counterexamples):
`ROOT=… uv run --no-project --with jinja2 python -I props/templates.py` and
`ROOT=… uv run --no-project --with jinja2 --with playwright python -I props/browser.py` (run from `props/`).

## Reading a result

- `CHANGED <p>: got 'ok …', recorded 'finding …'`: a recorded defect disappeared. If the product code was fixed on purpose, update `props/expected.txt` for that line and move the finding out of this file.
- `CHANGED <p>: got 'finding …', recorded 'ok …'`: a real regression: read the indented counterexample under it (it is printed above the CHANGED line by the halves, or re-run the half).
- `HARNESS …` lines or `property did not run`: harness error (missing Chrome, Playwright not fetchable, template path renamed). Not a product bug.
- `NOTE drift` + a `git diff --stat`: a covered file changed since the sync commit; the properties still ran against the new code.

## Bounds and assumptions

- Phone grouping is checked for 0-14 digits; a country table lookup is used as shipped (`assets/js/data/countries.js`, 199 entries, 197 distinct dial codes).
- The popover and highlight logic run in Chrome (`el-popover` falls back to the native Popover API; no Tailwind Elements runtime is loaded in the fixture).
- The SDK is a stub: `wishlists`, `addToWishlists`, `removeFromWishlist` return scripted promises. Real server behavior (does a wishlist write succeed, 401 text) is not modelled.
- Vitrin's template environment has no autoescape and no Zid filters beyond pass-through stubs (`currency`, `asset_url`, …); `_()` returns the msgid; `vitrin:` includes render empty.
- Sequence length 4 for `wishlist-states`; two buttons, one initially wished.

## Coverage record

| Property | File:function |
|---|---|
| `phone-digits`, `phone-spacing`, `phone-full-value`, `phone-idempotent`, `phone-caret`, `phone-numerals` | `props/browser.py:prop_phone_input_format`, `prop_phone_numerals` → `assets/js/features/phone-input.js:formatPhone`, `handlePhoneInput` |
| `phone-filter`, `phone-select`, `phone-dial-collision`, `phone-validate` | `props/browser.py:prop_phone_filter_select` → `phone-input.js` country list, `validate`, `isValid`; `assets/js/data/countries.js:validatePhoneLength` |
| `phone-escape` | `props/browser.py:prop_phone_escape` → `phone-input.js` search keydown handler |
| `phone-wiring` | `props/templates.py:phone_wiring` → `components/ui/phone-input.jinja` |
| `wishlist-template`, `wishlist-callers` | `props/templates.py:wishlist_template`, `wishlist_callers` → `components/products/wishlist-button.jinja`, `product-card.jinja`, `templates/product.jinja` |
| `wishlist-states`, `wishlist-refresh-midflight`, `wishlist-duplicates` | `props/browser.py:prop_wishlist_states`, `prop_wishlist_refresh_midflight`, `prop_wishlist_duplicates` → `wishlist.js:handleWishlistClick`, `addToWishlist`, `removeFromWishlist`, `updateAllButtons`, `getButton` |
| `wishlist-guest-redirect`, `wishlist-sync`, `wishlist-sdk-wait`, `wishlist-label-language` | `props/browser.py:prop_wishlist_guest`, `prop_wishlist_sync`, `prop_wishlist_sdk_wait`, `prop_wishlist_label_language` → `wishlist.js:redirectToLogin`, `syncWishlistState`, `waitForZidSDK`, constructor `LABELS` |

Mutations proven caught (copy of the repo, never the working tree): `mutants/phone-truncate.patch`
(`slice(10,14)`→`slice(10,13)`) → `phone-digits`, `phone-caret` flip; `mutants/wishlist-guest-guard.patch`
(drops the guest redirect guard) → `wishlist-guest-redirect` flips. Transcripts:
`<proof>/formal-account/{pass,break,pass-after}.txt`.

## What is not covered

- Logged-in server behavior of the wishlist (needs a customer session; verify-account stubs the SDK too).
- `wishlistManager.shareWishlist`, wishlist page rendering and anything under `account` templates: they are not in this group's modules.
- Visual layout of the popover and the heart icons.
- Real keyboard layouts / IME composition for the phone field (only `input` events with prepared values and `press_sequentially` in the journeys).
