"""verify-blog journeys: the blog list page (templates/blogs.jinja), its filters and shared blog scripts,
and the missing-post path of templates/blog.jinja, against the live storefront as a guest.

Loaded by ../../verify-growth-theme/scripts/drive.py; run from the repo root:

    uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py blog-list

Store 1 (testing API) has blog categories but **no blog posts**, so no journey can show a card, a post, a
pagination bar or a share row. Those render paths are proven by formal-blog from fixture data.
"""

import datetime
import re
from urllib.parse import parse_qs, urlparse


# A theme-bundle console error is a blog defect; landbot/SDK noise is not ours.
def _theme_errors(page, sink):
    page.on(
        "console",
        lambda m: sink.append(f"{m.text} @ {m.location.get('url', '')}")
        if m.type == "error"
        and ("theme.js" in (m.location.get("url") or "") or "dist/" in (m.location.get("url") or ""))
        else None,
    )


_SNAPSHOT = """
(() => {
  const main = document.querySelector('main#main');
  const crumbs = Array.from(document.querySelectorAll('nav[aria-label] li, nav[aria-label] a, nav[aria-label] [aria-current]'))
    .map((n) => n.textContent.trim()).filter(Boolean);
  const pills = Array.from(main.querySelectorAll('a[href^="/blogs"]')).filter((a) => a.className.includes('rounded-lg') && a.className.includes('border'))
    .map((a) => ({ href: a.getAttribute('href'), text: a.textContent.trim(), active: a.className.includes('bg-foreground') }));
  const sticky = (() => { const h = document.querySelector('header'); return h && h.parentElement ? h.parentElement.offsetHeight : null; })();
  return {
    template: document.body.dataset.template,
    h1: Array.from(document.querySelectorAll('h1')).map((h) => h.textContent.trim()),
    crumbs: Array.from(new Set(crumbs)),
    pills,
    cards: main.querySelectorAll('article').length,
    empty: !!Array.from(main.querySelectorAll('h3')).find((h) => h.textContent.trim() === 'No posts found'),
    pagination: main.querySelectorAll('[data-slot="pagination"]').length,
    perPage: main.querySelectorAll('[data-blog-per-page]').length,
    chip: (() => { const c = Array.from(main.querySelectorAll('span')).find((s) => s.textContent.trim().startsWith('Results for')); return c ? c.parentElement.innerText.replace(/\\s+/g, ' ').trim() : null; })(),
    headerVar: getComputedStyle(document.documentElement).getPropertyValue('--header-h').trim(),
    stickyHeight: sticky,
  };
})()
"""


# ── blog-list ────────────────────────────────────────────────────────────────
def blog_list(page, base, out, checks):
    """/blogs for a store with categories and no posts: frame, breadcrumb, category pills, empty state, --header-h sync."""
    errors = []
    _theme_errors(page, errors)
    resp = page.goto(base + "/blogs", wait_until="load")
    page.wait_for_selector("main#main h1")
    page.wait_for_timeout(600)
    s = page.evaluate(_SNAPSHOT)
    checks["status"] = resp.status
    checks["snapshot"] = s
    page.screenshot(path=out / "1-blogs-desktop.png")

    # blog-scripts: --header-h tracks the sticky header height, also after a resize.
    checks["header_var_matches_desktop"] = s["headerVar"] == f"{s['stickyHeight']}px"
    page.set_viewport_size({"width": 390, "height": 800})
    page.wait_for_timeout(600)
    m = page.evaluate(_SNAPSHOT)
    checks["mobile_header_var"] = [m["headerVar"], m["stickyHeight"]]
    checks["header_var_matches_mobile"] = m["headerVar"] == f"{m['stickyHeight']}px"
    page.screenshot(path=out / "2-blogs-mobile.png")
    page.set_viewport_size({"width": 1280, "height": 900})

    # The "All categories" pill is the active one with no filter; every other pill points at ?category=<slug>.
    all_pill = s["pills"][0] if s["pills"] else {}
    others = s["pills"][1:]
    checks["theme_console_errors"] = errors
    return (
        resp.status == 200
        and s["template"] == "list_blogs"
        and s["h1"] == ["Blog"]
        and s["crumbs"][:2] == ["Home", "Blog"]
        and len(s["crumbs"]) == 2
        and all_pill == {"href": "/blogs", "text": "All categories", "active": True}
        and len(others) >= 1
        and all(re.fullmatch(r"/blogs\?category=[^&\"]+", p["href"]) and not p["active"] for p in others)
        and s["cards"] == 0
        and s["empty"] is True
        and s["pagination"] == 0
        and s["perPage"] == 0
        and s["chip"] is None
        and checks["header_var_matches_desktop"]
        and checks["header_var_matches_mobile"]
        and not errors
    )


