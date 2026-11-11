---
name: formal-layout
description: Formal properties for growth-theme's layout group — escaping, redirect origin, phone-length verdicts, carousel bounds, template gates and component invariants — checked over bounded-exhaustive inputs and rendered templates. Use after changing layout.jinja, header/footer, components/*, js/main, js/lib/carousel, js/utils or the group's schemas.
sync-commit: 2b1c67df1fb4f69637887f375d22099b90dafeb5
---

# formal-layout

A test checks the cases someone thought to write. This skill checks the layout group's promises
over **whole input families**: every string up to length 3 from a hostile alphabet, every country ×
every digit length, every template × loyalty × direction, every show/hide sequence, every menu size.
It lives in `.agents/skills/formal-layout/` and reads the real files under `ROOT` — it never edits
them.

```bash
bash .agents/skills/formal-layout/check.sh                 # all 24 properties, ~65 s
ROOT=/path/to/copy bash .agents/skills/formal-layout/check.sh
```

Exit 0 = every property matched its **recorded outcome** (five of them are recorded findings).
Exit 1 prints `CHANGED <property> (recorded: …; now: …)`. When covered files move, it prints
`NOTE drift` plus `git diff --stat <sync-commit> -- <covered files>`; move `sync-commit` in the
frontmatter only after confirming the properties still describe the code.

## Current findings

Five properties are **recorded as failing on purpose**. `check.sh` exits 0 while they still
reproduce and exits 1 the moment they do not — do not "fix" the check to make them green.

1. **`breadcrumb` — `components/ui/breadcrumb.jinja` renders merchant text as HTML.**
   `components/ui/breadcrumb.jinja:19` and `:29` write `{{ item.label|safe }}`, and
   `templates/category.jinja:29,32` pass `category.name` as a label. A category named
   `<img src=x onerror=alert(1)>` executes in the breadcrumb of every page under that category.
   Counterexample printed by the property: the label is emitted raw, not as `&lt;img …&gt;`.
   Evidence: `check.sh` output, `PROPERTY breadcrumb finding labels-unescaped`.
2. **`settings-keys` — a merchant toggle nothing reads.** `layout.schema.json` declares
   `gifting.cart_page` (→ `settings.gifting_cart_page`); no template, section or script in the repo
   reads it (`gifting_product_page` and `gifting_add_to_cart_popup` are read). A merchant turning
   "gifting on the cart page" on sees no change.
3. **`auth-redirect` — the same-origin guard is bypassable.** `normalizeAuthRedirect` in
   `assets/js/features/layout.js:41` accepts any URL whose parsed origin matches, then returns
   `pathname + search + hash`. `new URL("/..//attacker.test", origin)` has origin `store.test` but
   **pathname `//attacker.test`**, and assigning that to `location.href` navigates to
   `https://attacker.test/` (confirmed in Chrome as well as Node). Reachable through
   `handleLoginAction(target, false)`, which is the `[data-login-redirect]` path — today that
   attribute is only ever server-rendered as `url_for(...)` (`components/products/product-reviews.jinja:63`),
   so this is a **latent** guard bypass, not a live open redirect; the pending redirect is also
   reused after `vitrin:auth:success`. Counterexample: `escapes=1,minimal=/..//attacker.test`.
4. **`footer` — footer link titles are written as HTML.** Vitrin renders `.jinja` with
   `select_autoescape()` (`sdk/jinja.py`), which is OFF for `.jinja`, and `footer.jinja` prints the
   link title without `|e`. A menu link titled `<b>x</b>` renders a `<b>` element. Counterexample:
   `violations=2` (`link title '<b>x</b>' rendered unescaped`, `link title not escaped at all`).
5. **`metafields` — text metafield values are written as HTML**, for the same reason
   (`components/shared/metafields.jinja`). Counterexample: `violations=1`
   (`text metafield value is not escaped`).

## Properties

Promise (what the code says it does) and harm (what a break costs) in one sentence each. Tools
are chosen for the cheapest check that reads the **real artifact**: plain Jinja2 for templates
(as `tests/repro` does), Node with stubbed globals for the modules that only touch
`window`/`document`/storage, and headless Chrome for anything that needs a live DOM or a real HTML
parser.

