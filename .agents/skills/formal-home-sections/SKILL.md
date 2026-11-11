---
name: formal-home-sections
description: Formal checks for growth-theme home-sections (templates/home, sections/*): escaping of merchant text, countdown never negative, element-iff-data invariants, empty hrefs, single h1. Use after changing templates/home.jinja or any sections/*.jinja/*.schema.json, or to re-confirm the recorded findings.
---

# formal-home-sections

sync-commit: 2b1c67df1fb4f69637887f375d22099b90dafeb5

Bounded-exhaustive property checks over the REAL `templates/home.jinja` and `sections/*.jinja`.
Templates are rendered with plain Jinja2 (harness `../verify-home-sections/render.py`, with vitrin's
autoescape setting `select_autoescape()`, which is OFF for `.jinja`) over generated settings and
parsed with `html.parser`; the countdown's inline script runs in `node:vm` with a fake
clock. No randomness except one seeded generator (`seed 20261111`, printed by `countdown.mjs`).
Modules: `templates/home` and all 12 `sections/*` (jinja + schema).

## Properties

Each: promise, harm if broken, tool and why.

- **P1-escaping** (all 12 sections + `templates/home` h1). Promise: no merchant/customer text
  field can add an element, an `on*` attribute or a `<script>`. Harm: stored XSS on the store's
  front page. Tool: Jinja render + HTML parse; every text/textarea/url/image/color/video field,
  every list-item field, category/product names, store name and contact handles get 3 hostile
  payloads, one field at a time (exhaustive over fields).
- **P2-countdown-literal** (`sections/countdown`). Promise: `end_date` cannot break the
  `new Date("...")` string literal of the inline script. Harm: countdown dies (or script injection if
  escaping were removed). Tool: render + string check of the literal, because the escaping here is
  HTML-escaping inside a JS context, which does not cover `\` or newlines.
- **P3a-hero-flags** (`sections/hero`). Promise: h1 iff primary and heading non-blank, h2 iff not
  primary, one anchor iff button text non-blank, `fetchpriority=high` for order<=2 and `loading=lazy`
  after, never both. Harm: SEO heading structure, LCP regression. Tool: exhaustive 4x2x3x2x3x2
  grid of flags.
- **P3b-carousel-flags** (`sections/carousel`). Promise: slide count = data, dots only when
  `show_dots` and more than 1 slide, autoplay/fade attributes follow settings, one high-priority image
  at most (slide 0, order<=2). Harm: dots that cannot navigate, wrong autoplay. Tool: exhaustive
  n in 0..5 x flags x order.
- **P3c-gallery-count** (`sections/gallery`). Promise: `data-items-count` and tile count = data
  (0..8), no grid for zero items, overlay h3 iff title. Harm: CSS layouts keyed on the count
  (1..5) pick the wrong grid. Tool: exhaustive n in 0..8.
- **P3d-element-iff-data** (`sections/products`, `categories`, `benefits`, `partners`,
  `testimonials`, `video`, `call-to-action`). Promise: each element/section is rendered iff its data
  is present (cards = results, products section absent without results, stars = rating, 1 video
  element and overlay only without autoplay, blank CTA text renders nothing). Harm: empty headings,
  broken cards, wrong ratings. Tool: exhaustive small counts and flag grids.
- **P4-no-empty-href** (`sections/hero`, `call-to-action`, `countdown`, `carousel`, `gallery`).
  Promise: a rendered button never links to `href=""`. Harm: click reloads the page. Tool: render
  with the schema-default (empty) `button_url`.
- **P5-single-h1** (`templates/home` with sections). Promise: the home page has exactly one `<h1>`.
  Harm: SEO/accessibility heading structure. Tool: render home with hero/carousel combos.
- **P6-countdown-never-negative** (`sections/countdown`). Promise: displayed fields are 2+ digit
  numbers, h<24, m<60, s<60, equal `floor(distance/1000)`, never increase; at distance < 0 the
  section is hidden and the interval cleared, also with throttled/late ticks. Harm: "-1 day"
  or frozen sale banner. Tool: the real inline script in `node:vm`, 17 end offsets x 3 tick schedules.
- **P7-countdown-expired-at-load** (`sections/countdown`). Promise: a countdown that is already
  over hides like one that expires on the page (the script's own expiry branch hides the whole
  section). Harm: blank 480/700 px block. Tool: same vm harness.

## Current findings (recorded in `expected.txt`, `check.sh` exits 0 while they reproduce)

- **P1** (`finding 265`): vitrin renders `.jinja` with `select_autoescape()` (`sdk/jinja.py`), which
  does not cover `.jinja`, and the sections print merchant text with plain `{{ }}`. Every hostile
  payload in a section text/url/image field, a list-item field, a category/product name, the store
  name or a contact handle adds an element, an `on*` attribute or a `<script>` (265 field x payload
  violations; the first are printed). The content is merchant-authored (theme editor, catalog),
  so it runs on the merchant's own storefront. Evidence: `verify-home-sections` journeys `hero`,
  `call-to-action`, `categories`, `benefits`, `testimonials`, `video`, `logo-social` fail their
  escaping checks in a real browser (recorded in that skill's `KNOWN`).
- **P2** (`finding 4`): `end_date` is written into `new Date("...")` unescaped. `"` closes the
  literal and runs script (`countdown` journey: `garbage_cannot_inject_js`); `\` (or a value ending
  in `\`) or a newline is a JS SyntaxError and the countdown stays `00` forever.
- **P4**: `hero.jinja` and `call-to-action.jinja` use `settings.button_url | default('#')`; the schema
  default is `""`, which `default` does not replace, so the default button is `<a href="">`.
  Evidence: `verify-home-sections` `E_default_button_href_attr: ""`.
- **P5**: `templates/home.jinja` always emits `<h1 class="hidden">` and a primary `hero` (schema
  default `is_primary_hero: true`) emits another; two hero sections give three `<h1>`.
- **P7**: `countdown.jinja` hides only `.countdown-content` when `end_date` is past/empty/invalid at
  load, leaving the section's `min-h-[700px] md:min-h-[480px]` box (with the background image, if any).
  Evidence: `verify-home-sections` countdown `past_section_visible_height: 480`.

## Run

```bash
bash .agents/skills/formal-home-sections/check.sh            # ROOT defaults to this repo, ~2 s
ROOT=/path/to/copy bash .agents/skills/formal-home-sections/check.sh
```

Needs `uv` (Jinja2 fetched on demand) and `node`. Properties and recorded outcomes: `expected.txt`.

## Reading a result

- `OK <p> holds`: matches. `FINDING: <p> still reproduces`: known, unchanged.
- `CHANGED <p> (recorded: A, now: B)`, exit 1: either the code changed behavior (read the
  counterexample lines printed above, e.g. `hero: ...`) or the harness broke.
  Real bug: the counterexample names a template and settings. Harness error: a Python/Node traceback or
  `CHANGED harness-error`, or counterexamples that mention only the stubs (`image_url`, `url_for`).
  If the change is an intended fix of a finding, update `expected.txt` (and the Findings above).
- `NOTE drift` + `git diff --stat`: covered files changed since the sync-commit; re-read the properties.

## Bounds and assumptions

- Hostile payloads: 3 fixed strings (element, script close, attribute break); range/select/checkbox
  fields are not fuzzed (the editor constrains them), so CSS injection through `<style>` interpolation
  of range values is out of scope.
- The stubs match vitrin by reading `sdk/extensions.py` and `sdk/v2/filters.py` (`safeget`,
  `template_components`). With autoescape off, `image_url`'s output reaches the page raw, as in vitrin.
- `safeget` and `|default` semantics are Jinja's; the sandbox is `SandboxedEnvironment` like vitrin.
- Countdown: `Date` faked, `setInterval` driven by hand; the browser's timer clamping is not modeled
  beyond the "throttled" schedule (gaps up to 91 s).
- Product cards are minimal fixtures (`components/products/product-card.jinja` reads many fields).

## Coverage record

| Property | File:function |
|---|---|
| P1 | `props.py:p1_escaping` (+ `hostile_variants`, `injected`) over `sections/*.jinja`, `templates/home.jinja` |
| P2 | `props.py:p2_countdown_literal` over `sections/countdown.jinja` |
| P3a | `props.py:p3_hero` over `sections/hero.jinja` |
| P3b | `props.py:p3_carousel` over `sections/carousel.jinja` |
| P3c | `props.py:p3_gallery` over `sections/gallery.jinja` |
| P3d | `props.py:p3_data_present` over `sections/{products,categories,benefits,partners,testimonials,video,call-to-action}.jinja` |
| P4 | `props.py:p4_empty_href` over hero, call-to-action, countdown, carousel, gallery |
| P5 | `props.py:p5_single_h1` over `templates/home.jinja` + hero/carousel |
| P6 | `countdown.mjs` (main loop) over the script in `sections/countdown.jinja` |
| P7 | `countdown.mjs` (`p7`) over `sections/countdown.jinja` |
| Schemas (`sections/*.schema.json`) | defaults feed every property through `props.py:defaults`; schema validity of types/options is not checked |

Mutation proof (`mutants/*.patch`, applied to a scratch copy only; transcripts in
`<proof>/formal-home-sections/break.txt`):
`hero-heading-escaped` (adds `| e` to the hero h1) -> P1 CHANGED (finding 265 -> 262); `countdown-negative-window` -> P6 CHANGED;
`carousel-dots-single-slide` -> P3b CHANGED; `gallery-count-off-by-one` -> P3c CHANGED.
`pass.txt` / `pass-after.txt`: unmodified worktree, exit 0.

## Not covered

Carousel/embla JS behavior (see `verify-home-sections`); real `image_url`, video playback, the
Theme Editor; layout and CSS (grid geometry is checked in the verify journeys, not here); product
card internals; Arabic/English string content; `layout.jinja` and the `<title>` block of `templates/home`.
