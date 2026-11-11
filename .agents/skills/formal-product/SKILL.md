---
name: formal-product
description: Check the product group's promises (PDP buy box, gallery/zoom indices, variant identity, quick-view isolation, sticky bar, notify-me targeting, question email, review/question templates, bundle badges) against generated data and click sequences. Use before shipping a change to templates/product*, components/products/* or assets/js/product/*, and after a bug report there.
sync-commit: 2b1c67df1fb4f69637887f375d22099b90dafeb5
---

# formal-product

Tests check the cases someone thought of. These checks try every case in a stated
bound: every unit edge for relative time, every click sequence up to two steps in
the gallery, every option pick on a real product, 20 cache inserts, 34 generated
e-mail addresses, and five products/review distributions/questions fixtures
rendered from the real templates.

Thirteen properties. Each is one sentence a merchant would recognise, and each
one has a harm that a shopper pays for.

## Run it

```bash
# the browser half needs the same storefront verify-growth-theme serves:
#   .agents/skills/verify-growth-theme/scripts/storefront.sh up
bash .agents/skills/formal-product/check.sh          # ROOT defaults to this checkout
```

- exit 0 — every property matched its recorded outcome (both findings reproduce)
- exit 1 — `CHANGED <property> …` : the code moved against what this file records
- exit 2 — `BLOCKED` : the storefront is not up, so P2–P8/P13 could not run

`ROOT=/path/to/checkout` points it at another copy (that is how the break test
works). `BASE=http://127.0.0.1:9005` points the browser half at another instance.
A full run takes about a minute: P1 and P9–P12 take a second, the seven browser
properties run four at a time.

## Properties

| Id | Promise | Harm if it breaks | Tool and why |
|---|---|---|---|
| P1 | A relative date names the largest unit that fits, floored, singular only for 1, and never goes backwards as time moves forward (`assets/js/time-ago.js:formatTimeAgo`). | A two-day-old review reads "1 day ago" or "just now"; the shop looks busier or fresher than it is. | Node imports the real file with a stub `document` and walks 265 offsets: every unit edge ±1s plus a spread to two years. Cheapest way to cover the whole table. |
| P2 | From any state two clicks away, the highlighted thumbnail is the slide on screen, the index stays in `0..n-1`, and the arrows are disabled exactly at the ends (`assets/js/product/gallery.js:initProductGallery`). | The thumbnail lies about which photo is showing; the arrows dead-end. | Playwright on a live PDP: 31 click sequences over next/prev/thumb, geometry read from the real slide boxes. |
| P3 | Opening image *i* shows image *i* at its full-size URL, for every image (`assets/js/product/lightbox.js:collectImageData/openAtIndex`). | Zoom opens the wrong photo, so the shopper inspects the wrong detail and buys the wrong thing. | Playwright: clicks each thumbnail, opens PhotoSwipe, compares the shown `src` with that link's `href`. |
| P4 | Any option pick leaves `#product-id`, price, SKU, sticky price and gallery media describing exactly the variant the platform answered with (`assets/js/product/variants.js`, `templates/product.jinja`). | Add to cart sends a variant the shopper did not pick; the wrong size or colour arrives. | Playwright: clicks every non-active option in the first two groups and reads the `/options` response back. |
| P5 | Quick view gives the page its `productObj` back on close, empties the content, and its cache never exceeds 15 entries with LRU eviction (`assets/js/product/quick-view.js`). | After closing a quick view the page keeps talking about another product; memory grows per card viewed. | Playwright: opens from a PDP and from a listing, then drives `cacheSet`/`cacheGet` 20 times. |
| P6 | The sticky bar is on screen exactly while the buy box is not, and it shows the same price (`assets/js/product/sticky-bar.js`). | The bar covers the page while the buy box is visible, or hides the price the shopper came for. | Playwright: five scroll positions plus a return to the top. |
| P7 | The notify-me dialog always takes the product (or picked variant) of the section the trigger sits in — buy box, sticky bar, card (`assets/js/features/notify-me.js`). | A restock alert goes out for the wrong product; the shopper waits for a product they never wanted. | Playwright: real option pick, then the buy-box, out-of-stock and card triggers. |
| P8 | The ask-a-question form accepts an address exactly when it is a valid one (`assets/js/question-form.js:validateForm`). | A shopper with a modern address cannot ask; or a typo'd address is accepted and the answer never arrives. | Playwright: `noValidate` disables the browser layer, then 34 seeded addresses (seed 20261111) are submitted through the real form with the request aborted. |
| P9 | A PDP renders one buy box whose visible actions match what can be sold (in-stock block hidden iff `can_buy`, one add-to-cart form), and one gallery whose zoom targets are exactly the image media in order, each resized (`templates/product.jinja`, `components/products/product-gallery.jinja`, `sticky-product-actions.jinja`). | The page offers to sell something it cannot ship, or the zoom service answers with a thumbnail. | Plain Jinja2: 5 generated products (simple, options, out of stock, preorder, no media). |
| P10 | The reviews page renders every rating distribution without dividing by zero, keeps each bar inside 0–100%, lists exactly the reviews it was given, and loads the script that fills its relative dates (`templates/reviews.jinja`, `components/products/product-reviews.jinja`, `review-card.jinja`). | A product with no ratings 500s; a 130% bar misstates the shop's reputation; readers get raw `2026-01-27 21:19:21`. | Plain Jinja2: 4 distributions including `total_count: 0`. |
| P11 | An anonymous question never publishes the asker's name, and every answer stays under its own question (`templates/questions.jinja`, `components/products/product-questions.jinja`). | A shopper who asked anonymously is named on the storefront. | Plain Jinja2: mixed anonymous/named fixtures with and without answers. |
| P12 | A product card shows exactly one cart action, and it is the one the product's stock and options allow (`components/products/product-card.jinja`). | A card offers Add to cart for a sold-out product, or two competing buttons send the shopper in circles. | Plain Jinja2: 5 products (simple, options, fields, sold out, preorder). |
| P13 | A card's bundle badge names exactly one offer that the API returned, and re-rendering never duplicates or drops badges (`assets/js/features/bundle-offers.js`). | A promo label that says two things (or a stale one) is a pricing complaint waiting to happen. | Playwright on the listing: reads the API payload, then calls `reload()` and compares. |