| Property | Where | Promise | Harm | Tool |
|---|---|---|---|---|
| `escape-attr` | `assets/js/utils/escape.js:escapeAttr` | For every string, `escapeAttr` inside a double-quoted attribute parses back as exactly that one attribute value, with no extra attributes and no child elements | A storefront string that breaks out of an attribute runs attacker script (XSS) | Chrome's own HTML parser via the real module (13 163 inputs: alphabet³, payloads, 2 000 seeded) |
| `auth-redirect` | `assets/js/features/layout.js:handleLoginAction` | No login or post-login redirect ever leaves the storefront's origin | A crafted return target bounces a shopper — or a fresh session — to a phishing page | Node + WHATWG `URL`, real module (46 curated + 2 000 seeded payloads, three branches) |
| `location-gate` | `assets/js/utils/customer-location.js` | A stored location counts only when it is a current, well-formed confirmed selection, and the pre-add-to-cart gate opens the selector only when every gate agrees, otherwise failing open | Either every add-to-cart is blocked by a location nag (lost sales) or the required city is silently skipped (wrong shipping price) | Node, real module (curated + 400 seeded JSON documents, 2⁵ gate truth table, throwing storage) |
| `country-table` | `assets/js/data/countries.js:validatePhoneLength` | A country's verdict is exactly determined by its declared `phoneLengths`, formatting never changes it, and every dial code `phone-input.jinja` ships exists in the table | A valid number is rejected at OTP/checkout or an impossible one is accepted and the SMS never arrives | Node, real module (199 countries × lengths 0–20 + template↔table cross-check) |
| `events` | `assets/js/utils/events.js` | `dispatch` delivers the detail to the target and bubbles, and `on`'s cleanup removes exactly that listener — same handler, same options — and nothing else | A handler that survives cleanup double-adds to cart or re-opens a dialog | Node `EventTarget` + a recording target double |
| `loading` | `assets/js/utils/loading.js` | Every show/hide sequence restores the original label and leaves `disabled` matching the last operation | A double-clicked submit button stays disabled forever (order impossible) or loses its label | Chrome + real DOM (all 63 sequences up to length 5) |
| `carousel-bounds` | `assets/js/lib/carousel.js` | The index stays in `[0, slides-1]`, the active dot equals the index, a disabled arrow sits at the bound that carousel actually reached, progress stays 0–100 %, `loop` wraps, one slide returns `null` | Arrows that stop early strand products; a mid-range disabled arrow hides half the shelf | Chrome, real module, import-mapped embla from `node_modules` |
| `main-init` | `assets/js/main.js:initCarousels` | One carousel per `[data-carousel]`, created once even across repeated `content:loaded`, with the dataset→options mapping exactly as documented | Duplicate embla instances double plugins/handlers (runaway autoplay); a mistyped attribute silently changes behaviour | Chrome, real `main.js`, sibling modules stubbed, `createCarousel` wrapped by a recording proxy |
| `loyalty-button` | `assets/js/layout-loyalty.js` | Exactly one floating button, on the side the direction says, opening the SDK dialog once per click, and nothing when the label is not defined | Two buttons overlap the cart CTA, or the rewards button opens nothing | Chrome, the real classic script + a synthetic `load` |
| `layout-gates` | `layout.jinja` | One `<main>`, one header, one footer, `data-template`, `dir`/`lang`, one theme bundle, loyalty block iff its template/loyalty gate, announcement bar iff its display/page gate | A duplicated theme bundle doubles every listener; a loyalty button on the cart page overlays checkout | Plain Jinja2 render (24 shell combos + 12 announcement combos) |
| `settings-keys` | `layout.jinja`, `header.jinja`, `footer.jinja`, `components/**` vs `*.schema.json` | A template never reads a `settings.*` key its schemas do not declare, and the group's schemas declare no key nothing reads | A typo silently disables a merchant toggle; a dead toggle makes a merchant believe it works | Jinja AST over the group templates + the whole repo |
| `footer` | `footer.jinja` | One list per visible link group, every link kept with its href, labels escaped, richtext `about_us` passed through | A footer link disappears or a merchant-supplied label injects markup | Plain Jinja2 render |
| `404-countdown` | `templates/404_not_found.jinja` (inline script) | The rendered countdown ticks 3, 2, 1, 0, redirects home exactly once, never goes negative, and clears its interval | A 404 that never leaves, redirects instantly, or counts into negatives | Render + execute the real inline script against fake timers (`props/run_script.mjs`) |
| `rating-stars` | `components/rating-stars.jinja` | Always exactly five stars, filled = half-up of the rating, nothing when `rating` is `none` | A 4.9-rated product showing three stars loses the sale | Plain Jinja2 render (16 ratings incl. halves and garbage) |
| `main-nav` | `components/header/main-nav.jinja` | `min(n,6)` items visible, *More* iff `n>6`, overflow exactly `n-6`, no item in both lists | A menu item silently disappears from the shop | Plain Jinja2 render (n = 0…10) |
| `mobile-drawer` | `components/header/mobile-drawer.jinja` | Every menu item exactly once, region control iff >1 country or language, exactly one login entry | Mobile shoppers cannot reach a category | Plain Jinja2 render (n × 1/2 countries × 1/2 languages) |
| `logo` | `components/header/logo.jinja` | Exactly one image when any logo source is configured, the store-name heading otherwise | Two logos overlap in the header | Plain Jinja2 render (4 source branches) |
| `region-selector` | `components/header/region-selector.jinja` | The region button appears iff zone selection, >1 country or >1 language (minus the hide settings); the stored-branch script only in coordinates mode | A region control that opens an empty dialog, or a missing one blocking country switching | Plain Jinja2 render (16 flag combos) |
| `quantity-input` | `components/ui/quantity-input.jinja` | One number input whose value/min/max match the props, both actions present, remove only with `show_delete` | Quantity 0/NaN or a missing clamp oversells stock | Plain Jinja2 render |
| `disclosure` | `components/ui/disclosure.jinja` | Checkbox when multi-open, radio with the group name when single, one input, label wired to it, content passed as HTML | Every FAQ panel opens at once, or the label stops toggling | Plain Jinja2 render |
| `breadcrumb` | `components/ui/breadcrumb.jinja` | Labels are HTML-escaped, exactly one `aria-current`, one separator per gap | **Finding**: stored XSS from a category name | Plain Jinja2 render with an injection payload |
| `pagination` | `components/ui/pagination.jinja` | The active page is not a link and carries `aria-current`, a disabled arrow has no `href`, an enabled one keeps the whole query string | Clicking disabled "next" navigates to page 0 and drops filters | Plain Jinja2 render of the macros in both states |
| `metafields` | `components/shared/metafields.jinja` | Nothing when the store flag is off, one row per visible field, `json` skipped, text escaped, table rows/cells match the data | A disabled feature leaks, or a table renders wrong | Plain Jinja2 render (6 data types) |
| `phone-input` | `components/ui/phone-input.jinja` | The options are exactly the given country list (18 defaults), dial codes preserved, the current selection from `country_code` with first-country fallback, both hidden inputs set | The submitted number carries the wrong country code and OTP fails | Plain Jinja2 render + `country-table`'s template cross-check |

