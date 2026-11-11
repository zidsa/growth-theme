---
name: verify-product
description: Prove the growth-theme product group on a live storefront — running the real templates and built theme.js — by driving the PDP, gallery/zoom, variants, sticky bar, quick view, notify-me, reviews, questions and bundle badges in headless Chrome. Use on growth-theme before calling a product-page change done, and before opening a PR.
---

# verify-product

Product pages are where this theme earns or loses the sale, and they are the
group with the most moving parts: a buy box that follows the platform's variant
API, a carousel whose thumbnails, arrows and zoom must all agree, a sticky bar
that shadows the buy box, a quick view that borrows and must return the page's
product object, a login-free question form, and the reviews/questions pages that
aggregate shopper text.

This skill drives those on a real instance. It verifies the theme's rendering
and browser JS against the store's own API — not a mock.

## What the group covers

| Module | What it owns |
|---|---|
| `templates/product.jinja` | The PDP: buy box, options, quantity, sticky bar include, bundles, reviews/questions blocks |
| `templates/reviews.jinja`, `templates/questions.jinja` | The all-reviews and all-questions pages |
| `components/products/` | `product-card`, `product-gallery`, `product-options`, `product-variant`, `product-reviews`, `review-card`, `product-questions`, `question-form`, `notify-me-dialog`, `quick-view-modal`, `sticky-product-actions`, plus the smaller badges and grouped-product partials |
| `assets/js/product/gallery.js` | Embla carousel, thumbnail sync, video slides, arrow state |
| `assets/js/product/lightbox.js` | PhotoSwipe data collection, zoom entry points, thumbnail double-click |
| `assets/js/product/variants.js` | Option picks → price/SKU/media/stock/quantity, gallery rebuild |
| `assets/js/product/sticky-bar.js` | Show/hide against the buy box, sticky add-to-cart state machine |
| `assets/js/product/quick-view.js` | Prefetch, LRU cache, modal render, productObj save/restore |
| `assets/js/features/notify-me.js` | Stock-alert dialog: product seeding per section, phone validation, submit |
| `assets/js/features/bundle-offers.js` | Bundle badge fetch and fill on cards |
| `assets/js/question-form.js` | Ask-a-question validation and submit |
| `assets/js/time-ago.js` | Relative dates on reviews |

## Launch and doctor: see verify-growth-theme

This group rides the base skill: it renders this checkout's `.jinja` files through
vitrin and serves this checkout's `assets/` (so `assets/dist/theme.js` must be
current). Start it once, doctor it, then drive journeys.

```bash
npm ci && npm run build
S=.agents/skills/verify-growth-theme/scripts
export VITRIN_API_TOKEN="$(kubectl -n testing get secret vitrin-secret -o jsonpath='{.data.API_TOKEN}' | base64 -d)"
$S/storefront.sh up
$S/storefront.sh doctor                     # must end "doctor: healthy"
uv run --no-project --with playwright python -I $S/drive.py --list
uv run --no-project --with playwright python -I $S/drive.py product-pdp
```

Journeys live in [journeys.py](journeys.py) and are loaded by `drive.py` through
its `.agents/skills/verify-*/journeys.py` scan.

## Journeys

Run them one at a time. A journey writes `summary.json`, screenshots and the
network/console logs to `~/.cache/verify-growth-theme/evidence/<stamp>-<name>/`.

