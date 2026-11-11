---
name: verify-search-category
description: Drive the growth-theme products, category, brand and search pages as a shopper - filters, sorting, paging, the search dropdown, price range, category and brand listings - and keep the evidence. Use before calling any change to those pages done.
---

# verify-search-category

The search/category group: the all-products listing, one category page, the categories
index, one brand page, the brands index, the header search dropdown, and the filter drawer
with its price range and sort. Launch, doctor and stop the storefront with
`.agents/skills/verify-growth-theme` (see its SKILL.md: `storefront.sh up`, then `doctor`
must print `doctor: healthy`); nothing here starts a server of its own.

```bash
S=.agents/skills/verify-growth-theme/scripts
uv run --no-project --with playwright python -I $S/drive.py --list | grep search-category
uv run --no-project --with playwright python -I $S/drive.py search-category-products
```

`drive.py` writes `summary.json`, screenshots, `network.log` and `console.log` to
`~/.cache/verify-growth-theme/evidence/<UTC stamp>-<journey>/` and exits 0 when the journey
passes. Journeys live in `journeys.py` next to this file.

## What this group covers

| Module | What it is |
|---|---|
| `templates/products.jinja` | all-products listing: grid, count line, paging, quick view |
| `templates/category.jinja` | one category: hero, breadcrumb, subcategory carousel, product grid |
| `templates/categories.jinja` | the categories index: hero, one card per category (500 on store 1), one carousel per parent |
| `templates/brand.jinja` | one brand: heading with product count, grid, filters |
| `templates/brands.jinja` | the brands index: cards with counts, paging |
| `components/categories/*` | `category-card`, `category-hero`, `subcategory-card`, `subcategories-carousel` |
| `components/brands/*` | `brand-card`, `product-brand` (the brand line on a product page) |
| `assets/js/features/search.js` | header search dialog: debounce, live results, "search for …" link |
| `assets/js/features/product-filter.js` | AJAX filtering, sorting, paging, URL building, filter chips |
| `assets/js/features/price-slider.js` | the price range slider in the filter drawer |

## Journeys

| Journey | Shopper does | Pass condition |
|---|---|---|
| `search-category-products` | Opens "all products" and takes the next-page link. | 24 cards; the header line's N = cards and M = `/api/v1/products` count; page 2 shows 24 different cards with "2" as the current page. |
| `search-category-per-page` | Switches "products on page" to 12. | `page_size=12` in the URL, 12 cards, header line 12/880 (store 1), and the page did **not** reload (an in-page marker survives). |
| `search-category-filter-attribute` | Opens Filters on a brand page, ticks the first attribute, applies, then removes the chip. | Drawer closes; the attribute is in the URL; a chip names it; the header total equals the brand-scoped API count; no navigation; the chip's X restores the 5 products. |
| `search-category-filter-price` | Types 100 and 500 in the drawer's From/To boxes and applies. | `from_price=100&to_price=500`, a Price chip, and the header total equals the API count for the same query. |
| `search-category-filter-price-clear` | On `?from_price=100&to_price=500`, clears both boxes and applies. | Both parameters leave the URL and the Price chip disappears. **Fails on 2b1c67d: F3.** |
| `search-category-filter-zero` | Filters a brand page down to a price nothing matches. | 0 cards, the "no products" text, and the Filters button + drawer still there to undo it. **Fails on 2b1c67d: F5.** |
| `search-category-sort` | On a filtered brand page picks "Price, high to low". | `sort_by=price&order=desc`, the label changes, the attribute filter survives, no reload, and the first five cards' order equals the API's order. |
| `search-category-search` | Opens the header search, types `منتج`, follows "Search for 'منتج'". | ≤ 8 result cards with `/products/` links, the all-link href is `/products?q=منتج`, and that page's header total equals the API count for `q`. |
| `search-category-categories` | Opens the categories index and clicks a subcategory slide. | 500 cards = API categories; 33 carousels = parents with children, ids unique; one `<h1>`; 12 sampled cards link to their own id+slug; the child page's `<h1>` and breadcrumb name the parent and the child. |
| `search-category-brands` | Opens the brands index, pages to 2, opens the `thumbsup` card, then opens one of its products. | 24 cards matching the API's first page in order and label; page 2 = the 7 remaining; the brand page shows "THUMBSUP (5 products)" with 5 cards and a Brands > thumbsup breadcrumb; the product page links back to `/brands/thumbsup` with the brand name. |

Both failures are real defects recorded in `formal-search-category` (F3, F5), not journey
bugs — do not loosen them. Everything else passes.

## Coverage

