---
name: verify-blog
description: Drive growth-theme's blog surface (templates/blogs.jinja list page and filters, the missing-post path of templates/blog.jinja, components/blogs/*) on the live local storefront as a guest and keep evidence. Use after changing any blog template or component, and before opening a growth-theme PR that touches them. Store 1 has no blog posts, so card, post, pagination and share rendering are proven by formal-blog instead.
---

# verify-blog

Runnable verification for the **blog** group of `zidsa/growth-theme`. Launch, doctor, evidence and
cleanup are in [verify-growth-theme](../verify-growth-theme/SKILL.md); this skill only adds journeys.

## What the group covers

| Module | What it renders |
|---|---|
| `templates/blogs.jinja` | `/blogs`: breadcrumb, title, category pills, tag chip with remove link, card grid or empty state, pagination include, blog scripts include |
| `templates/blog.jinja` | `/blogs/<slug>` post page: cover, title, date, two share rows, content, category/tag links, featured products, related posts |
| `components/blogs/blog-card.jinja` | one post card (image or placeholder, snippet, up to 4 badges + `+N`, date, read more) |
| `components/blogs/blog-pagination.jinja` | per-page select (12/24/48) and the numbered pager |
| `components/blogs/blog-share.jinja` | copy-link, X, WhatsApp, Facebook links |
| `components/blogs/blog-scripts.jinja` | inline script: locale date formatting, `--header-h` sync, per-page navigation, copy-link feedback |
| `components/blogs/blogs-carousel.jinja` | related-posts carousel used by the post page |

**Store 1 (testing API) has blog categories (`/blogs?category=posts`) but no blog posts** and one
blog that is really a store page (`/api/v1/blogs` → id 476, slug `test`). Every journey below
therefore drives the empty-list path; everything that needs a post is covered by formal-blog.

## Launch and doctor: see verify-growth-theme

Use the already-running instance (port 8995) or `storefront.sh up` as described there; `doctor` must
end `doctor: healthy`. Drive from the repo root, one journey at a time:

```bash
uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py blog-list
uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py blog-filters
uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py blog-missing
```

## Journeys

| Journey | What the shopper does | Pass condition |
|---|---|---|
| `blog-list` | Opens `/blogs` (desktop, then a 390px viewport) | 200, `data-template=list_blogs`, one `<h1>` "Blog", breadcrumb Home › Blog, active "All categories" pill plus a `?category=<slug>` pill per category, "No posts found" state, no cards, no pager, no per-page select, no tag chip; `--header-h` equals the sticky header height at both sizes; no theme.js console error. |
| `blog-filters` | Clicks a category pill; opens `?category=…&tags=summer`, clicks the chip's remove link (with and without category); opens an unknown category and page 999; probes hostile `tags` values | Category click puts `?category=<slug>` in the URL, activates that pill and adds the category to the breadcrumb; pill hrefs keep `tags`; chip shows the tag and its remove link keeps the category (or goes to bare `/blogs`); unknown category / out-of-range page still render the frame and empty state with 200. The unescaped `tags` value is recorded in `checks.finding_unescaped_tags_param`, not asserted. |
| `blog-missing` | Opens `/blogs/this-post-does-not-exist` and the slug of the store's only blog | Unknown slug: 404 inside the normal shell (`404_not_found`), no article, no share row, no debug script; the page-backed slug redirects to `/pages/test` (200, template `pages`). |

## Coverage

| Module | Driven by | Notes |
|---|---|---|
| `templates/blogs.jinja` | `blog-list`, `blog-filters` (empty-state paths); formal-blog `blogs-filter-urls`, `pagination-total` | Filled grid not drivable live: no posts on store 1. |
| `templates/blog.jinja` | `blog-missing` (404 only); formal-blog `blog-post`, `blog-post-debug-script` | **Cannot be driven live**: no blog post exists to open. The post template is rendered by formal-blog over generated posts. |
| `components/blogs/blog-card.jinja` | formal-blog `blog-card` | **Cannot be driven live**: needs at least one post. |
| `components/blogs/blog-pagination.jinja` | formal-blog `pagination-window`, `pagination-links`, `pagination-total` | **Cannot be driven live**: the template renders nothing unless the list has posts. |
| `components/blogs/blog-share.jinja` | formal-blog `blog-share` | **Cannot be driven live**: only the post page includes it. |
| `components/blogs/blog-scripts.jinja` | `blog-list` (`--header-h`); formal-blog `blog-scripts-*` | Dates, per-page navigation and copy-link need post/card DOM; formal-blog loads the real script from the rendered template. |
| `components/blogs/blogs-carousel.jinja` | formal-blog `blogs-carousel` | **Cannot be driven live**: only the post page's related-posts block includes it. |

## Recorded run

2026-11-11, theme `2b1c67d` (`2b1c67df1fb4f69637887f375d22099b90dafeb5`), vitrin `dfd3386b`, store 1 on
`testing-api.zid.sa`, headless Chrome ar-SA 1280x900. `doctor: healthy`.

| Journey | Result | Evidence |
|---|---|---|
| `blog-list` | passed | `<proof>/verify-blog/20261111T131703Z-blog-list` |
| `blog-filters` | passed | `.../20261111T131710Z-blog-filters` |
| `blog-missing` | passed | `.../20261111T131734Z-blog-missing` |

## Evidence

drive.py writes `summary.json` (every value in `checks`), screenshots, `network.log` and `console.log`
under `~/.cache/verify-growth-theme/evidence/<UTC stamp>-<journey>/`. Keep copies outside this skill dir.
The full drive.py stdout of the recorded run is `<proof>/verify-blog/run.txt`.

## Gotchas

- The page strings are English ("Blog", "No posts found") even though the shell is ar-SA RTL; the store's category names are Arabic. Journeys assert the theme's msgids.
- `GET /blogs/<slug>` for a slug that is a store page returns 301 → `/pages/<slug>`; there is no `/api/v1` endpoint for blog posts, so post data cannot be read back.
- `?tags=` with an inline event handler (`onerror=...`) is refused by vitrin with 403 before the theme renders; markup without handlers is rendered unescaped (recorded finding, formal-blog `blogs-query-escaping`).
- Never `networkidle`: the chat widget polls.
- If a store with posts becomes available, add journeys for card grid, pagination and the post page rather than relaxing formal-blog.
