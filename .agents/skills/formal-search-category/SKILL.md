---
name: formal-search-category
description: Formal properties for growth-theme's search/category group - card links, attribute escaping, listing counts, filter URL building, price-slider bounds and filter request ordering. Use when changing templates/products|category|brand|brands|categories, components/categories, components/brands or js/features/{search,price-slider,product-filter}.
sync-commit: 2b1c67df1fb4f69637887f375d22099b90dafeb5
---

# formal-search-category

Properties the products / category / brand / search / filter pages promise, checked
against the real templates and the real JS source. `check.sh` runs every property in
seconds and compares the outcome with the recorded one, so a change that breaks a
promise fails loudly instead of quietly.

```bash
.agents/skills/formal-search-category/check.sh   # ok, or CHANGED <property>
ROOT=/path/to/checkout .agents/skills/formal-search-category/check.sh
```

This is the formal half of the group; `.agents/skills/verify-search-category` drives the
same pages as a shopper in a browser. Both use the same nouns.

## Properties

Each row is one promise, the harm if it breaks, and the tool that checks it.

| Tool | Why this one |
|---|---|
| `properties/templates.py` | The question is what a browser parses out of a `.jinja` file for a given data shape. Rendering the real template is the only honest way to ask it; a copy of the template would answer for the copy. Jinja2 in a sandbox with vitrin's settings (`select_autoescape()`, `finalize`) reproduces the platform closely enough for attribute/text questions. |
| `properties/browser.py` | These modules only run against a DOM (`noUiSlider`, `FormData`, `history.pushState`, `innerHTML`), and the promise is about what the shopper's browser ends up with. Chromium executes the real module file; stubbing the DOM in Node would test the stub. |
| `properties/url_builder.mjs` | `buildCleanUrl` and `removeFilter` are pure functions over `URL`. Importing the real module in Node and driving it with generated queries reaches every case in milliseconds, with no DOM. |
| `properties/filter_race.tla` | The question is whether *some order* of two async actions breaks the page. A test can only replay the orders someone wrote; TLC enumerates every interleaving of a small model whose branches are read from the code. |

| # | Property (`expected.txt`) | Promise | Harm | Tool |
|---|---|---|---|---|
| 1 | `cards-own-record` | Every category / subcategory / brand card links to, and names, the record it was rendered for, and shows an image exactly when that record has one. | A card that points at the neighbour's category sends the shopper to the wrong aisle, and a logo-less brand renders a broken image. | `properties/templates.py` (Jinja2, the real `.jinja` files) |
| 2 | `cards-escape` | A brand or category name containing a double quote stays inside the attribute it is printed into. | Names like `شاشة 55"` break the card's `alt`/`href`; a crafted name becomes an event handler on the shop's own page (XSS). | `properties/templates.py` |
| 3 | `hero-h1-image` | The category hero renders exactly one `<h1>` carrying its title, no `<h1>` when the title is empty, and a background image only when it has one. | An empty or duplicated `<h1>` misdescribes the page to search engines and screen readers. | `properties/templates.py` |
| 4 | `carousel-scope` | A subcategories carousel renders one slide per subcategory, renders nothing when there are none, and its `<style>` block only matches its own id. | Two carousels on the categories page share a style scope, so one's sizing leaks into the other; an empty carousel shows arrows that do nothing. | `properties/templates.py` |
| 5 | `listing-grid` | Products / brands / categories listings render one card per record, the "N out of M products" line reports the rendered count and the full total, and the empty state appears only when there are no records. | "24 out of 880" next to 12 cards, or a grid plus "no products", makes the shopper think the shop lost products. | `properties/templates.py` |
| 6 | `filter-recovery` | A brand or category page whose filters match nothing still offers the filter controls. | The shopper who narrowed to zero results has no way back except the browser's back button. **Breaks today: F5.** | `properties/templates.py` |
| 7 | `search-escape` | A product name, badge or price shown in the search dropdown is text — never markup, never an attribute value. | A product named `x" onerror=…` runs script in the browser of everyone who opens search; a name with an inch mark breaks the thumbnail. **Breaks today: F1.** | `properties/browser.py` (Chromium, real module) |
| 8 | `price-slider-order` | The price drawer's two handles always describe the interval its From/To boxes show, clamped to the slider's range and never crossed. | The drawer shows a price range the shop is not filtering by, so the next Apply silently changes the filter. **Breaks today: F2.** | `properties/browser.py` |
| 9 | `filter-url-roundtrip` | Rebuilding a filter URL preserves every query parameter exactly: order, repeats and reserved characters. | A filter silently drops out of the address bar, so a reload or a shared link shows a different result set. | `properties/url_builder.mjs` (Node, real module) |
| 10 | `filter-remove-semantics` | Removing one filter — a chip, the sort, the price, or "clear all" — changes only that filter. | Removing one colour chip also drops the other colours or the search term. | `properties/url_builder.mjs` |
| 11 | `filter-form-url` | After Apply, the URL carries exactly the filters the drawer shows; a box the shopper emptied is not still applied. | The shopper clears the price box, presses Apply, and the shop keeps filtering by the old price. **Breaks today: F3.** | `properties/browser.py` |
| 12 | `filter-request-order` | Whenever the page is idle, the products on screen are the products for the URL in the address bar. | A second filter applied while the first is loading is dropped: the grid shows the first filter's products under the second filter's URL. **Breaks today: F4.** | `properties/filter_race.tla` (TLC) |
| 13 | `filter-request-order-model-sanity` | The same model with a coalescing fix keeps the invariant. | Guards against "the model is simply wrong": the property is satisfiable. | `properties/filter_race_fixed.tla` (TLC) |

