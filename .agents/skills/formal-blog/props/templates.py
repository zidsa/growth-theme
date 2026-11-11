"""Jinja-side properties of formal-blog: templates/blogs.jinja, templates/blog.jinja and components/blogs/*.

    ROOT=<repo> uv run --no-project --with jinja2 python -I props/templates.py

Renders the REAL templates with plain Jinja2 (same shape as tests/repro) over generated data and prints
`PROPERTY <id> <ok|finding> <signature>`. Vitrin's `.jinja` environment has no autoescape, so neither does
this harness; `session.url.include_query_params` mimics starlette's URL method.
"""

import itertools
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, parse_qsl, quote, urlencode, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import ROOT, make_env, report, report_finding  # noqa: E402

ENV = make_env()


class Url:
    def __init__(self, url):
        self.url = url

    def include_query_params(self, **kw):
        parts = urlparse(self.url)
        q = dict(parse_qsl(parts.query))
        q.update({k: str(v) for k, v in kw.items()})
        return f"{parts.path}?{urlencode(q)}"


def session(query=None, path="/blogs"):
    query = query or {}
    qs = urlencode(query)
    return {
        "query_params": query,
        "url": Url(f"http://store.test{path}" + (f"?{qs}" if qs else "")),
        "lang": "en",
        "template": "list_blogs",
    }


STORE = {"name": "S", "permalink": "https://s.test/", "settings": {}}


def render(name, **ctx):
    ctx.setdefault("store", STORE)
    return ENV.get_template(name).render(**ctx)


def post(i, **over):
    p = {
        "id": i,
        "title": f"Post {i}",
        "slug": f"post-{i}",
        "snippet": f"Snippet {i}",
        "content": f"<p>Body {i}</p>",
        "published_at": "2026-04-13T10:00:00Z",
        "cover": {"image": {"medium": f"https://img.test/m{i}.jpg", "large": f"https://img.test/l{i}.jpg"}},
        "category": {"name": "News", "slug": "news"},
        "tags": [{"name": "Summer", "slug": "summer"}],
    }
    p.update(over)
    return p


def listing(count, page=1, page_size=12, n=None, query=None, categories=None, **extra):
    n = min(count, page_size) if n is None else n
    return render(
        "templates/blogs.jinja",
        posts={"results": [post(i) for i in range(n)], "count": count, "page": page, "page_size": page_size},
        categories={"results": categories if categories is not None else [{"name": "News", "slug": "news"}, {"name": "Tips", "slug": "tips"}]},
        session=session(query),
        **extra,
    )


def hrefs(html, prefix=None):
    out = re.findall(r'href="([^"]*)"', html)
    return [h for h in out if prefix is None or h.startswith(prefix)]


