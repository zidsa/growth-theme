---
name: formal-content-pages
description: Check the growth-theme content pages (FAQs, custom/policy pages, shipping & payment with its cities dialog and copy buttons) against stated promises, with property checks on the real .jinja and shipping-payment.js. Use when a change touches those templates, components/shipping-payment or assets/js/shipping-payment.js, or before believing a fix there.
sync-commit: 2b1c67df1fb4f69637887f375d22099b90dafeb5
---

# formal-content-pages

`verify-content-pages` drives these pages in a browser against store 1. This skill states their
promises as properties and checks every case in a stated scope: a matrix of shipping method
shapes, seeded-random city lists with ten search terms each, and the double-click copy sequence.
It needs no server, runs in about 10 s, and prints one line per property.

```bash
bash .agents/skills/formal-content-pages/check.sh                 # this checkout
ROOT=/path/to/checkout bash .agents/skills/formal-content-pages/check.sh
```

Exit 0: every property has the outcome recorded below, including the **five recorded violations**
(three distinct defects), which are open, not passes. Exit 1 with a `CHANGED <property>` line: an
outcome moved (a finding was fixed, or something broke). Exit 2: the harness could not run
(no Chrome, not a growth-theme checkout); read the error, do not guess. Run output goes to
`~/.cache/formal-content-pages/`, never into this directory.

## The properties

Tools: **J** = plain-Jinja2 render of the real template (`harness/render_props.py`), chosen because the
template is the code under test. **B** = the real, unmodified `assets/js/shipping-payment.js` loaded in
headless Chrome through Playwright over a page rendered from the real templates
(`harness/dom_props.py`), chosen because the file only runs against a DOM and builds markup itself.
No TLA+: nothing here has an ordering race worth a model.

Template properties (J):

- **FaqAccordionShape** (`templates/faqs.jinja`). Promise: N FAQs render N toggle buttons paired by id with N
  panels, only the first open, answers rendered as HTML, and zero FAQs show only the empty state. Harm: a
  question whose button controls the wrong or no panel cannot be opened.
- **PageShape** (`templates/page.jinja`). Promise: exactly one `h1` equal to the page title, the title tag reads
  `title – store`, the breadcrumb ends on the title, and the content is emitted verbatim in the prose block.
  Harm: a policy page with a missing or doubled heading, or a mangled body.
- **ShippingRowsMatchData** (`shipping-table.jinja`, `shipping-cards-mobile.jinja`). Promise: for 150 method shapes
  (0/1/3/4/10 cities x cost none/one/range x five COD states x image or not), each method shows its name, the first
  three cities plus a "+N more" trigger exactly when there are more than three (N correct, carrying the method id and
  name), "All areas" only with no cities, "Free" only with no cost, every cost string, and COD as Not supported /
  Available / fee strings by flag; the table and the mobile cards agree; no methods shows only the empty state. Harm:
  a shopper reads free delivery or COD where there is none, or cannot open the full area list.
- **ShippingPageSections** (`templates/shipping_payment.jinja`, `cities-dialog.jinja`). Promise: every id is unique,
  there is exactly one dialog, one search/title/list/empty hook (what the JS queries), the bank section exists iff there
  are banks, shipping opens by default and payment/banks start closed, every close button targets the dialog, every
  "+N more" trigger id resolves in the embedded data, and the script loads once with `defer`. Harm: a duplicated or
  missing hook makes the JS bind the wrong element or throw, and an unresolved trigger silently does nothing.
- **PaymentAndBanks** (`payment-methods.jinja`, `bank-accounts.jinja`). Promise: one image per icon, never an empty alt,
  the description only when set, one copy button per present account number / IBAN carrying exactly that value, an
  aria-label on each, logo and beneficiary only when set, empty states otherwise. Harm: a copy button that copies a
  different number than the one shown sends a customer's transfer to the wrong account.
- **JsonIslandIsInert** (`shipping-table.jinja`, `#shipping-methods-data`). Promise: whatever a method or city is called
  (`</script>`, `<!--`, quotes, U+2028), the embedded JSON parses back to the same data and contains no `</` or `<!--`.
  Harm: a name containing `</script>` ends the block and injects markup page-wide. **holds** (Jinja's `tojson`
  escapes `<`, `>`, `&`, `'`).