## Current findings

Ordered by how much they cost a shopper. Each is reproduced by a property above.

**F1 — product names run script in the search dropdown (XSS).** `SearchManager.showResults`
interpolates `product.name`, `product.badges` and `product.price` through `escapeHtml`
(`assets/js/features/search.js:288`), which sets `textContent` and reads `innerHTML` back —
that escapes `& < >` but **not** `"`. Line 162 then puts the name into `alt="${…}"`, so a
name like `x" onerror="window.__pwned=1` closes the attribute and the rest becomes
attributes of the real `<img>`; the handler fires when the image fails to load (a broken
image URL is enough). Observed live on the test storefront: setting
`window.searchManager.showResults([{name: 'x" onerror="window.__pwned=2', image: 'https://broken.invalid/x.jpg', …}])`
left `window.__pwned === 2`. Names with an inch mark (`شاشة 55"`) hit the same line by accident.
A product name is merchant/staff/app-controlled, so this is stored XSS in the storefront
origin, not self-XSS.

**F2 — the price drawer's handles disagree with its boxes.** `initPriceSliders` clamps each
endpoint on its own and uses `||`, which treats `0` as "unset"
(`assets/js/features/price-slider.js:33-34`), while `syncFromInputs` (l.91-98) both clamps
and orders. On `/products?from_price=5000&to_price=100` the boxes read 5,000 and 100 and the
handles sit at 5,000–5,000; with `?to_price=0` the boxes read 0 and the max handle stays at
20,000. Any Apply from that drawer re-submits the boxes, so the slider is decoration that
lies about the active filter.

**F3 — an emptied price box stays applied.** `submitDrawerForm` skips empty form values
before it reaches the price branch (`assets/js/features/product-filter.js:248`), so a
`from_price`/`to_price` the shopper cleared is never sent, never deleted, and the old chip
stays. Reproduced live: from the drawer on `/products?from_price=100&to_price=500`, clearing
both boxes and pressing Apply leaves both parameters and the "Price: 100 - 500" chip. Only
"Clear all" removes it.

**F4 — the second filter wins the URL, the first wins the grid.**
`applyFilter` pushes the new URL and *then* calls `fetchProducts`, which returns immediately
when `this.isLoading` (`product-filter.js:39, 56`). The pending response renders the products
for the URL it fetched, and nothing re-fetches, so an idle page can show filter A's products
under filter B's URL. TLC finds the 3-step trace `Apply(A) → Apply(B) → Complete`
(`/statechart` reads it as a chart); two clicks in a filter drawer on a slow connection are
enough.

