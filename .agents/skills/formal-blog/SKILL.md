---
name: formal-blog
description: Formal property checks for growth-theme's blog group (templates/blogs.jinja, templates/blog.jinja, components/blogs/*). Generated-data Jinja renders plus the real blog-scripts.jinja script in headless Chrome; asserts the recorded outcome of each property, including six known defects. Use after changing any blog template or component, since store 1 has no posts to drive them live.
sync-commit: 2b1c67df1fb4f69637887f375d22099b90dafeb5
---

# formal-blog

sync-commit: `2b1c67df1fb4f69637887f375d22099b90dafeb5` (growth-theme, branch chore/verification_coverage).

Run: `bash .agents/skills/formal-blog/check.sh` (≈20 s). Exit 0 = every property matched
`props/expected.txt`; exit 1 prints `CHANGED <property>`. Needs `uv`, Google Chrome, network for the first
`uv run` to fetch `jinja2` and `playwright`. No repo dependency is added.

This is the main proof for the blog group: the testing store has categories but **no posts**, so
[verify-blog](../verify-blog/SKILL.md) can only reach the empty list and the 404. Everything that needs
posts is rendered here from generated data.

Tools: **Jinja** = plain Jinja2 over the real templates with no autoescape (vitrin renders `.jinja`
files unescaped), `layout.jinja` reduced to a frame, `products-carousel.jinja` stubbed (owned by another
group; only its call-site is checked), `session.url.include_query_params` mimicking starlette.
**Browser** = headless Chrome running the real `<script>` of `components/blogs/blog-scripts.jinja`
(rendered from the template, not copied) against fixture DOM. Chosen because the list/post templates
are pure functions of data, and the script only misbehaves in a DOM.

## Properties

| Property | Promise (plain) | Harm if broken | Tool, why |
|---|---|---|---|
| `blogs-filter-urls` | For every category/tag combination the pills keep the tag, the tag chip's remove link keeps the category, exactly the right pill is active and the breadcrumb gains the category only when it exists. | A filter click silently drops the other filter, or marks the wrong category active. | Jinja, 5 categories × 3 tags incl. Arabic slug and unknown slug. |
| `pagination-total` | The pager appears only when there is more than one page and posts; last page = ceil(count / page_size); the per-page select shows the page size. | Posts unreachable (floor) or a pager on an empty page. | Jinja, 11 counts × 4 page sizes. |
| `pagination-window` | The numbered pager is ascending, inside 1..N, marks only the current page active and never uses "…" to hide nothing. | A dead "…" confuses navigation. **Finding.** | Jinja, every (current, total) for total 1-30 (465 cases). |
| `pagination-links` | Every pager link keeps category/tag/page_size and points at an in-range page; First/Previous are disabled on page 1, Next/Last on the last page. | Paging loses the filter or leaves the shopper on a dead link. | Jinja, 6 positions × 4 filter sets. |
| `blog-card` | One `<article>`, one link to the post, an `<img>` iff there is a cover, a date iff `published_at`, at most 4 badges plus `+N`, a description iff there is a snippet, stripped of markup and ≤ 160 chars. | Broken card layout, markup leaking from a snippet. | Jinja, 256 combinations of category/tags/cover/snippet/date. |
| `blog-post` | One `<h1>`, one `<article>`, exactly two share rows, the cover with `fetchpriority` iff present, the date iff present, featured products and related posts iff given, tags link only when they have a slug, category linked from breadcrumb and badge. | Duplicated or missing blocks on a post. | Jinja, 128 combinations. |
| `blog-post-debug-script` | The post page ships no debug script. | Raw post content is dumped to every visitor's console. **Finding.** | Jinja, search of the rendered page; plus hostile content cannot break out of the `<script>`. |
| `blog-share` | The X and WhatsApp links carry the exact title and URL for any title text (`& = ? # % + / " ' < >`, Arabic, accents); the optional copy-link attribute is honoured; external links all have `rel="noopener noreferrer"`. | A shared post link with a truncated or garbled title. | Jinja, 384 generated titles (all 1-2 character strings over a 18-char alphabet). |
| `blogs-carousel` | Zero posts render nothing; otherwise one prev, one next, one progress, one viewport, one slide and one card per post, "view all" present iff given, scoped styles for the carousel id. | A related-posts carousel with dead controls. | Jinja, 24 combinations. |
| `blogs-query-escaping` | Shopper-controlled `tags` / `category` query values are text, not markup, and cannot leave an attribute. | Reflected HTML injection on a link a shopper can be sent. **Finding.** | Jinja with hostile values. |
| `blog-fields-escaping` | Merchant-entered blog title and category names are rendered as text. | Stored markup in titles/categories executes for every visitor. **Finding.** | Jinja with hostile values. |
| `blog-scripts-dates` | Every `[data-blog-date]` is replaced by the date in the page's language, bad dates and invalid locales leave readable text. | Raw ISO timestamps on the page. | Browser, 5 locales × 7 values. |
| `blog-scripts-date-only` | A date-only value (`2026-04-13`) shows the same day in every timezone. | The day shifts for shoppers west of UTC. **Finding.** | Browser, 4 timezones. |
| `blog-scripts-header-h` | `--header-h` tracks the sticky header height on load, on header resize and on viewport changes, and a page without a header does not stop the script. | Sticky category pills sit under/over the header. | Browser. |
| `blog-scripts-per-page` | Changing the per-page select navigates to the same path with the chosen `page_size`, `page=1` and every other parameter intact. | Filters lost, or the shopper lands beyond the new last page. | Browser, 8 URLs × 3 sizes. |
| `blog-scripts-copy-link` | Copy-link writes the current URL, shows a check mark on only the clicked row for 2000 ms then restores the icon, never navigates, and falls back to `execCommand('copy')` (cleaning up) without the Clipboard API. | Nothing copied, or a stuck icon. | Browser, both share rows. |
| `blog-scripts-copy-denied` | A denied or failing clipboard write does not leave an unhandled rejection. | Silent failure on browsers that block the clipboard. **Finding.** | Browser. |

