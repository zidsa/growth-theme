"""Browser-side properties of formal-blog: the REAL <script> of components/blogs/blog-scripts.jinja
(rendered from the template, not copied) running in headless Chrome against a small fixture page.

    ROOT=<repo> uv run --no-project --with jinja2 --with playwright python -I props/browser.py

Prints `PROPERTY <id> <ok|finding> <signature>`. Pages are served by request interception: no server.
"""

import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import ROOT, make_env, report, report_finding  # noqa: E402

CHROME = os.environ.get(
    "CHROME",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" if sys.platform == "darwin" else "/usr/bin/google-chrome",
)
ORIGIN = "http://blog.test"
SCRIPT = make_env().get_template("components/blogs/blog-scripts.jinja").render()
SHARE = make_env().get_template("components/blogs/blog-share.jinja").render(share_title="t", share_url="https://s.test/blogs/p")


def page_html(body, lang="en", header=True, script=True):
    head = '<div id="sticky" style="position:sticky;top:0;height:99px"><header style="height:99px">h</header></div>' if header else ""
    return f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"></head><body>{head}{body}{SCRIPT if script else ""}</body></html>'


def open_page(browser, body, path="/blogs/p", lang="en", tz=None, **kw):
    context = browser.new_context(locale="en-US", timezone_id=tz or "UTC", permissions=["clipboard-read", "clipboard-write"] if kw.pop("clip", False) else [])
    page = context.new_page()
    seen = []

    def handler(route):
        url = route.request.url
        if not url.startswith(ORIGIN):
            return route.abort()
        seen.append(url)
        route.fulfill(status=200, content_type="text/html", body=page_html(body, lang=lang, **kw) if urlparse(url).path.startswith("/blogs") else "ok")

    context.route("**/*", handler)
    page.goto(ORIGIN + path)
    return context, page, seen


# ── blog-scripts-dates ───────────────────────────────────────────────────────
def prop_dates(browser):
    bad = []
    stamps = ["2026-04-13T10:00:00Z", "2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z", "2024-02-29T12:00:00+03:00", "2026-04-13T10:00:00.123456Z"]
    for lang in ("ar", "en", "fr", "ar-SA", "x-invalid-locale-code-that-is-far-too-long-to-be-valid"):
        body = "".join(f'<span class="d" data-blog-date="{s}">{s}</span>' for s in stamps) + '<span class="d" data-blog-date="not a date">not a date</span><span class="d" data-blog-date="">empty</span>'
        context, page, _ = open_page(browser, body, lang=lang)
        rows = page.evaluate(
            """(lang) => {
              let f; try { f = new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'short', year: 'numeric' }); } catch (e) { f = new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric' }); }
              return Array.from(document.querySelectorAll('.d')).map((e) => ({ raw: e.getAttribute('data-blog-date'), shown: e.textContent.trim(), expect: isNaN(new Date(e.getAttribute('data-blog-date'))) ? e.getAttribute('data-blog-date') : f.format(new Date(e.getAttribute('data-blog-date'))) }));
            }""",
            lang,
        )
        for r in rows:
            r["expect"] = r["expect"] or {"": "empty"}.get(r["raw"], r["raw"])
            if r["shown"] != r["expect"]:
                bad.append(f"lang {lang!r}: {r['raw']!r} shown as {r['shown']!r}, want {r['expect']!r}")
            if re.fullmatch(r"\d{4}-\d\d-\d\dT.*", r["shown"]):
                bad.append(f"lang {lang!r}: raw ISO string left on the page: {r['shown']!r}")
        context.close()
    return report("blog-scripts-dates", bad, "langs=5,values=7")


def prop_date_only(browser):
    """published_at as a bare date: shown on the same calendar day in every timezone? (scope: date-only strings)"""
    bad = []
    for tz in ("Pacific/Kiritimati", "UTC", "America/Los_Angeles", "Pacific/Pago_Pago"):
        context, page, _ = open_page(browser, '<span id="d" data-blog-date="2026-04-13">2026-04-13</span>', lang="en", tz=tz)
        shown = page.inner_text("#d")
        if "13" not in shown:
            bad.append(f"tz {tz}: 2026-04-13 shown as {shown!r}")
        context.close()
    return report_finding("blog-scripts-date-only", bad, "same-day-in-all-timezones" if not bad else "date-shifts-by-timezone")