# ── blogs-filter-urls ────────────────────────────────────────────────────────
def blogs_filter_urls():
    bad, n = [], 0
    cats = [{"name": "News", "slug": "news"}, {"name": "Tips & Tricks", "slug": "tips"}, {"name": "ال", "slug": "مقالات"}]
    for cat, tag in itertools.product(["", "news", "tips", "مقالات", "no-such"], ["", "summer", "a-b_c"]):
        n += 1
        q = {k: v for k, v in (("category", cat), ("tags", tag)) if v}
        html = listing(0, n=0, query=q, categories=cats)
        pills = re.findall(r'<a\s+href="(/blogs[^"]*)"\s+class="([^"]*rounded-lg border px-5[^"]*)"\s*>\s*([^<]*?)\s*</a>', html)
        tag_href = lambda c: "/blogs?" + "&".join(x for x in ([f"category={c}"] if c else []) + ([f"tags={tag}"] if tag else []))
        want = [("/blogs" + (f"?tags={tag}" if tag else ""), "All categories")] + [(tag_href(c["slug"]), c["name"]) for c in cats]
        got = [(h, t) for h, _, t in pills]
        if got != want:
            bad.append(f"category={cat!r} tags={tag!r}: pills {got} != {want}")
            continue
        active = [t for h, c, t in pills if "bg-foreground" in c]
        known = {c["slug"]: c["name"] for c in cats}
        want_active = ["All categories"] if not cat else ([known[cat]] if cat in known else [])
        if active != want_active:
            bad.append(f"category={cat!r} tags={tag!r}: active pills {active} != {want_active}")
        remove = re.search(r'<a\s+href="([^"]*)"\s+aria-label="Remove tag filter"', html)
        if bool(tag) != bool(remove):
            bad.append(f"category={cat!r} tags={tag!r}: remove-tag link presence")
        elif remove:
            want_remove = "/blogs" + (f"?category={cat}" if cat else "")
            if remove.group(1) != want_remove:
                bad.append(f"category={cat!r} tags={tag!r}: remove link {remove.group(1)!r} != {want_remove!r}")
            # round trip: following the remove link leaves exactly the category filter
            if parse_qs(urlparse(remove.group(1)).query) != ({"category": [cat]} if cat else {}):
                bad.append(f"remove link query does not round-trip: {remove.group(1)!r}")
        crumbs = re.findall(r'<li class=" inline-flex[^>]*>\s*(?:<a[^>]*>|<span[^>]*>)\s*([^<]*?)\s*</', html)
        want_crumbs = ["Home", "Blog"] + ([known[cat]] if cat in known else [])
        if crumbs != want_crumbs:
            bad.append(f"category={cat!r}: breadcrumb {crumbs} != {want_crumbs}")
    return report("blogs-filter-urls", bad, f"combinations={n}")


# ── blogs-pagination ─────────────────────────────────────────────────────────
def pager(count, page, page_size=12, query=None):
    q = dict(query or {})
    q.setdefault("page", str(page))
    html = listing(count, page=page, page_size=page_size, query=q)
    desktop = html.split('class="hidden md:flex')[1].split("</ul>")[0] if 'class="hidden md:flex' in html else ""
    return html, desktop


def pagination_window():
    bad, cases = [], 0
    for total in range(1, 31):
        for current in range(1, total + 1):
            cases += 1
            html, desk = pager(total * 12, current)
            if total == 1:
                if "data-slot=\"pagination\"" in html:
                    bad.append(f"total 1: pagination rendered")
                continue
            nums = [(int(m.group(2)), m.group(1) == "true") for m in re.finditer(r'data-slot="pagination-link"\s+data-active="(true|false)"[^>]*>\s*(?:<span[^>]*>)?\s*(\d+)', desk.replace('data-active="true"\n      aria-current', 'data-active="true" aria-current'))]
            # pagination-link spans/anchors: collect (page, active) pairs in order
            items = re.findall(r'data-slot="pagination-link"\s*(?:data-active="(true|false)")?[^>]*>\s*(\d+)', desk)
            pages = [int(p) for _, p in items]
            tag = f"total {total} current {current}"
            actives = [int(p) for a, p in items if a == "true"]
            if actives != [current]:
                bad.append(f"{tag}: active links {actives}")
            if pages != sorted(set(pages)):
                bad.append(f"{tag}: page links not strictly ascending: {pages}")
            if not set(pages) <= set(range(1, total + 1)):
                bad.append(f"{tag}: link outside 1..{total}: {pages}")
            if total > 1:
                firsts = re.findall(r'aria-label="First page"[^>]*', desk)
                lasts = re.findall(r'aria-label="Last page"[^>]*', desk)
                if not firsts or not lasts:
                    bad.append(f"{tag}: first/last controls missing")
            gaps = []
            seq = []
            for m in re.finditer(r'data-slot="pagination-link"[^>]*>\s*(\d+)|data-slot="pagination-ellipsis"', desk):
                seq.append(int(m.group(1)) if m.group(1) else None)
            for a, b, c in zip(seq, seq[1:], seq[2:]):
                if b is None and a is not None and c is not None and c - a == 1:
                    gaps.append(f"ellipsis between {a} and {c} hides no page")
            bad.extend(f"{tag}: {g}" for g in gaps[:1])
    dead = sorted({int(re.search(r"current (\d+)", b).group(1)) for b in bad if "hides no page" in b})
    other = [b for b in bad if "hides no page" not in b]
    # Recorded finding: the dead ellipsis. Anything else is a new break.
    status = report_finding("pagination-window", bad, f"dead-ellipsis-at-current={','.join(map(str, dead))};other={len(other)}")
    return status