**F5 — a zero-result filter removes the drawer that could undo it.** `brand.jinja:38` and
`category.jinja:62` render `components/products/products-header.jinja` only
`{% if products and products.results %}`. Filter a brand page down to nothing and the whole
header — filters, sort, drawer — is replaced by "No products found in this brand"; the AJAX
swap removes it in place, so the shopper has to leave the page to relax the filter.
`templates/products.jinja` keeps its header in the same situation, which is why this reads as
a bug and not a choice.

**F6 — card templates break on a quoted merchant name.** `category-card.jinja:26`,
`subcategory-card.jinja:25`, `brand-card.jinja:21`, `category-hero.jinja:19` and
`product-brand.jinja:15,20` print names straight into `alt`/`aria-label`/`href` and vitrin
renders `.jinja` with autoescape **off** (`sdk/jinja.py:166 select_autoescape()`), so a
category called `شاشة 55"` truncates the `alt` and spills the rest into the tag. Same class as
F1, template side; `| e` on those five spots is the whole fix (the harness passes with it).

## How to run, and how to read a result

```bash
.agents/skills/formal-search-category/check.sh
```

- `ok: every property matched expected.txt` — nothing moved.
- `CHANGED <property> (recorded PASS, now FAIL)` — a real regression **unless** the covered
  code was just changed on purpose; then rerun the break proof below and update
  `expected.txt`.
- `CHANGED <property> (recorded FAIL, now PASS)` — someone fixed a finding. Delete it from
  "Current findings" and flip the line in `expected.txt`; do not leave the file claiming a
  bug that is gone.
- `PROP <id> ERROR` / `CHANGED <id> (no result: the check did not run)` — the harness, not the
  theme: a missing `uv`, `node`, `tlc`, `jinja2`, `playwright`, or a template/function that
  moved. Fix the harness before reading anything into it.
- `NOTE drift` + a `git diff --stat` — a covered file changed after `sync-commit`. The
  properties may still pass; reread them against the new code and only then move
  `sync-commit` to the new `git rev-parse HEAD`.

TLA+ results: read every one with the pstack `/statechart` skill. It turns the invariant
violation into the shortest sequence of actions in the code's own words, and draws the state
chart when the model passes.

## Bounds and assumptions

- **Templates** render through a plain Jinja2 sandbox with `select_autoescape()` — autoescape
  **off** for `.jinja`, exactly as vitrin configures it (`sdk/jinja.py`). `url_for`,
  `image_url`, `session.query_params` and the `vitrin:` includes are stubbed (a `url_for`
  that builds `/categories/<id>/<slug>` and `/brands/<slug>`; `image_url` returns its input).
  A property that raises a Jinja error is a harness error, not a finding.
- **JS** properties import the source file (`assets/js/features/*.js`), not
  `assets/dist/theme.js`, so a stale bundle cannot hide a regression; the bundle is exercised
  end-to-end by `verify-search-category`'s journeys. `price-slider.js`'s bare
  `nouislider` import is resolved to `node_modules/nouislider/dist/nouislider.mjs` from the
  same checkout, which is what vite does at build time.
- `price-slider-order` covers a 7 × 7 grid of `from_price`/`to_price` values
  (`0, 50, 100, 5000, 20000, 99999, absent`), plus typing in the To box. It does not simulate
  dragging the handles.
- `filter-url-roundtrip` covers 300 seeded queries (seed `20261111`) over the 10 keys the
  filter UI can produce and 13 hostile values (`& = # % + " <`, Arabic, spaces, commas).
  Keys are *not* generated with reserved characters: attribute keys are derived from merchant
  attribute names and are bracketed slugs; `buildCleanUrl` does not encode keys, which is only
  safe while that holds.
- `filter-request-order` is a 2-URL, 4-state model; its `Apply`/`Complete` branches come from
  `applyFilter` (pushState before fetch) and `fetchProducts` (early return on `isLoading`).
  It models the theme's own state machine, not the network.

## Coverage record