## Current findings

All asserted by `check.sh`: exit 0 while the counterexample still reproduces (a loud `FINDING:` line),
exit 1 with `CHANGED <property>` the moment any of them flips.

- **`pagination-window`**: for 6+ pages with the current page 4, the desktop pager renders `1 … 2`: the leading "…" (blog-pagination.jinja:95-101) is shown after page 1 although the window already starts at page 2, so it hides nothing.
- **`blog-post-debug-script`**: `templates/blog.jinja:71-81` has a `<script>` that does `console.log('[Blog Post Debug] Raw content:', <post content>)` (and two more debug logs); its comment says `remove before merging`.
- **`blogs-query-escaping`**: `templates/blogs.jinja` writes `active_tag_name` (the raw `tags` query value) into the chip and `tags` / `category` into `href` attributes without `| e`; `?tags=<b id=x>` becomes an element and `?tags=a"b` closes the attribute. vitrin refuses inline event handlers in the query with 403 (seen live in verify-blog), which is the only thing between this and script execution.
- **`blog-fields-escaping`**: blog `title` (card, post page) and category `name` (card badge, filter pill) are printed raw; the platform renders `.jinja` without autoescape and the theme never applies `| e`.
- **`blog-scripts-date-only`**: `new Date('2026-04-13')` is parsed as UTC midnight and formatted in local time, so shoppers in the Americas see the 12th. ISO timestamps with a time and zone (what the API sends) are fine; this only affects date-only values.
- **`blog-scripts-copy-denied`**: the copy handler calls `navigator.clipboard.writeText(...).then(...)` without a `.catch` or fallback on rejection; a denied write is an unhandled rejection and the shopper sees no feedback.

## How to run

```bash
bash .agents/skills/formal-blog/check.sh                      # ROOT defaults to this repo
ROOT=/path/to/other/checkout bash .agents/skills/formal-blog/check.sh
```

Halves, run from `props/`: `ROOT=… uv run --no-project --with jinja2 python -I templates.py` and
`ROOT=… uv run --no-project --with jinja2 --with playwright python -I browser.py`. Each prints
`PROPERTY <id> <ok|finding> <signature>` plus the first counterexamples.