- **FaqTextEscaping**, **PageTitleEscaping**, **ShippingTextEscaping**. Promise: a merchant- or API-supplied plain
  string (FAQ question, page title, method / city / bank / beneficiary / payment names, account number, IBAN,
  cost and COD strings, payment description, image URL) is shown as text and cannot become markup or break out of
  an attribute. Harm: a string with `<` or `"` renders as elements. **FINDING 1.** (FAQ answers and page content are
  `|safe` on purpose: they are rich text.)

Browser properties (B):

- **CitiesDialogRenders** (`renderCities`). Promise: for any city list, any mix of `country.name` / `country_name` /
  none, and any search term (including `(`, `[a-`, `\`, other-case, a country name, no match), the dialog shows exactly
  the cities whose name or country contains the term, grouped by country in first-seen order, with `(N cities)` equal to
  the tags listed, the empty state iff nothing matches, and the accordion layout iff more than one country remains.
  Harm: a shopper looking for their city is told it is not covered. 140 cases, seed 20261111. **holds.**
- **CitiesDialogLifecycle** (`openCitiesDialog`, trigger binding, country accordion). Promise: a trigger opens the dialog
  titled with its method; reopening clears the search and shows the new method's cities only; the close button closes;
  an id that is not in the data neither opens nor throws; a country header collapses and re-expands its cities and
  rotates its icon. Harm: a stale list shows another courier's coverage.
- **CityTextEscaping** (`renderCities`, tag creation). Promise: a city name is shown as text. Harm: markup in a city
  name becomes DOM. **holds** (tags use `textContent`).
- **CountryTextEscaping** (`renderCities`, `headerEl` / `triggerEl` templates). Same promise for the country name.
  **FINDING 2.**
- **CopyButtonCopies** (`initCopyButtons`). Promise: each copy button writes exactly its `data-copy-value` to the
  clipboard once per click, shows the check, and restores its icon after 2 s. Harm: the wrong number copied.
- **CopyFeedbackRestores** (`initCopyButtons`). Promise: after any number of clicks and all timers, the button shows its
  original icon. Harm: a stuck checkmark says "copied" on a button that no longer shows what it is. **FINDING 3.**

## Current findings, in code terms

1. **No text is escaped in these templates.** vitrin builds its Jinja environment with
   `autoescape=select_autoescape()` (`sdk/jinja.py`), which does not match `.jinja`, so `{{ x }}` is raw; live
   `/shipping-and-payment` emits a literal `Shipping & Payment`. The harness renders the same way. Sinks that become markup:
   `faq.question`; `page.title` in the `h1`, the title tag and (also via `item.label|safe` in `components/ui/breadcrumb.jinja`)
   the breadcrumb; and in the shipping page the method name, city names, cost and COD strings, image URL, payment names and
   description, bank name, beneficiary, account number and IBAN. The last two also land in `data-copy-value="..."` attributes.
   Today these strings come from merchants, so this is a self-inflicted display defect (a name with `<` or `"` renders
   wrong) and an XSS path for anyone who can edit them but not the rich-text pages. One fix in vitrin's environment (autoescape for `.jinja`) or `|e` in these templates closes all of them.
2. **The country name is written with `innerHTML`** in `renderCities` (single-country header and multi-country trigger).
   A country named `<img src=x onerror=...>` runs the handler when the dialog opens (replayed live by
   `content-pages-cities-country-escaped`). City names are safe (`textContent`). Live data cannot show it: store 1's cities
   carry no country, so the dialog says "Other" and the multi-country branch is not reachable there.
3. **Copy feedback sticks after a quick second click** (`initCopyButtons`). `originalSvg` is read from the button at click
   time; a second click inside the 2 s window reads the check icon as "original", and its timer later restores the check.
   Final state: the copy icon is gone for good (the button still copies). Also not covered by a property:
   `navigator.clipboard` missing (plain http off localhost) throws inside the `try`, is logged, and the shopper sees nothing.
   And the dialog's "(N cities)" and "Other" are English literals in JS, so an Arabic store shows them in English.

## Reading a result

- `CHANGED <property>: recorded holds, now violation`: a real break in the covered files (or a fixture drifted). Read the
  detail lines under it; each names the case (method shape, term, field). Reproduce in `journeys.py` if in doubt.