| Journey | The shopper | Passes when |
|---|---|---|
| `product-pdp` | Opens the PDP of an in-stock product with options | 200, one `#product-main-section` and one `#product-id`, a gallery slide whose image decoded, a price, the in-stock buy box visible, a sticky bar in the DOM, and no uncaught error from this checkout's JS |
| `product-gallery` | Walks the carousel with next/prev, picks thumbnails, clicks an image to zoom | each click moves the highlighted thumbnail with the slide on screen, prev is disabled only at the first slide and next only at the last, the zoom links are exactly the image media in order with an intrinsic size, and the picture that opens is the one clicked (full-size `href`) |
| `product-variants` | Picks another option on a product with options | the `/options` POST answers 200, the event fires, `#product-id`, price, SKU and sticky price all equal the API's variant, the gallery `data-media-src` list equals the variant's media, and the picked label is active |
| `product-sticky-bar` | Scrolls past the buy box and buys from the bar | hidden and `aria-hidden="true"` at the top, visible with the same price at the bottom, `POST /cart/items` succeeds, the product is in `/api/v1/cart`, the button shows success then returns to default, and the journey empties the cart |
| `product-quick-view` | Hovers a listing card and opens quick view, then closes it | the modal opens with one `#product-main-section`, a product id and price, the footer link is the card's URL, closing empties the content and restores `window.productObj` to what the page had |
| `product-notify-me` | Opens the stock-alert dialog from the buy box, the sticky bar and a card | the dialog opens with `[data-notify-product-id]` equal to that section's `#product-id` (or the card's own id), and no `stock-alerts` request is sent |
| `product-reviews` | Opens a product's reviews page (and its PDP block) | 200, one timestamp per returned review, every bar width in 0–100%, the first stamp reads as relative time, the PDP block converts the same dates — **currently fails: see Findings** |
| `product-questions` | Opens a product's questions page and submits it empty | 200, the form and submit button exist, an empty submit leaves the browser-invalid state and sends nothing, a filled form passes `checkValidity()`, no anonymous asker's name is in the page, no POST |
| `product-bundle-offers` | Browses a listing that has bundle offers | every visible badge names an offer the API returned for those products, carries at most one icon, and no badge appears without a name |

## Coverage

Every module of the group, and how it is proven here.

| Module | Proven by | Status |
|---|---|---|
| `templates/product.jinja` | `product-pdp` (renders, one buy box, sticky bar, gallery), `product-variants` (buy box follows the variant) | verified |
| `templates/reviews.jinja` | `product-reviews` | **finding**: renders review cards but never loads `js/time-ago.js`, so dates stay raw |
| `templates/questions.jinja` | `product-questions` (list, form, anonymity, no POST) | verified |
| `components/products/product-card.jinja` | `product-bundle-offers` (badge), `product-notify-me` (card trigger), `product-quick-view` (`data-open-quick-view` card) | verified |
| `components/products/product-gallery.jinja` | `product-gallery` (thumbs, arrows, lightbox data, media srcs) | verified |
| `components/products/product-reviews.jinja` | `product-reviews` (PDP block converts its stamps) | verified |
| `components/products/review-card.jinja` | `product-reviews` (one card per review, raw date in `data-time-ago-date`) | verified |
| `components/products/product-questions.jinja` | `product-questions` (list markup, anonymity) | verified |
| `components/products/question-form.jinja` | `product-questions` (renders and blocks an empty submit) | verified-partial: the browser's `required`/`type=email` layer answers first, so the module's own validator never runs on a click here; `formal-product` P8 drives it with `noValidate` |
| `components/products/notify-me-dialog.jinja` | `product-notify-me` (product id seeding per trigger, dialog open) | verified |
| `components/products/quick-view-modal.jinja` | `product-quick-view` (content, footer link, close) | verified |
| `components/products/sticky-product-actions.jinja` | `product-sticky-bar` (visibility, price, add to cart), `product-variants` (sticky price follows) | verified |
| `components/products/product-options.jinja`, `product-variant.jinja` | `product-variants` (the rendered option groups respond) | verified-partial: the option markup itself comes from `vitrin:v2/products/options/variant_options.jinja`, which this repo only includes |
| other `components/products/*` (badges, grouped-product, custom-input-fields, headless, filters) | — | not driven: the PDP this theme renders with schema defaults does not show grouped products or the headless partials on store 1; `formal-product` P9/P12 cover the card and PDP contracts by rendering them |
| `assets/js/product/gallery.js` | `product-gallery` | verified |
| `assets/js/product/lightbox.js` | `product-gallery` (zoom opens the clicked image) | verified |
| `assets/js/product/variants.js` | `product-variants` | verified |
| `assets/js/product/sticky-bar.js` | `product-sticky-bar` | verified |
| `assets/js/product/quick-view.js` | `product-quick-view` | verified |
| `assets/js/features/notify-me.js` | `product-notify-me` | verified |
| `assets/js/features/bundle-offers.js` | `product-bundle-offers` | verified |
| `assets/js/question-form.js` | `product-questions` (module loads, bound, no submission escapes) | verified-partial: native validation wins the click; see above |
| `assets/js/time-ago.js` | `product-reviews` (PDP block converts, page does not) | verified-partial: the module is correct where it is loaded; the reviews page never loads it |