## Reading a result

- `PROPERTY <id> ok <signature>` — the promise holds over the stated inputs.
- `PROPERTY <id> finding <signature>` followed by indented lines — a counterexample in code terms.
  Compare against **Current findings** above: the three recorded ones are expected, anything else
  is a new break, and `check.sh` reports it as `CHANGED`.
- `CHANGED <id> (missing from this run)` or `PROPERTY harness error` — the **harness** failed
  (missing `node`/`uv`, missing file in a partial copy, Chrome unavailable, page crash). Read the
  `tool:` lines `check.sh` prints; that is not a product verdict.
- A real finding can be reproduced by hand. For `auth-redirect`:
  `node -e 'const u=new URL("/..//attacker.test","https://store.test"); console.log(u.origin,u.pathname)'`
  prints `https://store.test //attacker.test`.

## Bounds and assumptions

- **escape-attr**: strings only (non-strings are stringified), **double-quoted attribute context**.
  `escapeAttr` does **not** escape `'`, so a single-quoted attribute is out of scope — never place
  its output in one. Strings containing NUL or CR are excluded from the round-trip assertion because
  the HTML parser normalises them before the attribute is set; their structure (one attribute, no
  children) is still asserted.
- **auth-redirect**: URL parsing is Node's WHATWG `URL` (the spec Chrome implements; the
  `/..//` bypass was also confirmed in Chrome). `addToUrl` is `false` — the
  `[data-login-redirect]` path; with the default `addToUrl` the path prefix keeps the target
  same-origin.
- **location-gate**: storage is JSON in `localStorage`; expiry cases are relative to the real
  `Date.now()`; the gate truth table covers `locationSelectionEnabled` × mode × stored ×
  fail-open flag × mounted dialog.
- **country-table**: bounded to `code`/`dialCode` lookups and national lengths 0–20 (E.164 caps
  at 15); countries with an empty `phoneLengths` are checked against the documented 7–15 fallback.
- **carousel-bounds / main-init**: fixed DOM fixture (300 px slides in a 400 px viewport, LTR);
  two-slide fixtures are bounds-only because embla collapses them to a single snap. `main.js`'s
  sibling modules are stubbed and `createCarousel` is wrapped by a recording proxy — the property
  is about `main.js`'s own wiring, not theirs.