- `CHANGED <property>: recorded violation, now holds`: a finding was fixed. Update `EXPECTED` in both harness files, this
  file and the finding.
- `NOTE drift` plus a `git diff --stat`: a covered file moved since `sync-commit`; re-read it against the properties.
- A Python traceback or `ERROR` with exit 2 is the harness (fixture or selector no longer matches the markup); the
  oracle in `dom_props.py:expected_view` is independent of the JS and should be corrected from the spec, not the code.

## Bounds and assumptions

- Templates render with `autoescape=False`, `trim_blocks`/`lstrip_blocks` as in vitrin; `layout.jinja`, `_()`,
  `image_url()`, `url_for()` and `asset_url` are stand-ins. Everything else is the real file.
- Shipping method shapes: cities {0,1,3,4,10}, cost {none, one, range}, COD {off, off+fee, on, on+fee, on+2 fees}, image
  {yes, no}. Payment icons {0,1,3}; banks all 16 present/absent combinations. Dialog: 14 city lists (4 country modes,
  4/5/9/25 cities), 10 search terms each; names are ASCII plus `(`.
- `<el-disclosure>` open/close is the platform component, not theme code: asserted for markup defaults only (J), behavior is
  in `verify-content-pages`.
- Clipboard is a recorder and the page clock is faked; real permission prompts are not modeled.

## Coverage record (property -> file:function)

| Property | Tool | file:function | Today |
|---|---|---|---|
| FaqAccordionShape | J | `templates/faqs.jinja` | holds |
| PageShape | J | `templates/page.jinja` | holds |
| ShippingRowsMatchData | J | `components/shipping-payment/shipping-table.jinja`, `shipping-cards-mobile.jinja` | holds |
| ShippingPageSections | J | `templates/shipping_payment.jinja`; `components/shipping-payment/cities-dialog.jinja` | holds |
| PaymentAndBanks | J | `components/shipping-payment/payment-methods.jinja`, `bank-accounts.jinja` | holds |
| JsonIslandIsInert | J | `components/shipping-payment/shipping-table.jinja` (island) | holds |
| FaqTextEscaping | J | `templates/faqs.jinja` (`faq.question`) | **violation** |
| PageTitleEscaping | J | `templates/page.jinja`; `components/ui/breadcrumb.jinja` (`item.label\|safe`) | **violation** |
| ShippingTextEscaping | J | `components/shipping-payment/*.jinja` | **violation** |
| CitiesDialogRenders | B | `assets/js/shipping-payment.js:renderCities` | holds |
| CitiesDialogLifecycle | B | `assets/js/shipping-payment.js:openCitiesDialog`, `initCitiesDialog` | holds |
| CityTextEscaping | B | `assets/js/shipping-payment.js:renderCities` (tags) | holds |
| CountryTextEscaping | B | `assets/js/shipping-payment.js:renderCities` (headers) | **violation** |
| CopyButtonCopies | B | `assets/js/shipping-payment.js:initCopyButtons` | holds |
| CopyFeedbackRestores | B | `assets/js/shipping-payment.js:initCopyButtons` | **violation** |

Module -> property: `components/shipping-payment` -> ShippingRowsMatchData, ShippingPageSections, PaymentAndBanks,
JsonIslandIsInert, ShippingTextEscaping, and the dialog markup hooks in ShippingPageSections; `js/shipping-payment` ->
the six B properties; `templates/faqs` -> FaqAccordionShape, FaqTextEscaping; `templates/page` -> PageShape,
PageTitleEscaping; `templates/shipping_payment` -> ShippingPageSections, JsonIslandIsInert, ShippingTextEscaping.

## Mutation proof

`mutants/*.patch` are the breaks used to show `check.sh` can fail, applied only to a scratch copy:
`preview-off-by-one` (table previews 4 cities, never shows "+N more" at 4), `search-case-sensitive` (dialog search stops
ignoring case), `city-tags-innerhtml` (city tags via `innerHTML`). Each turns the named property into `CHANGED`.

## Not covered

Vitrin-side data (what the API returns, slug redirects), the platform `el-disclosure` toggle, server-side caching, real
clipboard permissions, RTL layout and visual fit (use `verify-content-pages` screenshots), and the English literals in
the dialog (noted in finding 3, not asserted).