## Current findings

Both were found by these checks on this commit, and `check.sh` asserts they still
reproduce. Fixing either one flips its line to `CHANGED` — that is the prompt to
update this section, not to widen the check.

1. **P8 — the question form refuses valid addresses with a long TLD.**
   `assets/js/question-form.js:validateForm` uses
   `/^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/`: the TLD is capped at six
   letters, so `guest0@shop0.technology`, `…photography`, `…international` are
   marked invalid and the question is never sent. Counterexample:
   `buyer@shop.technology` → the email field gets `!border-destructive` and no
   request leaves the page. No false accepts were found.
2. **P10 — the reviews page never converts its dates.**
   `templates/reviews.jinja` renders `review-card.jinja` (which prints
   `data-time-ago-date="2026-01-27 21:19:21"`) but does not include
   `assets/js/time-ago.js`, and no `[data-time-ago-labels]` block, so the page
   shows the raw timestamp; `components/products/product-reviews.jinja` on the
   PDP includes both and shows "9 months ago". The live journey
   `verify-product/product-reviews` fails on the same thing.

## Reading a result

- `PASS` — the property held for every case in the bound.
- `FINDING` — the recorded counterexample still reproduces; the run is still green
  because the finding is the expected outcome at this commit.
- `CHANGED` — the code no longer behaves as this file records, in either
  direction. Read the detail: a `harness error` is my bug (a selector moved, a
  fixture gained a field), a behavioural detail is a real change. Compare with
  `git diff <sync-commit> -- <covered files>` (check.sh prints the stat as
  `NOTE drift` when anything covered moved).
- `BLOCKED` — the storefront is down. Start it, rerun; do not read it as a pass.

Real bug or harness error? Re-run the single property
(`--only P8` / `--only P10` on the python scripts, `node props/time_ago.mjs`) and
open the page it names. If the page really shows that, it is a finding: report
it, do not edit the property.

## Bounds and assumptions

- P1 covers offsets 0 s – 2 years at every unit edge ±1 s and 241 evenly spaced
  points; labels come from the English defaults and one Arabic block.
- P2 covers every click sequence of length ≤ 2 over `{next, prev, thumb 0..2}`
  (31 states) on a 3-image product, and assumes the shopper lets the carousel
  settle between clicks.
- P3 covers every image of the first product with three or more images.
- P4 covers the first two option groups, up to two non-active items each, on the
  first product with options **and** parent images.
- P5 assumes the page object is either a real PDP `productObj` or `undefined`
  (a listing); a hand-made object is not a state the app produces.
- P6 samples five scroll positions; the equivalence is asserted at each.
- P7 covers the buy box (after a real variant pick), the out-of-stock buy box and
  one listing card; it never submits an alert.
