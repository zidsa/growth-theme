---
name: verify-layout
description: Verify growth-theme's layout group (document shell, header, footer, shared components, layout JS utils, carousel, 404) against a live vitrin storefront in headless Chrome. Use before shipping any change to layout.jinja, header.jinja, footer.jinja, components/*, js/main, js/lib, js/features/layout or js/utils.
---

# verify-layout

The layout group is everything a shopper sees on **every** page: `layout.jinja` and the
Jinja includes it pulls in (`header.jinja`, `footer.jinja`, `components/*`), plus the JS that
wires the shell (`js/main.js`, `js/lib/carousel.js`, `js/features/layout.js`,
`js/layout-loyalty.js`, `js/utils/*`). A break here is not one bad page — it is every page.

This skill drives the running storefront. Launch, doctor, ports, the testing API, evidence
layout and cleanup all live in **verify-growth-theme**; do not repeat them here.

## Modules this skill covers

| Module | Paths |
|---|---|
| components (root) | `components/header-announcement-bar.jinja`, `components/rating-stars.jinja` |
| components/header | `logo.jinja`, `main-nav.jinja`, `mobile-drawer.jinja`, `region-selector.jinja`, `search.jinja` |
| components/shared | `metafields.jinja` |
| components/ui | `breadcrumb.jinja`, `disclosure.jinja`, `pagination.jinja`, `phone-input.jinja`, `quantity-input.jinja` |
| js/data | `countries.js` |
| js/features | `layout.js` (login redirect, auth visibility, locale forms, announcement bar height) |
| js | `layout-loyalty.js`, `main.js` |
| js/lib | `carousel.js` |
| js/utils | `customer-location.js`, `escape.js`, `events.js`, `loading.js` |
| layout | `layout.jinja`, `header.jinja`, `footer.jinja`, `layout.schema.json`, `header.schema.json`, `footer.schema.json` |
| templates | `templates/404_not_found.jinja` (inline countdown JS) |

## Launch and doctor

See **verify-growth-theme** for `storefront.sh up|doctor|down`, the vitrin checkout, the
testing API and the asset server. One instance is normally already running on 8995; confirm
it before driving:

```bash
bash .agents/skills/verify-growth-theme/scripts/storefront.sh doctor     # must end "doctor: healthy"

# run one journey (sequential, never in parallel)
uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py layout-shell

# all layout journeys, one at a time
for j in layout-shell layout-nav layout-carousel layout-phone layout-loyalty layout-404 layout-auth; do
  uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py "$j"
done
```

`drive.py` loads this directory's `journeys.py` automatically (`JOURNEYS` in this folder).
Evidence lands in `~/.cache/verify-growth-theme/evidence/<UTC stamp>-<journey>/`.

## Journeys

| Journey | Shopper does | Pass condition |
|---|---|---|
| `layout-shell` | opens `/`, then `/products` | one `<main id="main">`, one header, one footer, `dir=rtl lang=ar`, `data-template` matches, exactly one `dist/theme.js` from the local asset server, `layoutConfig.profileUrl` ends `/account`, cart link `/cart` with one cart badge, exactly one logo image or the store-name heading, footer link groups and links render, ≤1 announcement bar, `/products` keeps the same frame plus one breadcrumb; zero console errors attributed to theme assets |
| `layout-nav` | opens `/`, reads the desktop menu, clicks *More*, opens search | desktop shows `min(n,6)` items + *More* iff `n>6`; overflow count `n-6`; no item is both visible and overflow; every visible href is non-empty; every desktop label also appears in the mobile drawer (`n = drawer children`); *More* popover opens; search dialog opens, an Arabic query renders results or the empty state, the "all" link points at `/products?q=…`, the clear button appears |
| `layout-carousel` | PDP of an in-stock product → clicks *next* until it stops, then *prev* past the start | ≥2 slides; progress stays in 0–100 and never decreases; a disabled arrow sits at the bound that carousel actually reached (never mid-way); both arrows share one visibility state; prev disabled at start for non-loop carousels; `content:loaded` does not duplicate a carousel; zero theme console errors |
| `layout-phone` | PDP of an out-of-stock product → *notify me* → country selector | dialog opens with `n` country options equal to `assets/js/data/countries.js` rows (199) when `data-all-countries="true"`; `+966` is selected in display, hidden input and full value; search "Egypt" narrows to `+20`; selecting it updates display + hidden code and the full value starts `+20`; nothing is submitted |
| `layout-loyalty` | opens `/` then `/cart` | `/` has one `js/layout-loyalty.js` script, exactly one visible floating button on the RTL side (`left:40px`), label text, one dialog open per click; `/cart` (`cart_page`) has neither script nor button |
| `layout-404` | opens an unknown path | 404 status, `404_not_found` template, one home CTA, countdown starts at 3 and only decreases in 0–3 down to ≤1, then the tab is on `/` |
| `layout-auth` | opens `/`, opens the mobile drawer at 390px, clicks the header login button, then calls `handleLoginAction` with a hostile target while signed in (state stubbed — store 1 cannot log in) | login button visible / profile hidden, `handleLoginAction` is a function, drawer opens with the login entry and all 14 menu items, one auth dialog open per click, and a hostile `https://attacker.test/collect` target never leaves the origin (lands on `/account` → `/auth/login?redirect_to=%2Faccount`) |