# ── blog-filters ─────────────────────────────────────────────────────────────
def blog_filters(page, base, out, checks):
    """Category pill click, tag chip + its remove link, combined filters, out-of-range page, hostile query text."""
    errors = []
    _theme_errors(page, errors)
    page.goto(base + "/blogs", wait_until="load")
    page.wait_for_selector("main#main h1")
    first = page.evaluate(_SNAPSHOT)["pills"][1]
    cat_slug = parse_qs(urlparse(first["href"]).query)["category"][0]

    # 1. Click a category pill -> URL carries it, that pill is active, breadcrumb gains the category, still empty.
    page.locator(f'main a[href="{first["href"]}"]').first.click()
    page.wait_for_url(re.compile(r"/blogs\?category="))
    page.wait_for_selector("main#main h1")
    page.wait_for_timeout(400)
    cat = page.evaluate(_SNAPSHOT)
    checks["category"] = {"url": page.url, "pills": cat["pills"], "crumbs": cat["crumbs"], "empty": cat["empty"]}
    page.screenshot(path=out / "1-category.png")
    category_ok = (
        urlparse(page.url).query == f"category={cat_slug}"
        and [p["active"] for p in cat["pills"]] == [False] + [p["href"] == first["href"] for p in cat["pills"][1:]]
        and cat["crumbs"][:2] == ["Home", "Blog"]
        and len(cat["crumbs"]) == 3
        and cat["empty"]
    )

    # 2. Tag filter: chip shows the tag, "remove" returns to the list keeping the category.
    page.goto(base + f"/blogs?category={cat_slug}&tags=summer", wait_until="load")
    page.wait_for_selector("main#main h1")
    tag = page.evaluate(_SNAPSHOT)
    both_pill_hrefs = [p["href"] for p in tag["pills"]]
    checks["tag_with_category"] = {"chip": tag["chip"], "pill_hrefs": both_pill_hrefs}
    page.screenshot(path=out / "2-tag-and-category.png")
    tag_ok = (
        tag["chip"] is not None
        and "summer" in tag["chip"].lower()
        and both_pill_hrefs[0] == "/blogs?tags=summer"
        and both_pill_hrefs[1] == f"/blogs?category={cat_slug}&tags=summer"
    )
    page.locator('main a[aria-label="Remove tag filter"]').click()
    page.wait_for_url(re.compile(r"/blogs\?category="))
    checks["after_remove_tag"] = page.url
    remove_ok = urlparse(page.url).query == f"category={cat_slug}"

    # 3. Tag only: remove link goes to plain /blogs.
    page.goto(base + "/blogs?tags=summer", wait_until="load")
    page.wait_for_selector("main#main h1")
    page.locator('main a[aria-label="Remove tag filter"]').click()
    page.wait_for_url(re.compile(r"/blogs$"))
    checks["after_remove_tag_only"] = page.url
    remove_plain_ok = urlparse(page.url).path == "/blogs" and urlparse(page.url).query == ""

    # 4. Unknown category and a page beyond the data: the page still renders the frame + empty state.
    states = {}
    for label, q in (("unknown_category", "?category=no-such-category"), ("page_999", "?page=999&page_size=12")):
        r = page.goto(base + "/blogs" + q, wait_until="load")
        page.wait_for_selector("main#main h1")
        snap = page.evaluate(_SNAPSHOT)
        states[label] = {"status": r.status, "empty": snap["empty"], "pagination": snap["pagination"], "h1": snap["h1"]}
    checks["out_of_range"] = states
    range_ok = all(v["status"] == 200 and v["empty"] and v["pagination"] == 0 and v["h1"] == ["Blog"] for v in states.values())

    # 5. FINDING (recorded, not a failure here; formal-blog `blogs-query-escaping`): `.jinja` templates render
    # without autoescape in vitrin, so the `tags` query value is written into the page as markup. A harmless
    # <b id=...> proves injection; vitrin's input filter answers 403 to an inline event handler, which is the only
    # thing standing between this and script execution.
    page.goto(base + '/blogs?tags=%3Cb%20id%3D%22vb-probe%22%3Ex%3C%2Fb%3E', wait_until="load")
    page.wait_for_selector("main#main h1")
    probe = page.evaluate(
        "({ element: !!document.getElementById('vb-probe'), inChip: !!document.querySelector('main span #vb-probe, main span b#vb-probe') })"
    )
    quote = page.goto(base + "/blogs?tags=a%22b", wait_until="load")
    page.wait_for_selector("main#main h1")
    broken = page.evaluate(
        "Array.from(document.querySelectorAll('main a')).map((a) => a.getAttribute('href')).filter((h) => h && h.startsWith('/blogs'))"
    )
    handler = page.goto(base + "/blogs?tags=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E", wait_until="load")
    checks["finding_unescaped_tags_param"] = {
        "markup_injected_as_element": probe["element"],
        "quote_in_href": broken,
        "inline_handler_status": handler.status,
    }
    page.screenshot(path=out / "3-hostile-query.png")
    checks["theme_console_errors"] = errors

    checks.update(
        category_ok=category_ok, tag_ok=tag_ok, remove_ok=remove_ok, remove_plain_ok=remove_plain_ok, range_ok=range_ok
    )
    return category_ok and tag_ok and remove_ok and remove_plain_ok and range_ok and not errors