def pagination_links():
    """Every pager link keeps the other filters and sets page; prev/next/first/last disabled at the bounds."""
    bad, cases = [], 0
    for total, current in [(2, 1), (2, 2), (9, 1), (9, 5), (9, 9), (30, 15)]:
        for query in ({}, {"category": "news"}, {"tags": "summer"}, {"category": "news", "tags": "summer", "page_size": "24"}):
            cases += 1
            html, desk = pager(total * 12, current, query=query)
            anchors = re.findall(r'<a\s+href="([^"]*)"\s+data-slot="pagination[^"]*"', html)
            pages_seen = set()
            for h in anchors:
                if not h:
                    continue
                q = parse_qs(urlparse(h).query)
                for k, v in query.items():
                    if q.get(k) != [v]:
                        bad.append(f"total {total} current {current} {query}: link {h} lost {k}")
                if "page" not in q or not (1 <= int(q["page"][0]) <= total):
                    bad.append(f"total {total} current {current}: link {h} page out of range")
                pages_seen.add(int(q["page"][0]))
            at_start, at_end = current == 1, current == total
            for label, disabled in (("First page", at_start), ("Previous page", at_start), ("Next page", at_end), ("Last page", at_end)):
                m = re.search(rf'<[^>]*aria-label="{label}"[^>]*>', html)
                is_disabled = bool(m) and 'aria-disabled="true"' in m.group(0)
                if m and is_disabled != disabled:
                    bad.append(f"total {total} current {current}: {label} disabled={is_disabled}, want {disabled}")
    return report("pagination-links", bad, f"cases={cases}")