# ── blog-scripts-header-h ────────────────────────────────────────────────────
def prop_header_h(browser):
    bad = []
    context, page, _ = open_page(browser, "<p>x</p>")
    for h in (99, 65, 1, 240, 99):
        page.evaluate(f"document.querySelector('header').style.height = '{h}px'; document.getElementById('sticky').style.height = '{h}px'")
        page.wait_for_function(f"getComputedStyle(document.documentElement).getPropertyValue('--header-h').trim() === '{h}px'", timeout=3000)
    for w in (1280, 390, 768, 1280):
        page.set_viewport_size({"width": w, "height": 800})
        page.evaluate("document.getElementById('sticky').style.height = (innerWidth < 500 ? 65 : 99) + 'px'")
        want = 65 if w < 500 else 99
        try:
            page.wait_for_function(f"getComputedStyle(document.documentElement).getPropertyValue('--header-h').trim() === '{want}px'", timeout=3000)
        except Exception:
            bad.append(f"viewport {w}: --header-h is {page.evaluate('getComputedStyle(document.documentElement).getPropertyValue(\"--header-h\")')!r}, want {want}px")
    context.close()
    # no header on the page (e.g. embedded preview): the script must not throw and must leave the rest working
    errors = []
    context = browser.new_context()
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    context.route("**/*", lambda r: r.fulfill(status=200, content_type="text/html", body=page_html('<span data-blog-date="2026-04-13T10:00:00Z">raw</span>', header=False)))
    page.goto(ORIGIN + "/blogs/p")
    if errors:
        bad.append(f"page without <header>: {errors}")
    if page.evaluate("document.querySelector('[data-blog-date]').textContent") == "raw":
        bad.append("page without <header>: dates not formatted (script stopped early)")
    context.close()
    return report("blog-scripts-header-h", bad, "heights=5,viewports=4,no-header=1")


# ── blog-scripts-per-page ────────────────────────────────────────────────────
def prop_per_page(browser):
    bad, cases = [], 0
    urls = [
        "/blogs",
        "/blogs?page=3",
        "/blogs?page=3&page_size=12",
        "/blogs?category=news&page=2&page_size=24",
        "/blogs?tags=summer&category=news",
        "/blogs?category=%D9%85%D9%82%D8%A7%D9%84%D8%A7%D8%AA&page=9",
        "/blogs?q=a%26b%3Dc&page=2",
        "/blogs?page=2#top",
    ]
    for url in urls:
        for value in ("12", "24", "48"):
            cases += 1
            body = f'<select data-blog-per-page><option value="12">12</option><option value="24">24</option><option value="48">48</option></select>'
            context, page, seen = open_page(browser, body, path=url)
            before = list(seen)
            page.select_option("[data-blog-per-page]", value)
            page.wait_for_timeout(250)
            new = [u for u in seen[len(before):] if u != ORIGIN + url]
            if not new:
                if value != "12" or "page_size=12" not in url:
                    bad.append(f"{url} -> {value}: no navigation")
                context.close()
                continue
            q_new = parse_qs(urlparse(new[-1]).query)
            q_old = parse_qs(urlparse(ORIGIN + url).query)
            want = {k: v for k, v in q_old.items() if k not in ("page", "page_size")}
            want.update({"page_size": [value], "page": ["1"]})
            if q_new != want:
                bad.append(f"{url} -> {value}: {new[-1]} has {q_new}, want {want}")
            if urlparse(new[-1]).path != "/blogs":
                bad.append(f"{url} -> {value}: path changed to {urlparse(new[-1]).path}")
            context.close()
    return report("blog-scripts-per-page", bad, f"cases={cases}")