- **templates**: plain-Jinja2 harness (`tests/repro` style) with vitrin's autoescape setting,
  `select_autoescape()`: OFF for `.jinja`, so an escaping property sees what production renders. Platform filters that are not modelled
  (`localized_url`, …) pass their value through; `vitrin:` includes render empty; translations are
  null, so `_("x")` returns `x`. Renders use fixture data, not store 1's data.
- **404-countdown**: fake `setInterval`/`clearInterval`; the script is the exact text the template
  emitted, with `url_for('home')` already substituted.
- **loyalty-button**: `load` is dispatched synthetically; the SDK dialog is a stub with a call
  counter.

## Not covered

- Visual/layout regressions (geometry, CSS, RTL mirroring beyond the `dir` attribute) — no pixel
  assertions anywhere.
- The Vitrin SDK's own dialogs (`region_settings_dialog`, `auth_dialog`, `loyalty_rewards_dialog`)
  beyond "the theme calls them once"; their internals live outside this repo.
- Real merchant data shapes: menus with sub-menus, metafield tables with mixed cell types,
  announcement bars with URLs, store menus larger than 10 items.
- Network failure paths (failed add-to-cart, offline), the cart bundle (`cart-controller.js`) and
  every other feature group.
- Translation content and the `.po` files.

## Coverage record

| Property | Covers |
|---|---|
| `escape-attr` | `assets/js/utils/escape.js` (whole file) |
| `auth-redirect` | `assets/js/features/layout.js:handleLoginAction`, `:normalizeAuthRedirect`, `:getProfileRedirect` |
| `location-gate` | `assets/js/utils/customer-location.js` (whole file) |
| `country-table` | `assets/js/data/countries.js` (table + `validatePhoneLength`, `isPossiblePhoneNumber`, `getByCode`, `getByDialCode`), `components/ui/phone-input.jinja` default list |
| `events` | `assets/js/utils/events.js:dispatch`, `:on` |
| `loading` | `assets/js/utils/loading.js:showSpinner`, `:hideSpinner`, `:showLoading`, `:hideLoading` |
| `carousel-bounds` | `assets/js/lib/carousel.js:createCarousel`, `:setupNavigation`, `:setupDots`, `:setupProgress`, `:createConditionalCarousel` |
| `main-init` | `assets/js/main.js:initCarousels`, `:init` |
| `loyalty-button` | `assets/js/layout-loyalty.js` (whole file) |
| `layout-gates` | `layout.jinja` (shell + loyalty gate + announcement include), `header.jinja`, `footer.jinja` include points, `components/header-announcement-bar.jinja` |
| `settings-keys` | `layout.jinja`, `header.jinja`, `footer.jinja`, `components/**` reads vs `layout.schema.json`, `header.schema.json`, `footer.schema.json` |
| `footer` | `footer.jinja` link groups, about block, contact block |
| `404-countdown` | `templates/404_not_found.jinja` (markup + inline `startRedirectCountdown`) |
| `rating-stars` | `components/rating-stars.jinja` |
| `main-nav` | `components/header/main-nav.jinja` (visible/overflow split) |
| `mobile-drawer` | `components/header/mobile-drawer.jinja` |
| `logo` | `components/header/logo.jinja` |
| `region-selector` | `components/header/region-selector.jinja` |
| `quantity-input` | `components/ui/quantity-input.jinja` |
| `disclosure` | `components/ui/disclosure.jinja` |
| `breadcrumb` | `components/ui/breadcrumb.jinja` (label escaping) |
| `pagination` | `components/ui/pagination.jinja` (`Pagination`, `PaginationLink`, `Pagination{First,Previous,Next,Last}`) |
| `metafields` | `components/shared/metafields.jinja` |
| `phone-input` | `components/ui/phone-input.jinja` (options, current selection, hidden inputs) |

## Files

- `check.sh` — one command, `ROOT` override, recorded outcomes in `EXPECTED`.
- `props/templates.py` — Jinja properties (`settings-keys`, `layout-gates`, `footer`,
  `404-countdown`, the component suite).
- `props/node.mjs` — Node properties (`auth-redirect`, `location-gate`, `country-table`, `events`).
- `props/browser.py` — Chrome properties (`escape-attr`, `loading`, `carousel-bounds`, `main-init`,
  `loyalty-button`); serves the real modules by request interception, no server or build step.
- `props/run_script.mjs` — executes the rendered 404 script against fake timers.
- `mutants/*.patch` — the three breaks used to prove the check can fail (see
  `<proof>/formal-layout/break*.txt`).