- P8 assumes the reference grammar `local@domain.tld` with a 2–63 letter TLD and
  a permissive local part; it deliberately does not model quoted locals, IDN or
  RFC 5321 edge cases.
- P9–P12 assume the API's `total_count` is the sum of the star counts, and that
  `in_stock`, `quantity`, `is_infinite`, `has_options`, `has_fields` and
  `can_be_preordered` mean what the templates read them as.
- Store data is discovered from `/api/v1/*` at run time (first match in the
  listed order), so a store with no out-of-stock product, no reviews or no
  bundle offer reports that as the detail instead of passing silently.

## Coverage record

| Property | Code it describes |
|---|---|
| P1 | `assets/js/time-ago.js:formatTimeAgo`, `updateTimeAgoElements` |
| P2 | `assets/js/product/gallery.js:initProductGallery` (`updateActiveThumb`, `updateProgress`, thumbnail handlers), `components/products/product-gallery.jinja` |
| P3 | `assets/js/product/lightbox.js:collectImageData`, `openAtIndex`, `handleGalleryClick`; `components/products/product-gallery.jinja` (lightbox block, `data-lightbox-trigger`) |
| P4 | `assets/js/product/variants.js` (`productOptionsChanged`, `updateProductDetails`, `updateProductImages`), `templates/product.jinja` (buy box), `components/products/sticky-product-actions.jinja` |
| P5 | `assets/js/product/quick-view.js` (`open`, `close`, `handleDialogClose`, `cacheSet`, `cacheGet`), `components/products/quick-view-modal.jinja` |
| P6 | `assets/js/product/sticky-bar.js` (`init`, observer, `show`, `hide`), `components/products/sticky-product-actions.jinja` |
| P7 | `assets/js/features/notify-me.js` (`handleVariantChange`, `seedProductIdFromSection`, `handleNotifyMeTriggerClick`), `components/products/notify-me-dialog.jinja`, `components/products/product-card.jinja` |
| P8 | `assets/js/question-form.js` (`validateForm`, `showError`) |
| P9 | `templates/product.jinja`, `components/products/product-gallery.jinja`, `components/products/sticky-product-actions.jinja` |
| P10 | `templates/reviews.jinja`, `components/products/product-reviews.jinja`, `components/products/review-card.jinja` |
| P11 | `templates/questions.jinja`, `components/products/product-questions.jinja` |
| P12 | `components/products/product-card.jinja` |
| P13 | `assets/js/features/bundle-offers.js` (`collectProductIds`, `displayBundleOffer`, `loadBundleOffers`, `reload`) |

Also read but not asserted here: `components/products/product-options.jinja`
(renders vitrin's own options partial) and `product-variant.jinja` (used by the
grouped-product page) — their shape is set upstream, and P4 covers what this
theme does with the selection.

## What this does not cover

- Nothing about money: tax, shipping, coupon math, rounding and currency
  formatting belong to the cart group.
- Nothing behind a login (wishlist, review submission, order lookup), and no
  write to the shared store: P7 and P8 abort their requests.
- The PDP's schema settings (theme-settings DB is unreachable here), so
  section-level toggles on the product page are not exercised.
- Concurrency between two tabs, and slow networks: P2/P5 assume requests answer.
- `js/features/gifting.js`, loyalty and the cart's own bundle widget, which live
  in other groups.

## Keeping it honest

- Move `sync-commit:` forward only after a run of `check.sh` on the new commit,
  and after reading every `CHANGED` line.
- When you intend to change behaviour, change the property's expectation in the
  same commit (`EXPECTED` in `props/dom_states.py`, the `expected` column in
  `props/render_contracts.py`) and say why in the commit message.
- `mutants/` holds three realistic breaks, each caught when applied to a scratch copy:
  `gallery-arrows-swapped.patch` (P2: prev/next disabled states crossed),
  `questions-leak-anonymous.patch` (P11: anonymous asker's name printed),
  `time-ago-round.patch` (P1: `Math.floor` → `Math.round`). To repeat:
  `rsync -a --exclude node_modules --exclude .git <repo>/ $SCRATCH/copy/`, apply the
  patches with `patch -p1`, symlink `node_modules`, `npm run build:js` in the copy
  (JS mutants reach the browser half through the copy's built `theme.js`, which
  `check.sh` swaps in over the storefront's own), then
  `ROOT=$SCRATCH/copy bash check.sh` and expect `CHANGED P1`, `P2`, `P11` and exit 1.
  Never edit the shared checkout: the running storefront serves it.
