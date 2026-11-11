---
name: verify-growth-theme
description: Launch vitrin locally rendering THIS growth-theme checkout (templates, sections, components and the built theme.js / cart-controller.js), doctor it, drive shopper journeys in headless Chrome and keep evidence. The base for every verify-<group> skill in this repo. Use before calling any theme change done, and before opening a PR.
---

# verify-growth-theme

The growth theme has no server of its own: vitrin (`zidsa/vitrin`) renders its Jinja
templates and the browser loads its built JS from vitrin's asset host. This skill runs
that pair on your machine:

- **vitrin** (uvicorn, a sibling `vitrin` checkout) with `USE_DEVELOPMENT_THEME=True`
  and `DEVELOPMENT_THEME_ROOT=<this checkout>`, so every `.jinja` file is read from here.
- **an asset server** (`scripts/asset_server.py`) that serves this checkout's `assets/`
  where vitrin's `asset_url` points, so the page runs this checkout's `assets/dist/*.js`.
- Upstream data is the **testing** API (`https://testing-api.zid.sa/`), store 1
  (`my-store-2.zidtest.com`). Production API URLs are refused.

Group skills (`verify-<group>`, `formal-<group>`) reference this one instead of
repeating launch and cleanup. Index: [Group skills](#group-skills).

## Prerequisites

- A `zidsa/vitrin` checkout next to the growth-theme checkout (`../vitrin`), or set
  `VITRIN_ROOT`. Any recent `master` works; record its sha with the run.
- `uv`, Node (for `npm run build`), Google Chrome, a local Redis on 6379 (DB 14 is used).
- `kubectl` access to the `testing` namespace for vitrin's first-party token (VPN on).
  Without it the product page redirects to `/auth/login` (upstream bundle offers answer 401).

## Launch, doctor, drive, stop

```bash
npm ci && npm run build             # theme.js, cart-controller.js and styles.css the asset server serves
S=.agents/skills/verify-growth-theme/scripts
export VITRIN_API_TOKEN="$(kubectl -n testing get secret vitrin-secret -o jsonpath='{.data.API_TOKEN}' | base64 -d)"
$S/storefront.sh up                 # PORT=8995 (assets on PORT+1); never print the token
$S/storefront.sh doctor             # must end "doctor: healthy"
uv run --no-project --with playwright python -I $S/drive.py --list
uv run --no-project --with playwright python -I $S/drive.py home
$S/storefront.sh down
```

`doctor` checks: both servers are the processes this script started and own their
ports; vitrin runs from the checkout `up` used (`up` records it in its state dir, so
`doctor` needs no `VITRIN_ROOT`); `/healthz` is 200; the home page loads
`dist/theme.js` from the local asset server; the served `theme.js` and `styles.css`
are byte-equal to this checkout's build; and a product page answers 200 (a 307 to
login means `up` ran without `VITRIN_API_TOKEN`). A stale build or a missing token is
a doctor failure, not a silent pass.

`up` is idempotent: a healthy run is reused, a half-alive one (one server died) is
stopped and started again. Use a different `PORT` for a second instance.

## Journeys

`drive.py <journey>` opens headless Chrome (ar-SA, 1280x900) against the instance,
runs the journey, and writes `summary.json`, screenshots, `network.log` and
`console.log` to `~/.cache/verify-growth-theme/evidence/<UTC stamp>-<journey>/`
(`VERIFY_HOME` overrides the root). Exit 0 = passed, or a journey listed in its group
skill's `KNOWN` table (`journeys.py`) failed exactly its recorded `failed_checks` (prints
`FINDING`). Exit 1 = any other failure, a crash, or a recorded finding that changed or no
longer reproduces (prints `CHANGED`).

Base journeys:

| Journey | Shopper does | Pass condition |
|---|---|---|
| `home` | Opens `/` | 200 and the header cart link renders |
| `catalog` | Home → header "all products" link | cards render; "N out of M" total = `/api/v1/products` `count` |
| `add-to-cart` | PDP of an in-stock simple product → add to cart | `POST /api/v1/cart/items` succeeds and the product is in `/api/v1/cart`; the cart is emptied after |

`drive.py` also loads `JOURNEYS` from every `.agents/skills/verify-*/journeys.py`
(each exports `{"<group>-<name>": fn(page, base, out, checks) -> bool}`). A name clash
stops the run.

## Group skills

| Feature group | Verify | Formal |
|---|---|---|
| layout (layout.jinja, header/footer, shared components, `js/main`, utils) | `verify-layout` | `formal-layout` |
| home-sections (`templates/home`, `sections/*`) | `verify-home-sections` | `formal-home-sections` |
| search-category (products, category, brands, search, filters) | `verify-search-category` | `formal-search-category` |
| product (PDP, variants, gallery, reviews, questions, notify-me, bundles) | `verify-product` | `formal-product` |
| cart (cart page, `js/cart/*`, coupon, gifting, loyalty) | `verify-cart` | `formal-cart` |
| account (wishlist, phone input) | `verify-account` | `formal-account` |
| blog (`templates/blog*`) | `verify-blog` | `formal-blog` |
| content-pages (page, faqs, shipping & payment) | `verify-content-pages` | `formal-content-pages` |

The repo's own Playwright specs (`npm test`, `tests/*.spec.js`) and the Jinja repro
tests (`tests/repro/`) are unit-level checks; the group skills use them where they fit.

## Evidence

Keep the evidence directory of every journey you cite. A PR claim names the journey,
its `passed` value and the evidence path. In the group skills, `<proof>/` means the
verification transcripts attached to the PR that last changed that skill (evidence and
transcripts are never committed).

## Gotchas

- Theme settings come from vitrin's templates DB, which is out of reach here
  (`TEMPLATES_DB_PORT=1`): pages render this theme's **schema defaults**. The home page
  renders no sections at all (there is no `templates/home.schema.json` default list), so
  `verify-home-sections` renders `sections/*.jinja` through a Jinja harness instead. Log lines
  `settings: DB fallback failed` and `Failed to fetch .po` are expected.
- Pages poll a chat widget: wait for `load` then a selector, never `networkidle`.
- The store menu renders twice (desktop and mobile drawer): use `visible=true`.
- Store 1 is shared with other agents and people: never place orders, send OTPs,
  submit reviews or questions, or change account data. Cart writes are fine if the
  journey empties the cart after (`DELETE /api/v1/cart/items`).
- Cart product ids come back as bare UUID hex without dashes; listing ids have dashes.
- The shipping & payment page is `/shipping-and-payment` (`/shipping-payment` is no route); see `verify-content-pages`.
- On Apple Silicon the script pins a native Python (`UV_PYTHON`) for vitrin's venv;
  the venv lives in the run dir, never in the vitrin checkout.