# ── blog-scripts-copy-link ───────────────────────────────────────────────────
def prop_copy(browser):
    bad = []
    body = f'<div id="a">{SHARE}</div><div id="b">{SHARE}</div>'
    context, page, _ = open_page(browser, body, path="/blogs/p?utm=1")
    # Chrome's real clipboard needs focus + permission prompts; record writeText calls instead (the unit under test is the script).
    page.evaluate("window.__written = []; Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (t) => { __written.push(t); return Promise.resolve(); } } });")
    page.evaluate("window.__t = []; const st = window.setTimeout; window.setTimeout = (f, ms) => { window.__t.push([f, ms]); return 0; };")
    icons = page.evaluate("Array.from(document.querySelectorAll('[data-copy-link] svg')).map((s) => s.innerHTML)")
    page.click("#a [data-copy-link]")
    page.wait_for_function("window.__t.some((t) => t[1] === 2000)")
    copied = (page.evaluate("window.__written") or [None])[-1]
    state = page.evaluate("({ a: document.querySelector('#a [data-copy-link] svg').innerHTML.includes('polyline'), b: document.querySelector('#b [data-copy-link] svg').innerHTML.includes('polyline'), delay: (window.__t.find((t) => t[1] === 2000) || [0, 0])[1], href: location.href })")
    if copied != ORIGIN + "/blogs/p?utm=1":
        bad.append(f"copied {copied!r}")
    if not state["a"] or state["b"] or state["delay"] != 2000:
        bad.append(f"check-mark feedback wrong: {state}")
    page.evaluate("window.__t.find((t) => t[1] === 2000)[0]()")
    restored = page.evaluate("Array.from(document.querySelectorAll('[data-copy-link] svg')).map((s) => s.innerHTML)")
    if restored != icons:
        bad.append("icon not restored after the timer")
    # second share row works the same and independently
    page.click("#b [data-copy-link]")
    page.wait_for_function("window.__t.filter((t) => t[1] === 2000).length === 2")
    if not page.evaluate("document.querySelector('#b [data-copy-link] svg').innerHTML.includes('polyline')"):
        bad.append("second share row has no handler")
    # the click never navigates (href=javascript:void(0) + preventDefault)
    if page.evaluate("location.href") != ORIGIN + "/blogs/p?utm=1":
        bad.append("copy click navigated")
    context.close()

    # no Clipboard API (plain-http storefront preview, old webviews): execCommand fallback copies the URL and cleans up
    context = browser.new_context()
    page = context.new_page()
    context.route("**/*", lambda r: r.fulfill(status=200, content_type="text/html", body=page_html(body)))
    page.add_init_script("Object.defineProperty(navigator, 'clipboard', { value: undefined }); window.__cmd = []; document.execCommand = (c) => { __cmd.push([c, document.activeElement && document.activeElement.value]); return true; };")
    page.goto(ORIGIN + "/blogs/p?x=1")
    page.click("#a [data-copy-link]")
    fb = page.evaluate("({ cmd: __cmd, leftover: document.querySelectorAll('body > input').length })")
    if fb["cmd"] != [["copy", ORIGIN + "/blogs/p?x=1"]] or fb["leftover"] != 0:
        bad.append(f"fallback copy: {fb}")
    context.close()
    return report("blog-scripts-copy-link", bad, "rows=2,paths=clipboard+execCommand")


def prop_copy_denied(browser):
    """Clipboard permission denied: the shopper clicked 'copy link' and gets neither a copy nor an error."""
    context = browser.new_context()
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    context.route("**/*", lambda r: r.fulfill(status=200, content_type="text/html", body=page_html(f'<div id="a">{SHARE}</div>')))
    page.add_init_script("Object.defineProperty(navigator, 'clipboard', { value: { writeText: () => Promise.reject(new DOMException('denied', 'NotAllowedError')) } });")
    page.goto(ORIGIN + "/blogs/p")
    page.click("#a [data-copy-link]")
    page.wait_for_timeout(300)
    bad = []
    if errors:
        bad.append(f"unhandled promise rejection on denied clipboard: {errors[0][:80]}")
    context.close()
    return report_finding("blog-scripts-copy-denied", bad, "denied-clipboard-handled" if not bad else "unhandled-rejection-no-feedback")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        try:
            prop_dates(browser)
            prop_date_only(browser)
            prop_header_h(browser)
            prop_per_page(browser)
            prop_copy(browser)
            prop_copy_denied(browser)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