| Property | Covers |
|---|---|
| `cards-own-record` | `components/categories/category-card.jinja` (whole), `components/categories/subcategory-card.jinja` (whole), `components/brands/brand-card.jinja` (whole), `components/brands/product-brand.jinja` (whole) |
| `cards-escape` | the four above plus `components/categories/category-hero.jinja` (`alt`) |
| `hero-h1-image` | `components/categories/category-hero.jinja`: `{% if title %}` h1 guard, `{% if image %}` block |
| `carousel-scope` | `components/categories/subcategories-carousel.jinja`: root `data-subcategories-carousel`, `{% if subcategories %}`, the `<style>` block, slide loop |
| `listing-grid` | `templates/products.jinja` (grid, empty state), `templates/brand.jinja`, `templates/category.jinja`, `templates/brands.jinja`, `templates/categories.jinja`, `components/products/products-header.jinja` (count line) |
| `filter-recovery` | `templates/brand.jinja:38`, `templates/category.jinja:62`, `templates/products.jinja:28` (the header include) |
| `search-escape` | `assets/js/features/search.js`: `showResults` (l.154-184), `renderPrice`, `renderRating`, `escapeHtml` |
| `price-slider-order` | `assets/js/features/price-slider.js`: `initPriceSliders` (l.9-114, start pair l.33-34), `syncFromInputs` (l.78-99), `formatNumber`/`unformatNumber` |
| `filter-url-roundtrip` | `assets/js/features/product-filter.js`: `buildCleanUrl` (l.44-53) |
| `filter-remove-semantics` | `assets/js/features/product-filter.js`: `removeFilter` (l.140-169), `clearFilters` (l.122-138), `applyFilter` (l.19-42) |
| `filter-form-url` | `assets/js/features/product-filter.js`: `submitDrawerForm` (l.235-265), `applyFilter` |
| `filter-request-order` (+ sanity) | `assets/js/features/product-filter.js`: `applyFilter` (l.19-42), `fetchProducts` (l.55-94) |

## What is not covered

- `product.url` and `product.image` are interpolated into `href`/`src` with no escaping at all
  (`search.js:160-162`). They arrive from the API as absolute `html_url`s, so a quote is not
  reachable today; the properties assume that stays true.
- The search debounce and its request ordering (there is no cancellation, and two queries can
  resolve out of order) — only the *filter* ordering is modelled.
- `components/products/filters/default-filters.jinja` (the availability/price popovers) and
  `handleAvailability`/`handlePriceSubmit`: they render only for stores **without** attribute
  filters, and store 1 has attribute filters, so only the drawer path is exercised.
- `sections/categories.jinja` (the home-page carousel) belongs to the home-sections group.
- Whether the API returns the right products for a filter — vitrin's repository, not the theme.
- Price formatting/locale in search results (`renderPrice` escapes but does not format).

## Proving the checks can fail

Every code property was flipped once, on a scratch copy, by an edit of the kind people
actually make — a dropped guard, a `| e` added back, a hand-built query string:

```bash
S=${TMPDIR:-/tmp}/gt-search-category-break
rm -rf "$S" && mkdir -p "$S"
rsync -a --exclude node_modules --exclude .git ./ "$S"/
ln -s "$PWD/node_modules" "$S/node_modules"          # browser.py reads nouislider here
python3 .agents/skills/formal-search-category/break-proof.py "$S"
ROOT="$S" .agents/skills/formal-search-category/check.sh   # exits 1 with 11 CHANGED lines
```

`<proof>/formal-search-category/break-proof.txt` holds the recorded output: 11 of the 13 properties flipped in the expected
direction (PASS → FAIL or FAIL → PASS) and nothing else moved. The two state-machine rows are
proved as a pair instead: today's model violates `Consistent` (F4) and the coalescing variant
`filter_race_fixed.tla` satisfies it, which is the evidence that the invariant is
satisfiable rather than wrong.

Edits applied for the recorded proof (one per property):
`category-card`/`subcategory-card`/`brand-card`/`category-hero`/`product-brand` get `| e` on
alt/aria (2); `brand-card` logo guard → `{% if brand %}` (1); the hero h1 guard removed (3);
the carousel root id hardcoded (4); `{% if products.results %}` → `{% if products %}` in
`products.jinja` (5); the products-header include ungated in `brand.jinja`/`category.jinja` (6);
`escapeHtml` also escaping quotes (7); the price slider start pair ordered and `??` (8);
`buildCleanUrl` without `encodeURIComponent` (9); `removeFilter` dropping the whole attribute
(10); an emptied price box sent as `null` (11).