## Reading a result

- `CHANGED <p>: got 'ok …', recorded 'finding …'`: a recorded defect disappeared. If the product code was fixed on purpose, update `props/expected.txt` for that line and move the finding out of this file.
- `CHANGED <p>: got 'finding …', recorded 'ok …'`: a real regression; re-run the half that owns the property to read the counterexample.
- `HARNESS …` lines or `property did not run`: harness error (missing Chrome, Playwright not fetchable, renamed template path). Not a product bug.
- `NOTE drift` + `git diff --stat`: a covered file changed since the sync commit; the properties still ran against the new code.

## Bounds and assumptions

- Posts are generated with the fields the templates read (`title`, `slug`, `snippet`, `content`, `published_at`, `cover.image.{medium,large}`, `category`, `tags`, `related_products`, `related_posts`); the real API shape for posts is not available on store 1 and is not modelled beyond that.
- Pagination: totals 1-30, current 1..total, page sizes 12/24/48/5; the "…" rule is checked as "an ellipsis never sits between two consecutive page numbers".
- Titles for `blog-share`: all strings up to 2 characters over `' &=?#%+/"\'<>\\ا ل é a Z 0'` plus four hand-written Arabic/percent cases; longer titles are not generated.
- `layout.jinja` is replaced by a frame; header/footer behavior belongs to formal-layout. `products-carousel.jinja` is stubbed.
- Timezones for `blog-scripts-date-only`: Pacific/Kiritimati, UTC, America/Los_Angeles, Pacific/Pago_Pago. Clipboard is stubbed (Chrome's real clipboard needs user-gesture permissions).

## Coverage record

| Property | File:function |
|---|---|
| `blogs-filter-urls` | `props/templates.py:blogs_filter_urls` → `templates/blogs.jinja` (tag_qs / category_qs, pills, chip, breadcrumb), `components/ui/breadcrumb.jinja` |
| `pagination-total`, `pagination-window`, `pagination-links` | `props/templates.py:pagination_total`, `pagination_window`, `pagination_links` → `components/blogs/blog-pagination.jinja`, `components/ui/pagination.jinja`, `templates/blogs.jinja` (totalPages/currentPage) |
| `blog-card` | `props/templates.py:blog_card` → `components/blogs/blog-card.jinja` |
| `blog-post`, `blog-post-debug-script` | `props/templates.py:blog_post`, `blog_post_debug_script` → `templates/blog.jinja` |
| `blog-share` | `props/templates.py:blog_share` → `components/blogs/blog-share.jinja` |
| `blogs-carousel` | `props/templates.py:blogs_carousel` → `components/blogs/blogs-carousel.jinja` |
| `blogs-query-escaping`, `blog-fields-escaping` | `props/templates.py:blogs_query_escaping`, `blog_fields_escaping` → `templates/blogs.jinja`, `blog-card.jinja`, `templates/blog.jinja` |
| `blog-scripts-dates`, `blog-scripts-date-only`, `blog-scripts-header-h`, `blog-scripts-per-page`, `blog-scripts-copy-link`, `blog-scripts-copy-denied` | `props/browser.py:prop_dates`, `prop_date_only`, `prop_header_h`, `prop_per_page`, `prop_copy`, `prop_copy_denied` → `components/blogs/blog-scripts.jinja` |

Mutations proven caught (copy of the repo, never the working tree): `mutants/total-pages-floor.patch`
(`round(0,'ceil')`→`'floor'`) → `pagination-total` flips; `mutants/share-no-urlencode.patch` (drops
`| urlencode` from the X share link) → `blog-share` flips. Transcripts:
`<proof>/formal-blog/{pass,break,pass-after}.txt`.

## What is not covered

- The real post API shape and any server-side filtering/pagination (no posts on store 1, and vitrin has no public endpoint for them).
- Visual layout, images and Tailwind classes; the Facebook share link target beyond rel/target attributes.
- The `{% block title %}` / SEO meta of the blog pages (owned by layout and vitrin).
- A product carousel inside a post (stubbed here; `products-carousel.jinja` belongs to other groups).