The repo's own specs back the same surfaces at unit level and are worth running
too: `tests/product-gallery.spec.js` (alt text and escaping of gallery data),
`tests/product-options.spec.js`, `tests/notify-me.spec.js` (dialog target per
section), `tests/repro/test_inquiry_728_oos_markup.py` and
`tests/repro/test_inquiry_748_gallery_alt.py`.

## Recorded run

- Date: 2026-11-11 (+03)
- Theme: `2b1c67df1fb4f69637887f375d22099b90dafeb5`
- Vitrin: `dfd3386b` (a sibling checkout at `../verify-growth-theme-vitrin`)
- Store 1 (`my-store-2.zidtest.com`) via the testing API

| Journey | Result | Evidence |
|---|---|---|
| product-pdp | passed | `~/.cache/verify-growth-theme/evidence/20261111T124942Z-product-pdp` |
| product-gallery | passed | `~/.cache/verify-growth-theme/evidence/20261111T124951Z-product-gallery` |
| product-variants | passed | `~/.cache/verify-growth-theme/evidence/20261111T125005Z-product-variants` |
| product-sticky-bar | passed | `~/.cache/verify-growth-theme/evidence/20261111T125015Z-product-sticky-bar` |
| product-quick-view | passed | `~/.cache/verify-growth-theme/evidence/20261111T125026Z-product-quick-view` |
| product-notify-me | passed | `~/.cache/verify-growth-theme/evidence/20261111T125036Z-product-notify-me` |
| product-reviews | **failed — finding** | `~/.cache/verify-growth-theme/evidence/20261111T125050Z-product-reviews` |
| product-questions | passed | `~/.cache/verify-growth-theme/evidence/20261111T125105Z-product-questions` |
| product-bundle-offers | passed | `~/.cache/verify-growth-theme/evidence/20261111T125114Z-product-bundle-offers` |

Copies of every evidence directory and the full `drive.py` stdout (`run.txt`) are in
`<proof>/verify-product/`.

## Findings

**`templates/reviews.jinja` shows raw dates.** `review-card.jinja` prints
`data-time-ago-date="{{ review.created_at }}"` for every review, and
`js/time-ago.js` is what turns it into "9 months ago". The PDP's
`components/products/product-reviews.jinja` includes that script (plus the
`data-time-ago-labels` block); `templates/reviews.jinja` does not, so the
all-reviews page reads `2026-01-27 21:19:21`. The journey records both facts
(`rendered.rawLeft` on the page, `pdp_converts` on the PDP) and fails until the
page loads the script. `formal-product` P10 asserts the same thing from the
template side.

## Evidence

Keep the evidence directory of every journey you cite — screenshots show the
buy box, the zoomed image, the sticky bar and the dialogs, and `console.log`
holds the theme's own errors.

## Gotchas

- Theme settings come from vitrin's templates DB, which is unreachable here:
  the PDP shows this theme's schema defaults, so some sections (grouped
  products, custom-field-only variants) never appear on store 1.
- Pages poll a chat widget and load Tamara/Tabby/Landbot: wait for `load` and a
  selector, never `networkidle`.
- PhotoSwipe is imported from jsdelivr when the shopper clicks an image. If the
  CDN is unreachable the zoom cannot open; the journey records
  `zoom_skipped` and still checks the index contract. Do not read a skip as a
  pass for the lightbox.
- The products this group needs are discovered from `/api/v1/products` at run
  time (`has_options`, `availability`, `images`). If the shared store loses its
  last out-of-stock product or its last product with options, the journey fails
  with `no product in N matched …` — that is a data problem, not a code verdict.
- Variant switches go through the platform's own `product.js`
  (`POST /api/v1/products/{parent}/options`), loaded from `static.zid.store`.
  Offline, the buy box simply will not change and `product-variants` fails at the
  response wait — check the network log before blaming `variants.js`.
- The hidden `#product-id` input is written by the platform a beat after the
  options answer; read the response body when you need the selected variant.
- The sticky bar hides with a 300 ms timeout, and quick view closes on
  `cart-updated`; wait ~400 ms after a click before reading state.
- Cart product ids come back as bare UUID hex without dashes; listing ids keep
  their dashes.
- Store 1 is shared with people and other agents: this group never submits an
  alert, a question or a review, and the one cart write (sticky bar) is deleted
  at the end of the journey.