Unit-level references from this group (not edited here, run them as they are):

```bash
npx playwright test tests/layout-auth.spec.js tests/customer-location.spec.js
```

They cover redirect normalisation and the customer-location gate in the test harness; the
journeys above cover the same modules against a real page.

## Coverage

Every module of the group, and how it is proven. "Journey" means the table above; "spec"
means a repo test; "formal" means `formal-layout` (the property named); "n/a" gives the reason.

| Module | Verify | Why this is enough / why not more |
|---|---|---|
| `components/header-announcement-bar.jinja` | `layout-shell` (bar count ≤1 through the page shell) + formal `layout-gates` | store 1 ships the bar **off** by default (`announcement_bar_display` default), so the live page can only prove "absent, never duplicated"; the display/page_display truth table is proven in `formal-layout` by rendering the component through `layout.jinja` |
| `components/rating-stars.jinja` | formal `rating-stars` only | not rendered by store 1's default templates (no review block on the default PDP sections); proven by rendering the component over rating 0–5 incl. halves and garbage values |
| `components/header/logo.jinja` | `layout-shell` (exactly one logo image or heading) | live header renders the store logo; the four logo-source branches are enumerated in formal `logo` |
| `components/header/main-nav.jinja` | `layout-nav` | store 1's menu has 14 items, so the live split is the interesting one: 6 visible + 8 in *More* |
| `components/header/mobile-drawer.jinja` | `layout-nav` (label parity), `layout-auth` (drawer opens, login entry) | drawer is rendered twice; the journey reads the drawer's own children, not visibility |
| `components/header/region-selector.jinja` | formal `region-selector` only | the shared `region_settings_dialog` SDK is **not mounted** on this instance (no custom elements registered), so a click proves nothing beyond "no throw"; the visibility gate (countries/languages/zone flags × hide settings) is enumerated in formal |
| `components/header/search.jinja` | `layout-nav` | dialog opens, real query renders 8 product results, all-link and clear button work |
| `components/shared/metafields.jinja` | formal `metafields` only | store 1 has no metafields (`is_metafields_enabled` off), so live rendering is empty; the eight data types, the language fallback, the json skip and the table shape are enumerated in formal |
| `components/ui/breadcrumb.jinja` | `layout-shell` (renders on `/products` with 3 items) | the escaping promise is a **finding** proven by formal `breadcrumb`, not by driving |
| `components/ui/disclosure.jinja` | `layout-nav` (`/products` aside renders 3 disclosure wrappers) | live markup present; radio/checkbox and label wiring are enumerated in formal `disclosure` |
| `components/ui/pagination.jinja` | `layout-nav` (products page has `[data-slot=pagination]`; **no** page 2 on store 1's default listing, so linking is only structurally present) + formal `pagination` | the interesting promise (a disabled arrow must not carry an href, an enabled one keeps the full query string) is proven in formal over both states |
| `components/ui/phone-input.jinja` | `layout-phone` | 199 options from `countries.js`, `+966` default, search, selection and hidden-value sync all driven live |
| `components/ui/quantity-input.jinja` | `layout-carousel`'s PDP loads 8 components; formal `quantity-input` | PDP quantity controls are owned by the product group; the min/max/value/remove promise is enumerated in formal |
| `js/data/countries.js` | `layout-phone` (199 options rendered) + formal `country-table` | the validator's verdicts for every country × length 0–20, the table invariants and the template↔table dial-code agreement are formal; the live page proves the table is what the selector renders |
| `js/features/layout.js` | `layout-auth` + spec `tests/layout-auth.spec.js` + formal `auth-redirect` | live: guest click opens the dialog, signed-in hostile target stays on origin. The exhaustive redirect guard is formal (**finding**: `/..//attacker.test`) |
| `js/layout-loyalty.js` | `layout-loyalty` | both directions: present on a non-excluded template, absent on `/cart` |
| `js/lib/carousel.js` | `layout-carousel` + formal `carousel-bounds` | live PDP carousels + module-level bounds/dots/progress/loop |
| `js/main.js` | `layout-carousel` (data attributes on the real PDP carousels) + formal `main-init` | one carousel per container, once, and the dataset→options mapping |
| `js/utils/customer-location.js` | spec `tests/customer-location.spec.js` + formal `location-gate` | the live store does not require a location, so the gate cannot be observed in the browser; the truth table and storage validation are formal |
| `js/utils/escape.js` | formal `escape-attr` | the only consumer is the product gallery (other group); no page renders attacker-controlled attribute text through it, so the property is the proof: 13 163 inputs, one attribute, exact round trip |
| `js/utils/events.js` | formal `events` | dispatch/on/cleanup have no page-level symptom to drive |
| `js/utils/loading.js` | formal `loading` | spinner behaviour is only observable under a slow submit; all 63 show/hide sequences are proven instead |
| `layout` (`layout.jinja`, `header.jinja`, `footer.jinja`, schemas) | `layout-shell`, `layout-404`, `layout-loyalty`, `layout-auth` + formal `layout-gates`, `footer`, `settings-keys` | live shell invariants on two templates; every gate (loyalty × template, announcement × page_display), the footer's grouped links and the schema↔template key set are formal |
| `templates/404_not_found.jinja` | `layout-404` + formal `404-countdown` | live countdown and redirect, plus the rendered inline script executed against fake timers |

## Recorded run

- Date: **2026-11-11** (UTC), theme `2b1c67df1fb4f69637887f375d22099b90dafeb5` (= `origin/main`),
  vitrin `dfd3386ba77aa760d9335db185571e7f4425d3bb`, instance `http://127.0.0.1:8995`
  (assets on 8996), store 1, schema defaults, `ar-SA` 1280×900.
- Result: **7/7 journeys passed**. Durations: shell 9 s, nav 16 s, carousel 25 s, phone 10 s,
  loyalty 10 s, 404 22 s, auth 15 s. Stdout: `run.txt` next to this skill's evidence copy.

## Evidence

Every journey's directory (screenshots, `summary.json`, `network.log`, `console.log`) is copied to
`<proof>/verify-layout/`. A PR claim quotes the
journey name, its `passed` value and the evidence directory.

## Gotchas

- The storefront serves **schema defaults**: the announcement bar is off, the home page has no
  carousel, store 1's menu (14 items) is what exercises the 6+_More_ split. Say "not rendered by
  the defaults" instead of "broken" when a component is absent.
- The region dialog and the loyalty/auth dialogs come from the Vitrin SDK. `region_settings_dialog`
  is not mounted on this instance; `auth_dialog` and `loyalty_rewards_dialog` are, and they open a
  **MUI modal that intercepts clicks** — press `Escape` or reload before the next click, or the
  next `locator.click()` times out behind the overlay.
- Menu labels are not translated in this environment (`_()` returns the msgid), so the overflow
  trigger reads `More`.
- The 404 page redirects ~4 s after load. Navigate with `wait_until="commit"` and poll; a normal
  `goto(..., "load")` can raise `net::ERR_ABORTED` when the redirect wins the race.
- `#redirectCountdown` shows `0` for a single tick and navigates in the same tick, so `0` is often
  never painted: assert the run 3→2→1 and the redirect, not that `0` was seen.
- Carousel buttons are `<button disabled>` **and** carry `invisible` when the carousel cannot
  scroll at all; a disabled-but-visible arrow is normal (the theme dims it). Read
  `[data-carousel-progress]` width and `disabled`, not classes alone.
- `js/layout-loyalty.js` is a **classic** script (no build step) loaded after `vitrin_body`; on
  `cart_page`, `product_details`, `page_details` it is not emitted at all.
- Phone input option markup: options carry `data-dial-code`/`data-country-code` (ISO), the trigger
  is `[data-slot="country-trigger"]`, the search box is `[data-phone-country-search]`.
- `/products` returns `data-template="list_products"` and the 404 page
  `data-template="404_not_found.jinja"` — do not assert the file stem for those two.