| Module | Driven by |
|---|---|
| `templates/products.jinja` | `search-category-products` (grid, count line, paging), `search-category-per-page`, `search-category-filter-price` (grid + count after an AJAX filter), `search-category-search` (the `/products?q=` landing page) |
| `templates/brand.jinja` | `search-category-brands` (heading, 5 cards, breadcrumb), `search-category-filter-attribute`, `search-category-sort` |
| `templates/brands.jinja` | `search-category-brands` (24 cards = API order, page 2 = remainder) |
| `templates/categories.jinja` | `search-category-categories` (500 cards, 33 carousels, hero h1) |
| `templates/category.jinja` | `search-category-categories` (the slide click lands on a real category page: hero h1, breadcrumb, carousel). Its product grid cannot be driven here: **no category on store 1 has products** (the API reports `products_count: 0` for all 500), so the page only ever renders the empty state. The grid/empty-state logic is covered by `formal-search-category`'s `listing-grid` over rendered templates. |
| `components/categories/category-card.jinja` | `search-category-categories` (500 cards, first 12 checked against the API's id+slug+name) |
| `components/categories/subcategory-card.jinja` | `search-category-categories` (click the first slide → child page) |
| `components/categories/subcategories-carousel.jinja` | `search-category-categories` (count, unique ids, slide → child) |
| `components/categories/category-hero.jinja` | `search-category-categories` (the index h1, then the same journey's child page h1) |
| `components/brands/brand-card.jinja` | `search-category-brands` (24 cards, labels vs API) |
| `components/brands/product-brand.jinja` | `search-category-brands` (the last step opens a thumbsup product and checks the brand link back) |
| `assets/js/features/search.js` | `search-category-search` (dialog, results, all-link, q landing). Escaping and render bounds: `formal-search-category` `search-escape`. |
| `assets/js/features/price-slider.js` | `search-category-filter-price` (typing 100/500 moves the handles and applies). Bounds/ordering over every URL pair: `formal-search-category` `price-slider-order`. |
| `assets/js/features/product-filter.js` | `search-category-filter-attribute`, `-filter-price`, `-filter-price-clear`, `-filter-zero`, `-sort`, `-per-page`. URL building and chip removal: `formal-search-category` `filter-url-roundtrip`, `filter-remove-semantics`, `filter-form-url`, `filter-request-order`. |

The repo's own Playwright specs (`tests/*.spec.js`) and the Jinja repro tests (`tests/repro/`)
do not touch these pages, so they add nothing here.

## Recorded run

2026-11-11, theme `2b1c67df1fb4f69637887f375d22099b90dafeb5`, vitrin
`dfd3386ba77aa760d9335db185571e7f4425d3bb`, storefront `PORT=8995`, store 1
(`my-store-2.zidtest.com`), headless Chrome, `ar-SA`, 1280×900.

| Journey | Passed | s |
|---|---|---|
| products | yes | 10.1 |
| per-page | yes | 13.0 |
| filter-attribute | yes | 14.0 |
| filter-price | yes | 9.8 |
| filter-price-clear | **no** (F3) | 8.3 |
| filter-zero | **no** (F5) | 14.8 |
| sort | yes | 10.4 |
| search | yes | 13.9 |
| categories | yes | 18.9 |
| brands | yes | 22.9 |

Timings move with how loaded the machine is; the `passed` column does not.

Full stdout: `<proof>/verify-search-category/run.txt`.
Evidence directories: same folder, one per journey.

## Evidence

Keep the evidence directory of every journey you cite; a PR claim names the journey, its
`passed` value and that path. `summary.json` carries the numbers each journey compared
(`api_count`, `count_line`, `url`, `chips`), so a reviewer can check the claim without
rerunning it.

## Gotchas

- **Two journeys replay findings.** `search-category-filter-price-clear` and
  `search-category-filter-zero` reproduce F3 and F5 in `formal-search-category` and are listed in
  `KNOWN` in `journeys.py`: `drive.py` exits 0 for a journey listed in its skill's `KNOWN` table only while it fails exactly the recorded `failed_checks` (prints `FINDING`); any other failure, a crash, or the bug no longer reproducing exits 1 with `CHANGED`. If one prints `CHANGED ... no longer reproduces`, someone
  fixed the bug: update both skills instead of "fixing" the journey.
- **Store 1 has no products in any category** (500 categories, `products_count: 0`). Category
  pages only show the empty state; do not read a category journey as proof that the category
  grid renders products.
- **Search result hrefs are absolute to `my-store-2.zidtest.com`** (the API's `html_url`), so
  never click a result card — it leaves the local instance. Assert their paths. The only
  in-store link is "Search for '…'".
- The search dropdown needs 3-4 s (SDK import + API). Wait for
  `[data-search-results]:not(.hidden)` *and* `[data-search-loading].hidden`; never
  `networkidle` (a chat widget keeps polling), never a fixed sleep.
- Filters, sorting and per-page are **AJAX** (`fetch` + `history.pushState`): set a
  `window` marker before acting to prove the page did not reload, and wait on the response
  carrying `X-Requested-With: XMLHttpRequest`, not on a timeout.
- Every Applied drawer also writes `sort_by=popularity_order&order=asc` into the URL (the
  form's hidden inputs). Assert a subset of the query, never equality.
- A brand page's filter fetch carries `brand=<uuid>` from the route, not from the URL; API
  cross-checks must add it (`_api_for_page(page, base, {"brand": …})` in `journeys.py`).
- `#products-content` is replaced wholesale on every filter/sort action — re-query after it,
  and expect `el-dialog`/`el-select` to be fresh elements each time.
- The drawer's `<details>` blocks also carry `data-filter-type`; filter chips are
  `button.badge[data-filter-type]`.
- Attribute checkbox names are `attributes[ar-اللون-en-2][]`; compare **decoded** params
  (`urllib.parse.parse_qsl`), not raw URLs.
- Card hrefs are mixed: category and product cards come from `url_for` and are absolute to
  the local instance (`http://127.0.0.1:8995/...`), brand cards are the hardcoded
  `/brands/<slug>`. Never compare `href` strings; compare `urlsplit(href).path`.
- Paging (`?page=n`) is a full page load; the search `q` landing page is too. Only per-page,
  filters and sorting stay on the page.
