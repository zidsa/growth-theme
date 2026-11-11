---
name: verify-home-sections
description: Drive and verify the growth-theme home page and its 12 sections (benefits, call-to-action, carousel, categories, countdown, gallery, hero, logo-social, partners, products, testimonials, video) in headless Chrome against the real dist/theme.js. Use when a change touches templates/home.jinja or sections/*.jinja/*.schema.json, before calling it done or opening a PR.
---

# verify-home-sections

Group `home-sections` of zidsa/growth-theme: what a shopper sees on `/` and how each home
section renders and behaves (carousel/dots/autoplay, scroll buttons and progress bar, countdown
ticking, video play, gallery layouts, escaping of merchant text).

Covers: `templates/home` and `sections/{benefits,call-to-action,carousel,categories,countdown,
gallery,hero,logo-social,partners,products,testimonials,video}` (each `.jinja` + `.schema.json`).

## Why a render harness, not only the live store

`templates/home.jinja` has no `home.schema.json` and the template-settings DB is unreachable here,
so vitrin renders the home `<main>` with **only the hidden `<h1>` and zero sections** (journey
`home-sections-live-home` records this: 39 chars of `<main>`). The live store cannot show any
section, so every section journey:

1. renders the REAL `templates/home.jinja` + `sections/<x>.jinja` with plain Jinja2 (`render.py`,
   same approach as `tests/repro/`, with vitrin's autoescape setting: `select_autoescape()`, OFF for
   `.jinja`, so escaping is checked as production renders it), settings = the section schema's own defaults + fixture content
   for fields without a default (images, lists, categories);
2. serves that HTML at `<live origin>/__home-sections/<name>.html` through a Playwright route
   (nothing is written to the server) with the real `styles.css` and `dist/theme.js` URLs scraped
   from the live home page, so the page runs this checkout's built JS;
3. stubs only vitrin's platform pieces: `{% template_components %}` (copy of
   `sdk/extensions.py`: order = 1-based position, `sectionId`, `display:false` skipped), `image_url`
   (returns `/__img/w=..,q=..,f=../<url>`, answered by a generated SVG), `safeget`, `url_for`,
   `_()`, `vitrin:` includes. The products section uses the live `/api/v1/products` results.

The pages are not the live vitrin output: URL shaping of `image_url` and the layout shell
(`layout.jinja`, header, footer) are not exercised here; see `verify-layout`.

## Launch and doctor: see verify-growth-theme

The storefront (vitrin on 8995, assets on 8996) is started and stopped by
`verify-growth-theme/scripts/storefront.sh`; do not duplicate that. Check it, then drive from the
repo root:

```bash
bash .agents/skills/verify-growth-theme/scripts/storefront.sh doctor     # must end "doctor: healthy"
D="uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py"
$D --list | grep home-sections
$D home-sections-hero              # one journey at a time; exit 0 = passed or recorded FINDING
```

The harness runs `uv run --no-project --with jinja2 python -I render.py` itself (needs `uv`).
Evidence goes to `~/.cache/verify-growth-theme/evidence/<UTC>-home-sections-<name>/`.

## Journeys

| Journey | Shopper / harness does | Pass condition |
|---|---|---|
| `home-sections-live-home` | Opens `/` on the live store | 200; exactly one `h1.hidden` in `main` with text; `[section-id]` count in `main` is 0 exactly because `templates/home.schema.json` does not exist (records the zero-section fact) |
| `home-sections-hero` | Primary hero, non-primary 3rd hero, button/overlay/position/variant, markup in heading, default empty button url; desktop + mobile | h1 only when primary, h2 otherwise; `fetchpriority=high` order<=2 / `loading=lazy` order>2; overlay opacity = setting; desktop src `w=2220`, mobile `w=960`; min-height >= setting; blank heading/description/button render nothing; markup stays text; no theme.js error |
| `home-sections-carousel` | 3 slides with autoplay 1500 ms; waits for autoplay, clicks dots 2,0,1; 1 slide; dots off; no slides | 3 dots, one active at a time; autoplay moves off slide 0 unaided; each dot click activates that dot; LCP hints only on slide 0; single slide: no dots, autoplay attr empty; no slides: 0 slide elements |
| `home-sections-categories` | 12 categories (one without image, one with markup in name); clicks next until the end | hrefs `/categories/<id>/<slug>`; names escaped; alt = name; missing image falls back to `product-img.svg`; prev disabled at start, enabled after next; next disables at the end; progress bar grows to >99%; "View all" only with `display_more`; empty list keeps title |
| `home-sections-products` | Live `/api/v1/products` results rendered as carousel, grid, list, no-more, no data | 6 cards = API results; layout marker (`data-products-carousel` / `data-grid`); "see all" href = `products.url` else `/products`; no link when `display_more` off; section absent with no/empty results |
| `home-sections-testimonials` | 5 testimonials (ratings 5,3,0,4,5; markup in text; blank name); next/prev | filled stars = rating; `aria-label` "N out of 5 stars" except rating 0; markup not executed; blank name renders no h3; 3 slides per view on desktop; buttons labelled and enable/disable correctly |
| `home-sections-partners` | 14 partners (7 with url, one with mobile image) on desktop and 375 px | 14 slides, 7 links with the exact hrefs; alt = name; `data-carousel-autoscroll=0.5` and the track transform changes with no interaction; mobile image used (`w=160`); empty list renders no carousel |
| `home-sections-gallery` | 1..6 images, overlay content, order 1 vs 3, empty | `data-items-count` = n; computed geometry: n=3/5 first tile double width and height, n=1 spans, n=2 two columns, n=4 2x2, n=6 four columns; overlay only on tiles with title/button; button needs text and url; first image eager at order 1, all lazy at order 3; empty renders no grid |
| `home-sections-video` | Video with poster (Chrome `play()` stubbed to count calls); click the play button; autoplay variant; order 1..4 | click calls `play()` once and hides `.video-overlay`; poster `w=1280`; autoplay: attributes `autoplay muted controls`, no overlay; `preload` metadata for order<=2 else none; no url: no wrapper |
| `home-sections-countdown` | Future date (+2d 3h 4m 30s) read twice 2.3 s apart; expiring in 3 s sampled every 250 ms; past/empty/garbage date | displayed d/h/m/s equal remaining time within 2 s and tick down; two-digit padded; labels; button href; values never negative/NaN while expiring and the section hides at expiry; past/empty/garbage hide `.countdown-content`; garbage cannot run script |
| `home-sections-benefits` | 4 features (no image, markup title, blank title, no description) desktop + mobile | img/h3/p only when data present; title escaped; 4 columns desktop, 2 mobile; mobile image `w=96`; lazy only from the 3rd section; empty renders no grid |
| `home-sections-call-to-action` | Defaults, custom colors/image, blank text, markup in heading and color | default Arabic heading/button; colors applied (`rgb`); bg image alt = heading and `w=2220`; blank heading/description/button render nothing; heading is text; a quote in `background_color` cannot add an attribute |
| `home-sections-logo-social` | Store with all 7 social handles, none, one, hostile handle; desktop + mobile | 7 links with the exact URLs, `target=_blank rel=noopener`; contact title used, default "Follow us"; store logo for both breakpoints; no logo: name heading; min height 280/200 px; handle cannot break the attribute |

## Coverage

| Module | Driven by |
|---|---|
| `templates/home.jinja` | `home-sections-live-home` (live: hidden h1, zero sections); every section journey renders it as the page frame |
| `sections/hero` (.jinja, .schema.json) | `home-sections-hero`; defaults come from the schema file |
| `sections/carousel` | `home-sections-carousel` |
| `sections/categories` | `home-sections-categories` |
| `sections/products` | `home-sections-products` (cards come from `components/products/*`, owned by the product/search groups) |
| `sections/testimonials` | `home-sections-testimonials` |
| `sections/partners` | `home-sections-partners` |
| `sections/gallery` | `home-sections-gallery` |
| `sections/video` | `home-sections-video` (`play()` stubbed: headless Chrome has no media decode for the fixture) |
| `sections/countdown` | `home-sections-countdown` |
| `sections/benefits` | `home-sections-benefits` |
| `sections/call-to-action` | `home-sections-call-to-action` |
| `sections/logo-social` | `home-sections-logo-social` (its `logo_logo_*` settings are not in its schema; the journey records whether they are honoured) |

Not drivable here: the Theme Editor (merchant-side editing of the schema, drag/reorder); the
store's live section list (settings DB unreachable); real `image_url` output; real video playback.

## Recorded findings

Eight journeys replay open defects and are listed in `KNOWN` at the bottom of `journeys.py`: `drive.py` exits 0 for a journey listed in its skill's `KNOWN` table only while it fails exactly the recorded `failed_checks` (prints `FINDING`); any other failure, a crash, or the bug no longer reproducing exits 1 with `CHANGED`.
Seven of them (`hero`, `call-to-action`, `categories`, `benefits`, `testimonials`, `video`,
`logo-social`) are one bug: vitrin renders `.jinja` without autoescape and the sections print
merchant text with plain `{{ }}`, so markup in a heading, category name, store name or contact
handle becomes elements and attributes (`formal-home-sections` P1). `countdown`'s
`garbage_cannot_inject_js` is P2: `end_date` is written raw into `new Date("...")`.

## Recorded run

2026-11-11, theme `2b1c67d` (branch chore/verification_coverage, no product changes), vitrin
`dfd3386b`, `doctor: healthy`, Chrome headless ar-SA. All 13 journeys `passed: true`, one at a time.
Transcript `<proof>/verify-home-sections/run.txt`;
evidence dirs copied to `.../verify-home-sections/evidence/` (e.g. `20261111T130259Z-home-sections-hero`).

Observed facts recorded in `summary.json` (not failures; see `formal-home-sections` for the
properties): home with a primary hero has two `<h1>` (`page_h1_count_with_primary_hero: 2`);
the default hero/CTA button renders `href=""` (`E_default_button_href_attr: ""`); an expired
countdown at load hides only its content, the section keeps 480 px (`past_section_visible_height`).

## Evidence

Each journey writes `summary.json`, screenshots, the rendered page (`<name>.html`),
`network.log`, `console.log`. Keep every dir you cite. Evidence lives under `~/.cache` and
`~/proof`, never in this skill dir.

## Gotchas

- Run journeys sequentially; each spawns `uv run ... render.py` (needs network for `uv` cache only).
- `theme_errors` fails a journey on any `theme.js` console error or page error from theme.js;
  the chat-widget error on the live home is ignored on purpose (`chatbot.com`, not the theme).
- A route-fulfilled page is not loopback to Chrome, so CSS/JS from `:8996` are re-fetched through
  Playwright (`Session.__init__`); without it the page loads unstyled and theme.js never runs.
- Section ids are `<section>-<n>`; use `section-id`, not index, to address a section.
- `products` fixture data is the live store's first 6 products; their names/prices may change.
- If vitrin's `image_url` or `template_components` changes shape, update `render.py` first.