# ── blog-missing ─────────────────────────────────────────────────────────────
def blog_missing(page, base, out, checks):
    """/blogs/<slug> for a slug with no post: 404 inside the normal shell; a page-backed slug redirects, no blog template."""
    errors = []
    _theme_errors(page, errors)
    # templates/404_not_found.jinja sends the shopper home after 3 s. On a loaded machine that fires
    # before the checks below (and can abort the next goto), so freeze page timers first.
    page.clock.install()
    page.clock.pause_at(datetime.datetime.now() + datetime.timedelta(hours=1))
    r404 = page.goto(base + "/blogs/this-post-does-not-exist", wait_until="load")
    page.wait_for_selector("main#main")
    snap = page.evaluate(
        "({ template: document.body.dataset.template, h1: Array.from(document.querySelectorAll('h1')).map(h => h.textContent.trim()),"
        " article: document.querySelectorAll('main article').length, share: document.querySelectorAll('[data-copy-link]').length,"
        " debug: document.documentElement.outerHTML.includes('Blog Post Debug') })"
    )
    checks["missing"] = {"status": r404.status, **snap}
    page.screenshot(path=out / "1-missing-post.png")

    # `test` is a store page (blog id 476 in /api/v1/blogs has no posts); vitrin sends the blog URL to /pages/test.
    api = page.request.get(base + "/api/v1/blogs").json()
    checks["api_blogs"] = [{"id": b["id"], "slug": b["slug"]} for b in api]
    r = page.goto(base + "/blogs/" + api[0]["slug"], wait_until="load")
    checks["slug_redirect"] = {"final_url": page.url, "status": r.status, "template": page.evaluate("document.body.dataset.template")}
    page.screenshot(path=out / "2-slug-redirect.png")
    checks["theme_console_errors"] = errors

    return (
        r404.status == 404
        and snap["article"] == 0
        and snap["share"] == 0
        and snap["debug"] is False
        and urlparse(page.url).path == "/pages/" + api[0]["slug"]
        and r.status == 200
        and checks["slug_redirect"]["template"] != "blog_details"
        and not errors
    )


JOURNEYS = {
    "blog-list": blog_list,
    "blog-filters": blog_filters,
    "blog-missing": blog_missing,
}