def pagination_total():
    """totalPages = ceil(count / page_size); nothing paginates when posts fit one page; the select shows page_size."""
    bad, cases = [], 0
    for count in (0, 1, 11, 12, 13, 24, 25, 47, 48, 49, 120):
        for size in (12, 24, 48, 5):
            cases += 1
            n = min(count, size)
            html = listing(count, 1, size, n=n)
            total = -(-count // size) if count else 1
            has_pager = 'data-slot="pagination"' in html
            if has_pager != (total > 1 and n > 0):
                bad.append(f"count {count} size {size}: pager rendered={has_pager}, total pages {total}")
            if has_pager:
                last = re.findall(r'aria-label="Last page"[^>]*href="[^"]*page=(\d+)', html) or re.findall(r'href="[^"]*page=(\d+)[^"]*"[^>]*aria-label="Last page"', html)
                if last and int(last[0]) != total:
                    bad.append(f"count {count} size {size}: last page link {last[0]} != {total}")
            if n > 0 and f"<el-selectedcontent" in html and not re.search(rf"<el-selectedcontent[^>]*>\s*{size}\s*</", html):
                bad.append(f"count {count} size {size}: per-page select does not show {size}")
    # per-page select options are fixed; a request with another page_size still renders
    return report("pagination-total", bad, f"cases={cases}")


# ── blog-card ────────────────────────────────────────────────────────────────
def card(**over):
    return render("components/blogs/blog-card.jinja", blog=post(1, **over))


def blog_card():
    bad, cases = [], 0
    tags = lambda k: [{"name": f"T{i}", "slug": f"t{i}"} for i in range(k)]
    for cat, ntags, cover, snippet, date in itertools.product([True, False], range(0, 8), [True, False], ["", "A <b>bold</b> <script>x</script> word", "x" * 400, None], [True, False]):
        cases += 1
        over = {
            "category": {"name": "Cat", "slug": "cat"} if cat else None,
            "tags": tags(ntags),
            "cover": {"image": {"medium": "https://img.test/m.jpg"}} if cover else None,
            "snippet": snippet,
            "published_at": "2026-04-13T10:00:00Z" if date else None,
        }
        html = card(**over)
        tag = f"cat={cat} tags={ntags} cover={cover} snippet={str(snippet)[:8]!r} date={date}"
        if len(re.findall(r"<article\b", html)) != 1:
            bad.append(f"{tag}: not exactly one <article>")
        if html.count('href="/blogs/post-1"') != 1:
            bad.append(f"{tag}: not exactly one link to the post")
        if ("<img" in html) != cover:
            bad.append(f"{tag}: <img> present={('<img' in html)}, cover={cover}")
        if ("data-blog-date=" in html) != date:
            bad.append(f"{tag}: date element present iff published_at")
        badges = (1 if cat else 0) + ntags
        shown = len(re.findall(r"border-foreground text-foreground inline-flex", html))
        more = re.findall(r"\+(\d+)\s*</span>", html)
        if shown != min(badges, 4):
            bad.append(f"{tag}: {shown} badges shown for {badges}")
        if (badges > 4) != bool(more) or (more and int(more[0]) != badges - 4):
            bad.append(f"{tag}: +N badge {more} for {badges} badges")
        desc = re.search(r'<p class="text-foreground text-sm line-clamp-2">\s*(.*?)\s*</p>', html, re.S)
        if bool(snippet) != bool(desc):
            bad.append(f"{tag}: description present iff snippet")
        elif desc:
            text = desc.group(1)
            if "<b>" in text or "<script" in text:
                bad.append(f"{tag}: markup survived striptags: {text!r}")
            if len(unescape(text)) > 160:
                bad.append(f"{tag}: description {len(text)} chars > 160")
        if "Read more" not in html:
            bad.append(f"{tag}: no read-more affordance")
    return report("blog-card", bad, f"cases={cases}")


# ── blog-post ────────────────────────────────────────────────────────────────
def post_page(**over):
    return render("templates/blog.jinja", post=post(1, **over), session=session(path="/blogs/post-1"))


def blog_post():
    bad, cases = [], 0
    for cover, cat, tagshape, date, products, related in itertools.product([True, False], [True, False], ["none", "slugged", "plain", "mixed"], [True, False], [True, False], [True, False]):
        cases += 1
        tg = {"none": [], "slugged": [{"name": "A", "slug": "a"}], "plain": [{"name": "B"}], "mixed": [{"name": "A", "slug": "a"}, {"name": "B"}]}[tagshape]
        over = {
            "cover": {"image": {"large": "https://img.test/l.jpg"}} if cover else None,
            "category": {"name": "Cat", "slug": "cat"} if cat else None,
            "tags": tg,
            "published_at": "2026-04-13T10:00:00Z" if date else None,
            "related_products": [{"id": "p"}, {"id": "q"}] if products else [],
            "related_posts": [post(2)] if related else [],
        }
        html = post_page(**over)
        tag = f"cover={cover} cat={cat} tags={tagshape} date={date} products={products} related={related}"
        for label, count, want in (
            ("<h1>", len(re.findall(r"<h1\b", html)), 1),
            ("<article>", len(re.findall(r"<article\b", html)) - (1 if related else 0), 1),
            ("share rows", len(re.findall(r'\n\s+data-copy-link\n', html)), 2),
            ("blog-scripts", html.count("data-blog-per-page") * 0 + html.count("Sync --header-h"), 1),
            ("cover img", html.count('fetchpriority="high"'), 1 if cover else 0),
            ("date spans (post + related cards)", html.count('data-blog-date="'), (1 if date else 0) + (1 if related else 0)),
            ("products carousel", html.count("blog-featured-products"), 1 if products else 0),
            ("related carousel", html.count("blog-related-posts") and 1, 1 if related else 0),
        ):
            if count != want:
                bad.append(f"{tag}: {label} x{count}, want {want}")
        slug_links = len(re.findall(r'href="/blogs\?tags=a"', html))
        if slug_links != (1 if "a" in [t.get("slug") for t in tg] else 0):
            bad.append(f"{tag}: tag link count {slug_links}")
        if re.search(r'<a[^>]*>\s*B\s*</a>', html):
            bad.append(f"{tag}: slugless tag rendered as a link")
        if cat:
            if html.count("/blogs?category=cat") != 2:
                bad.append(f"{tag}: category linked {html.count('/blogs?category=cat')}x (breadcrumb + badge expected)")
        crumbs = re.findall(r'aria-current="page"[^>]*>\s*([^<]*?)\s*</span>', html)
        if crumbs != ["Post 1"]:
            bad.append(f"{tag}: current breadcrumb {crumbs}")
    return report("blog-post", bad, f"cases={cases}")


def blog_post_debug_script():
    html = post_page()
    leftovers = []
    if "[Blog Post Debug]" in html:
        leftovers.append("templates/blog.jinja ships `console.log('[Blog Post Debug] Raw content:' ...)` on every post (its comment: \"remove before merging\")")
    # content with a closing script tag must not leave the debug script (tojson escapes `<`)
    hostile = post_page(content='</script><img src=x onerror=alert(1)> "q" \\ \u2028')
    script = hostile.split("<script>")[1].split("</script>")[0] if "<script>" in hostile else ""
    if "<img src=x" in script or "</script" in script.lower():
        leftovers.append("post content breaks out of the debug <script>")
    return report_finding("blog-post-debug-script", leftovers, "console-debug-shipped" if leftovers else "no-debug-script")


# ── blog-share ───────────────────────────────────────────────────────────────
def blog_share():
    bad, cases = [], 0
    alphabet = list(' &=?#%+/"\'<>\\\u0627\u0644é') + ["a", "Z", "0"]
    titles = ["".join(c) for r in (1, 2) for c in itertools.product(alphabet, repeat=r)] + ["مقال جديد & خصم 50%", "a b", "x=1&y=2", "50% off #1"]
    for title in titles:
        cases += 1
        html = render("components/blogs/blog-share.jinja", share_title=title, share_url="https://s.test/blogs/post-1")
        x = re.search(r'href="(https://twitter\.com/intent/tweet[^"]*)"', html)
        w = re.search(r'href="(https://api\.whatsapp\.com/send[^"]*)"', html)
        if not x or not w:
            bad.append(f"{title!r}: share link missing")
            continue
        xq = parse_qs(urlparse(unescape(x.group(1))).query)
        wq = parse_qs(urlparse(unescape(w.group(1))).query)
        if xq.get("text") != [title] or xq.get("url") != ["https://s.test/blogs/post-1"]:
            bad.append(f"{title!r}: tweet params {xq}")
        if wq.get("text") != [f"{title} https://s.test/blogs/post-1"]:
            bad.append(f"{title!r}: whatsapp text {wq.get('text')}")
    html = render("components/blogs/blog-share.jinja", share_title="t", share_url="https://s.test/blogs/post-1", copy_link_attr="data-x")
    if "data-x" not in html or "data-copy-link" in html:
        bad.append("copy_link_attr prop ignored")
    if html.count('rel="noopener noreferrer"') != 3 or html.count('target="_blank"') != 3:
        bad.append("external share links must all open with rel=noopener noreferrer")
    return report("blog-share", bad[:12], f"titles={cases}")


# ── blogs-carousel ───────────────────────────────────────────────────────────
def blogs_carousel():
    bad, cases = [], 0
    for n, title, more, cid in itertools.product([0, 1, 5], [None, "T"], [(None, None), ("/blogs", "All")], ["abc", None]):
        cases += 1
        ctx = {"posts": [post(i) for i in range(n)], "title": title, "more_url": more[0], "more_text": more[1], "carousel_id": cid}
        html = render("components/blogs/blogs-carousel.jinja", **ctx)
        tag = f"n={n} title={title} more={more[0]} id={cid}"
        if n == 0:
            if html.strip():
                bad.append(f"{tag}: rendered something for zero posts")
            continue
        for hook, want in (("data-carousel-prev", 1), ("data-carousel-next", 1), ("data-carousel-progress", 1), ("data-carousel-viewport", 1), ("data-carousel-slide", n)):
            got = len(re.findall(rf"(?<![\w-]){hook}(?![\w-])", html))
            if got != want:
                bad.append(f"{tag}: {hook} x{got}, want {want}")
        if len(re.findall(r"<article\b", html)) != n:
            bad.append(f"{tag}: {len(re.findall('<article', html))} cards for {n} posts")
        root = re.search(r'data-blogs-carousel="([^"]+)"', html).group(1)
        if cid and root != cid:
            bad.append(f"{tag}: carousel id {root!r}")
        if html.count(f'[data-blogs-carousel="{root}"]') < 4:
            bad.append(f"{tag}: scoped style missing for {root}")
        if more[0]:
            want_links = 2 if title else 1  # desktop link lives in the title row, mobile link in the controls row
            if html.count(f'href="{more[0]}"') != want_links:
                bad.append(f"{tag}: 'view all' link count {html.count(chr(34) + more[0] + chr(34))}, want {want_links}")
        elif 'href="/blogs"' in html:
            bad.append(f"{tag}: 'view all' link without more_url")
        if bool(title) != ("<h2" in html):
            bad.append(f"{tag}: heading present iff title")
    return report("blogs-carousel", bad, f"cases={cases}")


# ── escaping (findings) ──────────────────────────────────────────────────────
def blogs_query_escaping():
    """Shopper-controlled `tags` and `category` query values are written into the page as markup."""
    probe = '<b id="probe">x</b>'
    leaks = []
    html = listing(0, n=0, query={"tags": probe})
    if probe in html:
        leaks.append("?tags=<b id=probe> is emitted as an element inside the 'Results for' chip")
    html = listing(0, n=0, query={"tags": 'a"b'})
    if 'tags=a"b' in html:
        leaks.append('?tags=a"b is written into href="..." unescaped (breaks out of the attribute)')
    html = listing(0, n=0, query={"category": 'q"><i id=probe>'})
    if '<i id=probe>' in html:
        leaks.append('?category=q"><i id=probe> is emitted as an element')
    return report_finding("blogs-query-escaping", leaks, f"unescaped-query-values={len(leaks)}" if leaks else "escaped")


def blog_fields_escaping():
    """Merchant-entered title/category/tag names are written into the page as markup (platform renders .jinja unescaped)."""
    title = 'T <i id=probe>x</i>'
    leaks = []
    if title in card(title=title):
        leaks.append("blog title unescaped in the card")
    if title in post_page(title=title):
        leaks.append("blog title unescaped in the post page")
    if "<i id=probe>" in card(category={"name": "<i id=probe>", "slug": "c"}):
        leaks.append("category name unescaped in the card badge")
    if "<i id=probe>" in listing(0, n=0, categories=[{"name": "<i id=probe>", "slug": "c"}]):
        leaks.append("category name unescaped in the filter pill")
    return report_finding("blog-fields-escaping", leaks, f"unescaped-fields={len(leaks)}" if leaks else "escaped")


if __name__ == "__main__":
    blogs_filter_urls()
    pagination_total()
    pagination_window()
    pagination_links()
    blog_card()
    blog_post()
    blog_post_debug_script()
    blog_share()
    blogs_carousel()
    blogs_query_escaping()
    blog_fields_escaping()
