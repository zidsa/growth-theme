"""verify-home-sections journeys: templates/home and the 12 sections/* (jinja + schema).

Loaded by ../verify-growth-theme/scripts/drive.py; run from the repo root:

    uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py home-sections-hero

Why most journeys use a render harness and not the live store: `templates/home.jinja` has no
`home.schema.json`, so with the template-settings DB unreachable vitrin renders `<main>` with only
the hidden <h1> and ZERO sections (journey `home-sections-live-home` records that). Every section
journey therefore renders the REAL `templates/home.jinja` + `sections/<x>.jinja` with plain Jinja2
(render.py, same approach as tests/repro/), serves the page from the live origin
(`/__home-sections/<name>.html`, fulfilled by a Playwright route, nothing is written to the
server) and loads the REAL `dist/theme.js` + `styles.css` URLs scraped from the live home page.
Settings = the section schema's own defaults + fixture content for the fields that have no default
(images, lists, products). Products come from the live `/api/v1/products`.
"""

import json
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = "/__home-sections/"


# ── plumbing ─────────────────────────────────────────────────────────────────
def defaults(section):
    """Schema defaults of sections/<section>.schema.json: {id: default} for settings that have one."""
    schema = json.loads((ROOT / "sections" / f"{section}.schema.json").read_text())
    return {s["id"]: s["default"] for s in schema["settings"] if "default" in s}


def comp(section, order_slot=None, display=True, **settings):
    return {
        "template": f"sections/{section}.jinja",
        "settings": {**defaults(section), **settings},
        "section_id": f"{section}-{order_slot or 1}",
        "display": display,
    }


class Session:
    """One journey's browser plumbing: scraped live shell, page routes, theme error capture."""

    def __init__(self, page, base, out):
        self.page, self.base, self.out = page, base, out
        self.pages, self.theme_errors, self.failures = {}, [], []
        live = page.request.get(base + "/").text()
        self.css = re.search(r'href="([^"]*styles\.css[^"]*)"', live).group(1)
        self.js = re.search(r'src="([^"]*dist/theme\.js[^"]*)"', live).group(1)
        root = re.search(r"<style>\s*:root \{.*?\}\s*</style>", live, re.S)
        self.root_style = root.group(0) if root else ""
        page.route(re.compile(re.escape(PREFIX)), self._serve_page)
        page.route(re.compile(r"/__img/|/__asset/|/__media/"), self._serve_media)
        # A route-fulfilled page is not treated as loopback by Chrome, so the sibling asset host
        # (same bytes the live page loads) is fetched through Playwright and fulfilled back.
        page.route(re.compile(r"^https?://[^/]+:\d+/[0-9a-f]{8}/(styles\.css|dist/)"), lambda route: route.fulfill(response=route.fetch()))
        page.on("pageerror", lambda e: self.theme_errors.append(f"pageerror: {e}") if "theme.js" in (e.stack or "") else None)
        page.on(
            "console",
            lambda m: self.theme_errors.append(f"{m.text} @ {m.location.get('url', '')}")
            if m.type == "error" and "theme.js" in (m.location.get("url") or "")
            else None,
        )

    def _serve_page(self, route):
        name = route.request.url.split(PREFIX)[1].split("?")[0].removesuffix(".html")
        if name not in self.pages:  # e.g. an injected <img src=x> resolving next to the page
            route.fulfill(status=404, body="")
            return
        route.fulfill(status=200, content_type="text/html; charset=utf-8", body=self.pages[name])

    def _serve_media(self, route):
        url = route.request.url
        if "/__asset/" in url:
            f = ROOT / "assets" / url.split("/__asset/")[1].split("?")[0]
            if f.is_file():
                return route.fulfill(status=200, content_type="image/svg+xml", body=f.read_bytes())
        if "/__media/" in url:
            return route.fulfill(status=200, content_type="video/mp4", body=b"")
        m = re.search(r"w=(\d+)", url)
        w = int(m.group(1)) if m else 100
        label = url.rsplit("/", 1)[-1][:24]
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{int(w * 0.75)}">'
            f'<rect width="100%" height="100%" fill="#8aa"/><text x="8" y="20" font-size="14">{label}</text></svg>'
        )
        route.fulfill(status=200, content_type="image/svg+xml", body=svg)

    def render(self, name, components, store=None, lang="ar", direction="rtl"):
        spec = {
            "components": components,
            "store": store or {"name": "Fixture Store", "settings": {}},
            "lang": lang,
            "dir": direction,
            "head_extra": f'{self.root_style}<link rel="stylesheet" href="{self.css}">',
            "body_extra": f'<script src="{self.js}"></script>',
        }
        res = subprocess.run(
            ["uv", "run", "--no-project", "--with", "jinja2", "python", "-I", str(HERE / "render.py")],
            input=json.dumps(spec),
            capture_output=True,
            text=True,
            cwd=ROOT,
            env={**__import__("os").environ, "ROOT": str(ROOT)},
        )
        if res.returncode:
            raise RuntimeError("render failed: " + res.stderr[-800:])
        self.pages[name] = res.stdout
        (self.out / f"{name}.html").write_text(res.stdout)
        return res.stdout

    def open(self, name, components, wait=600, **kw):
        self.render(name, components, **kw)
        self.page.goto(f"{self.base}{PREFIX}{name}.html", wait_until="load")
        self.page.wait_for_timeout(wait)

    def shot(self, name, full=True):
        self.page.screenshot(path=self.out / f"{name}.png", full_page=full)

    def check(self, checks, key, value, cond):
        checks[key] = value
        if not cond:
            self.failures.append(key)

    def verdict(self, checks):
        checks["theme_errors"] = self.theme_errors
        checks["failed_checks"] = self.failures
        return not self.failures and not self.theme_errors


def js(page, expr):
    return page.evaluate(expr)


def desktop(page):
    page.set_viewport_size({"width": 1280, "height": 900})


def mobile(page):
    page.set_viewport_size({"width": 375, "height": 800})


def img(name):
    return f"fx/{name}.png"


# ── live home ────────────────────────────────────────────────────────────────
def live_home(page, base, out, checks):
    """The real storefront home: document frame from templates/home.jinja, and what it shows as sections."""
    s = Session(page, base, out)
    resp = page.goto(base + "/", wait_until="load")
    page.wait_for_selector("main#main", state="attached")
    page.wait_for_timeout(800)
    page.screenshot(path=out / "home.png", full_page=True)
    s.check(checks, "status", resp.status, resp.status == 200)
    h1 = page.locator("main h1")
    s.check(checks, "h1_in_main", h1.count(), h1.count() == 1)
    s.check(checks, "h1_hidden_class", h1.first.get_attribute("class"), h1.first.get_attribute("class") == "hidden")
    api = page.request.get(base + "/api/v1/store")  # store name the h1 falls back to
    checks["store_api_status"] = api.status
    store_name = api.json().get("name") if api.ok else None
    if isinstance(store_name, dict):
        store_name = store_name.get("ar") or store_name.get("en")
    s.check(checks, "h1_text", h1.first.inner_text(), bool(h1.first.text_content().strip()))
    checks["store_api_name"] = store_name
    sections = page.locator("main [section-id]").count()
    has_schema = (ROOT / "templates" / "home.schema.json").exists()
    checks["templates_home_schema_json_exists"] = has_schema
    # No home.schema.json -> vitrin has no default component list to render. Expectation derived from that.
    s.check(checks, "live_section_count", sections, (sections == 0) == (not has_schema))
    checks["main_inner_html_chars"] = page.evaluate("document.querySelector('main').innerHTML.length")
    return s.verdict(checks)


# ── hero ─────────────────────────────────────────────────────────────────────
def hero(page, base, out, checks):
    s = Session(page, base, out)
    fx = dict(background_image=img("hero-d"), background_image_mobile=img("hero-m"))
    # A: primary hero, first section (order 1), schema defaults.
    s.open("hero-primary", [comp("hero", **fx)])
    sec = "section.section-hero"
    s.check(checks, "A_h1_in_section", page.locator(f"{sec} h1").count(), page.locator(f"{sec} h1").count() == 1)
    s.check(checks, "A_h2_in_section", page.locator(f"{sec} h2").count(), page.locator(f"{sec} h2").count() == 0)
    s.check(checks, "A_heading", page.locator(f"{sec} h1").inner_text(), page.locator(f"{sec} h1").inner_text() == "Superbloom 2025")
    img_el = page.locator(f"{sec} img")
    s.check(checks, "A_fetchpriority", img_el.get_attribute("fetchpriority"), img_el.get_attribute("fetchpriority") == "high")
    s.check(checks, "A_no_lazy", img_el.get_attribute("loading"), img_el.get_attribute("loading") is None)
    overlay = js(page, "getComputedStyle(document.querySelector('.section-hero .bg-primary')).opacity")
    s.check(checks, "A_overlay_opacity", overlay, abs(float(overlay) - 0.2) < 1e-6)
    s.check(checks, "A_desktop_min_height", js(page, "document.querySelector('.section-hero').offsetHeight"), js(page, "document.querySelector('.section-hero').offsetHeight") >= 700)
    src = js(page, "document.querySelector('.section-hero img').currentSrc")
    s.check(checks, "A_desktop_src", src, "w=2220" in src and "hero-d" in src)
    s.shot("hero-primary-desktop")
    mobile(page)
    page.wait_for_timeout(500)
    src_m = js(page, "document.querySelector('.section-hero img').currentSrc")
    s.check(checks, "A_mobile_src", src_m, "w=960" in src_m and "hero-m" in src_m)
    s.check(checks, "A_mobile_min_height", js(page, "document.querySelector('.section-hero').offsetHeight"), js(page, "document.querySelector('.section-hero').offsetHeight") >= 700)
    s.shot("hero-primary-mobile")
    desktop(page)
    # The hero is the page's only content here, yet home.jinja's hidden h1 is also there.
    checks["page_h1_count_with_primary_hero"] = page.locator("h1").count()
    # B: not primary, 3rd section (lazy), custom heights, blank heading/description/button.
    s.open(
        "hero-secondary",
        [comp("hero", **fx), comp("hero", 2, **fx), comp("hero", 3, is_primary_hero=False, min_height_desktop=500, min_height_mobile=400, heading="  ", description="", button_text=" ", badge_text="", **fx)],
    )
    third = "section[section-id='hero-3']"
    s.check(checks, "B_no_heading", page.locator(f"{third} h1, {third} h2").count(), page.locator(f"{third} h1, {third} h2").count() == 0)
    s.check(checks, "B_no_button", page.locator(f"{third} a.btn").count(), page.locator(f"{third} a.btn").count() == 0)
    s.check(checks, "B_lazy", page.locator(f"{third} img").get_attribute("loading"), page.locator(f"{third} img").get_attribute("loading") == "lazy")
    s.check(checks, "B_no_fetchpriority", page.locator(f"{third} img").get_attribute("fetchpriority"), page.locator(f"{third} img").get_attribute("fetchpriority") is None)
    h = js(page, f"document.querySelector(\"{third}\").offsetHeight")
    s.check(checks, "B_desktop_min_height_500", h, 500 <= h < 560)
    s.check(checks, "B_hero2_is_h1_when_primary", page.locator("section[section-id='hero-2'] h1").count(), page.locator("section[section-id='hero-2'] h1").count() == 1)
    s.shot("hero-secondary")
    # C: button + overlay + position + variant.
    s.open("hero-button", [comp("hero", button_url="/products", background_position="top", overlay_opacity=55, style_variant="compact", **fx)])
    btn = page.locator("section.section-hero a.btn")
    s.check(checks, "C_button_href", btn.get_attribute("href"), btn.get_attribute("href") == "/products")
    s.check(checks, "C_button_text", btn.inner_text(), btn.inner_text() == "Shop the Collection")
    pos = js(page, "document.querySelector('.section-hero img').style.objectPosition")
    s.check(checks, "C_object_position", pos, pos == "center top")
    s.check(checks, "C_variant", page.locator("section.section-hero").get_attribute("data-variant"), page.locator("section.section-hero").get_attribute("data-variant") == "compact")
    ov = js(page, "getComputedStyle(document.querySelector('.section-hero .bg-primary')).opacity")
    s.check(checks, "C_overlay_55", ov, abs(float(ov) - 0.55) < 1e-6)
    # D: merchant text with markup stays text.
    s.open("hero-xss", [comp("hero", heading='<img src=x onerror="window.__pwn=1">', description="<script>window.__pwn=1</script>", **fx)])
    s.check(checks, "D_no_injected_img", page.locator("section.section-hero h1 img").count(), page.locator("section.section-hero h1 img").count() == 0)
    s.check(checks, "D_no_script_ran", js(page, "window.__pwn === undefined"), js(page, "window.__pwn === undefined"))
    s.check(checks, "D_heading_literal", page.locator("section.section-hero h1").inner_text(), "<img" in page.locator("section.section-hero h1").inner_text())
    # E: empty button url (the schema default "") renders an anchor with href="" (reloads the page).
    s.open("hero-empty-url", [comp("hero", **fx)])
    checks["E_default_button_href_attr"] = page.locator("section.section-hero a.btn").get_attribute("href")
    return s.verdict(checks)


# ── carousel ─────────────────────────────────────────────────────────────────
def _slides(n):
    return [
        {
            "background_image": img(f"slide{i}-d"),
            "background_image_mobile": img(f"slide{i}-m"),
            "heading": f"Slide {i}",
            "description": f"About {i}",
            "button_text": f"Go {i}",
            "button_url": f"/products?slide={i}",
            "badge_text": "",
            "text_alignment": ["start", "center", "end"][i % 3],
            "overlay_opacity": 10 * i,
        }
        for i in range(n)
    ]


def carousel(page, base, out, checks):
    s = Session(page, base, out)
    s.open("carousel-three", [comp("carousel", slides=_slides(3), autoplay_delay=1500)], wait=900)
    dots = page.locator("[data-carousel-dots] button")
    active = lambda: js(page, "[...document.querySelectorAll('[data-carousel-dots] button')].findIndex(b => b.dataset.active === 'true')")
    s.check(checks, "dots_created", dots.count(), dots.count() == 3)
    s.check(checks, "initial_active_dot", active(), active() == 0)
    s.check(checks, "slides_rendered", page.locator(".embla__slide").count(), page.locator(".embla__slide").count() == 3)
    s.check(checks, "data_attrs", js(page, "({...document.querySelector('[data-carousel]').dataset})"), js(page, "document.querySelector('[data-carousel]').dataset.carouselAutoplay") == "1500" and js(page, "document.querySelector('[data-carousel]').dataset.carouselFade") == "true")
    imgs = js(page, "[...document.querySelectorAll('.embla__slide img')].map(i => [i.getAttribute('loading'), i.getAttribute('fetchpriority')])")
    s.check(checks, "lcp_hints", imgs, imgs == [[None, "high"], ["lazy", None], ["lazy", None]])
    s.shot("carousel-initial", full=False)
    # autoplay advances without a click
    page.wait_for_function("() => [...document.querySelectorAll('[data-carousel-dots] button')].findIndex(b => b.dataset.active === 'true') !== 0", timeout=6000)
    s.check(checks, "autoplay_advanced_to", active(), active() != 0)
    # dot click goes to that slide, every dot
    reached = []
    for target in (2, 0, 1):
        dots.nth(target).click()
        page.wait_for_function(f"() => document.querySelectorAll('[data-carousel-dots] button')[{target}].dataset.active === 'true'", timeout=3000)
        reached.append(active())
    s.check(checks, "dot_click_reaches", reached, reached == [2, 0, 1])
    # exactly one dot is active at any time
    n_active = js(page, "document.querySelectorAll('[data-carousel-dots] button[data-active=true]').length")
    s.check(checks, "one_active_dot", n_active, n_active == 1)
    s.shot("carousel-after-dots", full=False)
    # slide content
    first = page.locator(".embla__slide").first
    s.check(checks, "slide0_heading", first.locator("h2").inner_text(), first.locator("h2").inner_text() == "Slide 0")
    s.check(checks, "slide0_button_href", first.locator("a.btn").get_attribute("href"), first.locator("a.btn").get_attribute("href") == "/products?slide=0")
    ov = js(page, "getComputedStyle(document.querySelectorAll('.embla__slide .bg-primary')[2]).opacity")
    s.check(checks, "slide2_overlay_opacity", ov, abs(float(ov) - 0.2) < 1e-6)
    s.check(checks, "slide_min_height", js(page, "document.querySelector('.embla__slide').offsetHeight"), js(page, "document.querySelector('.embla__slide').offsetHeight") >= 700)
    # single slide: no dots, no embla init; autoplay off -> empty attribute; slide w/o text renders no text block
    s.open("carousel-one", [comp("carousel", slides=[{"background_image": img("only-d"), "heading": ""}], autoplay_enabled=False, transition_effect="slide")])
    s.check(checks, "single_no_dots", page.locator("[data-carousel-dots]").count(), page.locator("[data-carousel-dots]").count() == 0)
    s.check(checks, "autoplay_off_attr", page.locator("[data-carousel]").get_attribute("data-carousel-autoplay"), page.locator("[data-carousel]").get_attribute("data-carousel-autoplay") == "")
    s.check(checks, "fade_off_attr", page.locator("[data-carousel]").get_attribute("data-carousel-fade"), page.locator("[data-carousel]").get_attribute("data-carousel-fade") == "false")
    s.check(checks, "no_text_block_without_content", page.locator(".embla__slide .theme-container").count(), page.locator(".embla__slide .theme-container").count() == 0)
    # show_dots off with several slides
    s.open("carousel-nodots", [comp("carousel", slides=_slides(2), show_dots=False)])
    s.check(checks, "show_dots_false", page.locator("[data-carousel-dots]").count(), page.locator("[data-carousel-dots]").count() == 0)
    # no slides at all
    s.open("carousel-empty", [comp("carousel")])
    s.check(checks, "empty_slides_rendered", page.locator(".embla__slide").count(), page.locator(".embla__slide").count() == 0)
    return s.verdict(checks)


# ── categories ───────────────────────────────────────────────────────────────
def _cats(n):
    return [
        {
            "category": {
                "id": f"c{i:02d}",
                "slug": f"cat-{i}",
                "name": f"Category {i}",
                "image": f"cat{i}" if i != 1 else None,
                "image_full_size": img(f"cat{i}"),
            }
        }
        for i in range(n)
    ]


def categories(page, base, out, checks):
    s = Session(page, base, out)
    cats = _cats(12)
    cats[2]["category"]["name"] = '<b id="pwn">bold</b>'
    s.open("categories", [comp("categories", categories=cats, display_more=True)], wait=900)
    slides = page.locator("section.section-categories .embla__slide")
    s.check(checks, "slide_count", slides.count(), slides.count() == 12)
    hrefs = js(page, "[...document.querySelectorAll('.section-categories .embla__slide a')].map(a => a.getAttribute('href'))")
    s.check(checks, "hrefs_ok", hrefs[:3], hrefs == [f"/categories/c{i:02d}/cat-{i}" for i in range(12)])
    s.check(checks, "name_escaped", page.locator("#pwn").count(), page.locator("#pwn").count() == 0)
    s.check(checks, "name_literal", slides.nth(2).locator("h3").inner_text(), "<b" in slides.nth(2).locator("h3").inner_text())
    alts = js(page, "[...document.querySelectorAll('.section-categories .embla__slide img')].map(i => i.alt)")
    s.check(checks, "alt_is_name", alts[:2], alts[0] == "Category 0" and alts[1] == "Category 1")
    srcs = js(page, "[...document.querySelectorAll('.section-categories .embla__slide img')].map(i => i.getAttribute('src'))")
    s.check(checks, "image_widths", [srcs[0][:22], srcs[1][:50]], "w=768" in srcs[0] and "product-img.svg" in srcs[1] and "w=235" in srcs[1])
    lazy = js(page, "[...document.querySelectorAll('.section-categories .embla__slide img')].map(i => i.getAttribute('loading'))")
    s.check(checks, "lazy_attr_order1", lazy[:3], lazy[0] is None and lazy[1] == "lazy")
    # view-all links (desktop + mobile copies)
    more = js(page, "[...document.querySelectorAll('.section-categories a[href=\"/categories\"]')].map(a => a.textContent.trim())")
    s.check(checks, "view_all_links", more, more == ["View all", "View all"])
    # carousel controls: 12 slides overflow, next scrolls, progress grows, prev enables
    nxt, prv = page.locator(".section-categories .embla__next"), page.locator(".section-categories .embla__prev")
    s.check(checks, "prev_disabled_at_start", prv.is_disabled(), prv.is_disabled())
    s.check(checks, "next_enabled_at_start", nxt.is_disabled(), not nxt.is_disabled())
    bar = lambda: js(page, "parseFloat(document.querySelector('.section-categories [data-carousel-progress]').style.width)")
    before = bar()
    nxt.click()
    page.wait_for_function("() => parseFloat(document.querySelector('.section-categories [data-carousel-progress]').style.width) > 0", timeout=4000)
    s.check(checks, "progress_after_next", [before, bar()], bar() > before)
    s.check(checks, "prev_enabled_after_next", prv.is_disabled(), not prv.is_disabled())
    s.shot("categories-after-next", full=False)
    clicks = 0
    while not nxt.is_disabled() and clicks < 30:
        nxt.click()
        page.wait_for_timeout(350)
        clicks += 1
    s.check(checks, "next_disables_at_end", [clicks, nxt.is_disabled()], nxt.is_disabled() and clicks < 30)
    try:
        page.wait_for_function("() => parseFloat(document.querySelector('.section-categories [data-carousel-progress]').style.width) > 99", timeout=4000)
    except PlaywrightTimeoutError:
        pass
    s.check(checks, "progress_at_end", bar(), bar() > 99)
    # display_more false -> no links; no categories -> title only
    s.open("categories-nomore", [comp("categories", categories=_cats(3))])
    s.check(checks, "no_more_link_default", page.locator(".section-categories a[href='/categories']").count(), page.locator(".section-categories a[href='/categories']").count() == 0)
    s.open("categories-empty", [comp("categories")])
    s.check(checks, "empty_slides", page.locator(".section-categories .embla__slide").count(), page.locator(".section-categories .embla__slide").count() == 0)
    s.check(checks, "empty_title_kept", page.locator(".section-categories h2").inner_text(), page.locator(".section-categories h2").inner_text() == "Discover our signature collections")
    return s.verdict(checks)


# ── products ─────────────────────────────────────────────────────────────────
def products(page, base, out, checks):
    s = Session(page, base, out)
    api = page.request.get(base + "/api/v1/products?page_size=6")
    results = api.json()["results"]
    checks["api_products"] = [p["name"] for p in results]
    checks["live_api_count"] = api.json().get("count")
    s.check(checks, "api_has_products", len(results), len(results) >= 3)
    pr = {"results": results, "url": "/categories/c01/x"}
    card = "[data-product-card]"
    # carousel (schema default layout)
    s.open("products-carousel", [comp("products", title="Best sellers", products=pr, more_text="See all")], wait=900)
    s.check(checks, "carousel_marker", page.locator("[data-products-carousel]").count(), page.locator("[data-products-carousel]").count() == 1)
    s.check(checks, "carousel_cards", page.locator(card).count(), page.locator(card).count() == len(results))
    s.check(checks, "carousel_title", page.locator(".section-products h2").first.inner_text(), page.locator(".section-products h2").first.inner_text() == "Best sellers")
    more = js(page, "[...document.querySelectorAll('.section-products a')].filter(a => a.textContent.trim() === 'See all').map(a => a.getAttribute('href'))")
    s.check(checks, "carousel_more_href_is_settings_url", more, more and all(h == "/categories/c01/x" for h in more))
    names = js(page, f"[...document.querySelectorAll('{card}')].map(c => c.innerText)")
    s.check(checks, "card_names_from_data", [n for n in names[:2]], all(any(p["name"] in n for n in names) for p in results))
    s.shot("products-carousel")
    # grid
    s.open("products-grid", [comp("products", layout="grid", title="Grid", products={"results": results}, more_text="More")])
    s.check(checks, "grid_marker", page.locator("[data-grid-root][data-grid='grid']").count(), page.locator("[data-grid-root][data-grid='grid']").count() == 1)
    s.check(checks, "grid_cards", page.locator(card).count(), page.locator(card).count() == len(results))
    gm = js(page, "[...document.querySelectorAll('.section-products a')].filter(a => a.textContent.trim() === 'More').map(a => a.getAttribute('href'))")
    s.check(checks, "grid_more_default_url", gm, gm == ["/products"])
    s.shot("products-grid")
    # list
    s.open("products-list", [comp("products", layout="list", products={"results": results}, display_more=False)])
    s.check(checks, "list_marker", page.locator("[data-grid-root][data-grid='list']").count(), page.locator("[data-grid-root][data-grid='list']").count() == 1)
    s.check(checks, "list_no_title_no_header", page.locator(".section-products h2").count(), page.locator(".section-products h2").count() == 0)
    # display_more false -> no link; display_more true but no text -> no link
    s.open("products-nomore", [comp("products", title="T", products={"results": results}, display_more=False, more_text="X")])
    s.check(checks, "carousel_no_more_when_off", js(page, "[...document.querySelectorAll('.section-products a')].filter(a => a.textContent.trim() === 'X').length"), js(page, "[...document.querySelectorAll('.section-products a')].filter(a => a.textContent.trim() === 'X').length") == 0)
    # section absent without products / with empty results
    s.open("products-none", [comp("products"), comp("products", 2, products={"results": []})])
    s.check(checks, "absent_without_data", page.locator("section.section-products").count(), page.locator("section.section-products").count() == 0)
    return s.verdict(checks)


# ── testimonials ─────────────────────────────────────────────────────────────
def testimonials(page, base, out, checks):
    s = Session(page, base, out)
    items = [
        {"rating": 5, "text": "Great", "name": "Ali"},
        {"rating": 3, "text": '<img src=x id="pwn" onerror="window.__pwn=1">', "name": "<i>Sara</i>"},
        {"rating": 0, "text": "No stars", "name": "  "},
        {"rating": 4, "text": "Four", "name": "Omar"},
        {"rating": 5, "text": "Five", "name": "Lina"},
    ]
    s.open("testimonials", [comp("testimonials", testimonials=items)], wait=900)
    arts = page.locator("section.section-testimonials article")
    s.check(checks, "article_count", arts.count(), arts.count() == 5)
    stars = js(page, "[...document.querySelectorAll('.section-testimonials article')].map(a => [a.querySelectorAll('svg.text-warning').length, a.querySelectorAll('svg.text-muted-foreground').length])")
    s.check(checks, "star_fill_counts", stars, stars == [[5, 0], [3, 2], [0, 0], [4, 1], [5, 0]])
    aria = js(page, "[...document.querySelectorAll('.section-testimonials article [aria-label]')].map(a => a.getAttribute('aria-label'))")
    s.check(checks, "rating_aria", aria, aria == ["5 out of 5 stars", "3 out of 5 stars", "4 out of 5 stars", "5 out of 5 stars"])
    s.check(checks, "xss_text_not_executed", [page.locator("#pwn").count(), js(page, "window.__pwn === undefined")], page.locator("#pwn").count() == 0 and js(page, "window.__pwn === undefined"))
    s.check(checks, "blank_name_no_h3", arts.nth(2).locator("h3").count(), arts.nth(2).locator("h3").count() == 0)
    s.check(checks, "name_escaped", arts.nth(1).locator("h3 i").count(), arts.nth(1).locator("h3 i").count() == 0)
    # carousel behaviour at desktop (3 per view, 5 slides -> scrollable)
    nxt, prv = page.locator(".section-testimonials .embla__next"), page.locator(".section-testimonials .embla__prev")
    s.check(checks, "buttons_labelled", [nxt.get_attribute("aria-label"), prv.get_attribute("aria-label")], nxt.get_attribute("aria-label") == "Next" and prv.get_attribute("aria-label") == "Previous")
    s.check(checks, "prev_disabled_at_start", prv.is_disabled(), prv.is_disabled() and not nxt.is_disabled())
    nxt.click()
    page.wait_for_function("() => parseFloat(document.querySelector('.section-testimonials [data-carousel-progress]').style.width) > 0", timeout=4000)
    s.check(checks, "prev_enabled_after_next", prv.is_disabled(), not prv.is_disabled())
    s.shot("testimonials", full=False)
    clicks = 0
    while not nxt.is_disabled() and clicks < 10:
        nxt.click()
        page.wait_for_timeout(350)
        clicks += 1
    s.check(checks, "next_disables_at_end", [clicks, nxt.is_disabled()], nxt.is_disabled())
    # slide basis: 33.33% desktop, 83.33% xs
    w = js(page, "document.querySelector('.section-testimonials .embla__slide').getBoundingClientRect().width / document.querySelector('.section-testimonials .embla__container').getBoundingClientRect().width")
    s.check(checks, "desktop_three_per_view", round(w, 2), 0.3 < w < 0.37)
    s.open("testimonials-empty", [comp("testimonials", title="  ")])
    s.check(checks, "empty_no_slides", page.locator(".section-testimonials article").count(), page.locator(".section-testimonials article").count() == 0)
    s.check(checks, "blank_title_no_h2", page.locator(".section-testimonials h2").count(), page.locator(".section-testimonials h2").count() == 0)
    return s.verdict(checks)


# ── partners ─────────────────────────────────────────────────────────────────
def partners(page, base, out, checks):
    s = Session(page, base, out)
    items = [
        {"name": f"Partner {i}", "image": img(f"p{i}"), "url": f"https://p{i}.example" if i % 2 == 0 else "", "image_mobile": img(f"p{i}-m") if i == 1 else ""}
        for i in range(14)
    ]
    s.open("partners", [comp("partners", store_partners=items)], wait=1500)
    slides = page.locator(".section-partners .embla__slide")
    s.check(checks, "slide_count", slides.count(), slides.count() == 14)
    s.check(checks, "link_count", page.locator(".section-partners .embla__slide a").count(), page.locator(".section-partners .embla__slide a").count() == 7)
    hrefs = js(page, "[...document.querySelectorAll('.section-partners a')].map(a => a.getAttribute('href'))")
    s.check(checks, "link_hrefs", hrefs[:2], hrefs[0] == "https://p0.example" and hrefs[1] == "https://p2.example")
    alts = js(page, "[...document.querySelectorAll('.section-partners img')].map(i => i.alt)")
    s.check(checks, "alts", alts[:2], alts[:2] == ["Partner 0", "Partner 1"])
    s.check(checks, "autoscroll_attr", page.locator("[data-carousel]").get_attribute("data-carousel-autoscroll"), page.locator("[data-carousel]").get_attribute("data-carousel-autoscroll") == "0.5")
    # autoscroll moves the track with no interaction
    t0 = js(page, "document.querySelector('.section-partners .embla__container').style.transform")
    page.wait_for_timeout(1500)
    t1 = js(page, "document.querySelector('.section-partners .embla__container').style.transform")
    s.check(checks, "autoscroll_moves_track", [t0, t1], t0 != t1)
    s.check(checks, "title_default", page.locator(".section-partners h2").inner_text(), page.locator(".section-partners h2").inner_text() == "Our Partners")
    s.shot("partners-desktop", full=False)
    mobile(page)
    page.wait_for_timeout(500)
    src = js(page, "document.querySelectorAll('.section-partners img')[1].currentSrc")
    s.check(checks, "mobile_source_used", src, "p1-m" in src and "w=160" in src)
    s.shot("partners-mobile", full=False)
    desktop(page)
    s.open("partners-empty", [comp("partners")])
    s.check(checks, "empty_no_carousel", page.locator(".section-partners [data-carousel]").count(), page.locator(".section-partners [data-carousel]").count() == 0)
    return s.verdict(checks)


# ── gallery ──────────────────────────────────────────────────────────────────
def _gallery(n):
    return [{"src": img(f"g{i}"), "src_mobile": img(f"g{i}-m") if i == 0 else "", "alt": f"Photo {i}", "image_title": f"Title {i}" if i == 0 else "", "primary_button_text": "Buy" if i == 0 else "", "primary_button_url": "/products" if i == 0 else "", "secondary_button_text": "More" if i == 0 else "", "secondary_button_url": ""} for i in range(n)]


def gallery(page, base, out, checks):
    s = Session(page, base, out)
    geo = "[...document.querySelectorAll('.section-gallery [data-items-count] > div')].map(d => { const r = d.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), Math.round(r.left), Math.round(r.top)]; })"
    for n in (1, 2, 3, 4, 5, 6):
        s.open(f"gallery-{n}", [comp("gallery", gallery=_gallery(n), title="Our gallery")], wait=300)
        s.check(checks, f"n{n}_items_attr", page.locator("[data-items-count]").get_attribute("data-items-count"), page.locator("[data-items-count]").get_attribute("data-items-count") == str(n))
        g = js(page, geo)
        checks[f"n{n}_geometry_wh_left_top"] = g
        s.check(checks, f"n{n}_item_count", len(g), len(g) == n)
        if n in (3, 5):  # first tile spans 2 cols x 2 rows
            s.check(checks, f"n{n}_first_tile_double", [g[0][0], g[1][0], g[0][1], g[1][1]], abs(g[0][0] - 2 * g[1][0]) < 24 and g[0][1] > g[1][1] * 1.8)
        if n == 1:
            s.check(checks, "n1_spans_half_row", g[0][0], g[0][0] > 400)
        if n == 2:
            s.check(checks, "n2_two_columns", [g[0][2], g[1][2]], g[0][3] == g[1][3])
        if n == 4:
            s.check(checks, "n4_two_by_two", [g[0][3], g[1][3], g[2][3]], g[0][3] == g[1][3] and g[2][3] > g[0][3])
        if n == 6:
            s.check(checks, "n6_four_columns_first_row", [g[i][3] for i in range(5)], g[0][3] == g[1][3] == g[2][3] == g[3][3] and g[4][3] > g[0][3])
        s.shot(f"gallery-{n}")
    s.open("gallery-3b", [comp("gallery", gallery=_gallery(3), title="Our gallery")], wait=300)
    first = page.locator(".section-gallery [data-items-count] > div").first
    s.check(checks, "overlay_title", first.locator("h3").inner_text(), first.locator("h3").inner_text() == "Title 0")
    btns = js(page, "[...document.querySelectorAll('.section-gallery [data-items-count] > div:first-child a')].map(a => [a.textContent.trim(), a.getAttribute('href')])")
    s.check(checks, "button_needs_text_and_url", btns, btns == [["Buy", "/products"]])
    s.check(checks, "no_overlay_for_plain_tiles", page.locator(".section-gallery [data-items-count] > div:nth-child(2) h3, .section-gallery [data-items-count] > div:nth-child(2) a").count(), page.locator(".section-gallery [data-items-count] > div:nth-child(2) h3, .section-gallery [data-items-count] > div:nth-child(2) a").count() == 0)
    lazy = js(page, "[...document.querySelectorAll('.section-gallery img')].map(i => i.getAttribute('loading'))")
    s.check(checks, "lazy_all_but_first_at_order1", lazy, lazy == [None, "lazy", "lazy"])
    s.open("gallery-lazy", [comp("gallery", 1, gallery=_gallery(2)), comp("gallery", 2, gallery=_gallery(2)), comp("gallery", 3, gallery=_gallery(2))], wait=300)
    lazy3 = js(page, "[...document.querySelectorAll('section[section-id=gallery-3] img')].map(i => i.getAttribute('loading'))")
    s.check(checks, "order3_all_lazy", lazy3, lazy3 == ["lazy", "lazy"])
    s.check(checks, "no_title_no_h2", page.locator("section[section-id=gallery-1] h2").count(), page.locator("section[section-id=gallery-1] h2").count() == 0)
    s.open("gallery-empty", [comp("gallery", title="T")])
    s.check(checks, "empty_no_grid", page.locator("[data-items-count]").count(), page.locator("[data-items-count]").count() == 0)
    return s.verdict(checks)


# ── video ────────────────────────────────────────────────────────────────────
PLAY_STUB = "(() => { window.__plays = 0; HTMLMediaElement.prototype.play = function () { window.__plays++; return Promise.resolve(); }; })()"


def video(page, base, out, checks):
    s = Session(page, base, out)
    page.add_init_script(PLAY_STUB)
    s.open("video-click", [comp("video", title="Watch <b id=pwn>us</b>", video="/__media/a.mp4", poster_image=img("poster"))])
    v = page.locator("section.section-video video")
    s.check(checks, "source_src", page.locator("section.section-video source").get_attribute("src"), page.locator("section.section-video source").get_attribute("src") == "/__media/a.mp4")
    s.check(checks, "poster_w1280", v.get_attribute("poster"), "w=1280" in (v.get_attribute("poster") or "") and "poster" in v.get_attribute("poster"))
    s.check(checks, "overlay_present", page.locator(".video-overlay").count(), page.locator(".video-overlay").count() == 1)
    s.check(checks, "title_escaped", page.locator("#pwn").count(), page.locator("#pwn").count() == 0)
    s.check(checks, "not_muted_not_autoplay", [v.get_attribute("autoplay"), v.get_attribute("controls")], v.get_attribute("autoplay") is None and v.get_attribute("controls") is None)
    s.check(checks, "preload_metadata_at_order1", v.get_attribute("preload"), (v.get_attribute("preload") or "").strip() == "metadata")
    s.shot("video-before-click", full=False)
    page.locator(".play-button").click()
    s.check(checks, "play_called_once", js(page, "window.__plays"), js(page, "window.__plays") == 1)
    page.wait_for_function("() => getComputedStyle(document.querySelector('.video-overlay')).display === 'none'", timeout=3000)
    disp = js(page, "getComputedStyle(document.querySelector('.video-overlay')).display")
    s.check(checks, "overlay_hidden_after_play", disp, disp == "none")
    s.shot("video-after-click", full=False)
    # autoplay: no overlay, no script, autoplay+muted attributes
    s.open("video-autoplay", [comp("video", video="/__media/a.mp4", autoplay=True, controls=True)])
    va = page.locator("section.section-video video")
    s.check(checks, "autoplay_attrs", [va.get_attribute("autoplay"), va.get_attribute("muted"), va.get_attribute("controls")], va.get_attribute("autoplay") is not None and va.get_attribute("muted") is not None and va.get_attribute("controls") is not None)
    s.check(checks, "autoplay_no_overlay", page.locator(".video-overlay").count(), page.locator(".video-overlay").count() == 0)
    # lazy preload + no video
    s.open("video-lazy", [comp("video", 1, video="/__media/a.mp4"), comp("video", 2, video="/__media/a.mp4"), comp("video", 3, video="/__media/a.mp4"), comp("video", 4)])
    pre = js(page, "[...document.querySelectorAll('video')].map(v => v.getAttribute('preload').trim())")
    s.check(checks, "preload_by_order", pre, pre == ["metadata", "metadata", "none"])
    s.check(checks, "no_video_no_wrapper", page.locator("section[section-id=video-4] .video-wrapper").count(), page.locator("section[section-id=video-4] .video-wrapper").count() == 0)
    return s.verdict(checks)


# ── countdown ────────────────────────────────────────────────────────────────
def _iso(delta):
    return (datetime.now(UTC) + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


def countdown(page, base, out, checks):
    s = Session(page, base, out)
    end = _iso(timedelta(days=2, hours=3, minutes=4, seconds=30))
    s.open("countdown-future", [comp("countdown", title="Sale ends", badge_text="HOT", description="Hurry", end_date=end, button_text="Buy", button_url="/products", background_image=img("cd-d"), background_image_mobile=img("cd-m"))], wait=1200)
    read = "(() => { const g = c => parseInt(document.querySelector('.' + c).textContent, 10); return {d: g('days-value'), h: g('hours-value'), m: g('minutes-value'), s: g('seconds-value'), now: Date.now()}; })()"
    r1 = js(page, read)
    end_ms = int(datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp() * 1000)
    total = lambda r: r["d"] * 86400 + r["h"] * 3600 + r["m"] * 60 + r["s"]
    expect = (end_ms - r1["now"]) / 1000
    s.check(checks, "displayed_matches_remaining", [total(r1), round(expect, 1)], abs(total(r1) - expect) <= 2)
    s.check(checks, "fields_in_range", r1, 0 <= r1["h"] < 24 and 0 <= r1["m"] < 60 and 0 <= r1["s"] < 60 and r1["d"] == 2)
    s.check(checks, "padded_two_digits", js(page, "[...document.querySelectorAll('.countdown-timer [class$=-value], .countdown-timer [class*=-value]')].map(e => e.textContent.trim().length)"), all(n == 2 for n in js(page, "[...document.querySelectorAll('.countdown-timer [class*=-value]')].map(e => e.textContent.trim().length)")))
    page.wait_for_timeout(2300)
    r2 = js(page, read)
    s.check(checks, "ticks_down", [total(r1), total(r2)], 1 <= total(r1) - total(r2) <= 4)
    s.check(checks, "labels", js(page, "[...document.querySelectorAll('.countdown-timer span:not([class*=-value])')].map(e => e.textContent.trim()).filter(Boolean)"), js(page, "[...document.querySelectorAll('.countdown-timer span:not([class*=-value])')].map(e => e.textContent.trim()).filter(Boolean)") == ["Day", "Hour", "Min", "Sec"])
    txt = js(page, "document.querySelector('.countdown-content').innerText").lower()
    s.check(checks, "content_text", txt[:60], "sale ends" in txt and "hot" in txt and "hurry" in txt)
    s.check(checks, "button", page.locator("section.section-countdown a.btn").get_attribute("href"), page.locator("section.section-countdown a.btn").get_attribute("href") == "/products")
    s.shot("countdown-future")
    # never negative: expire within the run, sample every 250 ms until the section hides
    s.open("countdown-expiring", [comp("countdown", title="Soon", end_date=_iso(timedelta(seconds=3)))], wait=100)
    samples = js(page, """new Promise(res => {
      const out = []; const t0 = Date.now();
      const tick = () => {
        const sec = document.querySelector('section.section-countdown');
        out.push({t: Date.now() - t0, hidden: getComputedStyle(sec).display === 'none',
          v: ['days','hours','minutes','seconds'].map(c => document.querySelector('.' + c + '-value').textContent.trim())});
        if (out[out.length - 1].hidden || Date.now() - t0 > 7000) return res(out);
        setTimeout(tick, 250);
      }; tick(); })""")
    vals = [x for smp in samples for x in smp["v"]]
    s.check(checks, "no_negative_or_nan_values", [len(samples), samples[-1]], all(re.fullmatch(r"\d{2,}", x) for x in vals))
    s.check(checks, "section_hides_at_expiry", samples[-1], samples[-1]["hidden"])
    # expired / missing / garbage date at load -> content hidden
    for name, val in (("past", _iso(timedelta(days=-1))), ("empty", ""), ("garbage", 'not a date");window.__pwn=1;("')):
        s.open(f"countdown-{name}", [comp("countdown", title="T", end_date=val)], wait=400)
        cc = js(page, "getComputedStyle(document.querySelector('.countdown-content')).display")
        s.check(checks, f"{name}_content_hidden", cc, cc == "none")
        checks[f"{name}_section_visible_height"] = js(page, "document.querySelector('section.section-countdown').offsetHeight")
        if name == "garbage":
            s.check(checks, "garbage_cannot_inject_js", js(page, "window.__pwn === undefined"), js(page, "window.__pwn === undefined"))
    return s.verdict(checks)


# ── benefits ─────────────────────────────────────────────────────────────────
def benefits(page, base, out, checks):
    s = Session(page, base, out)
    feats = [
        {"image": img("b0"), "image_mobile": img("b0-m"), "title": "Free shipping", "description": "Over 100"},
        {"image": "", "title": '<b id="pwn">Bold</b>', "description": "  "},
        {"image": img("b2"), "title": "  ", "description": "Only text"},
        {"image": img("b3"), "title": "Four", "description": ""},
    ]
    s.open("benefits", [comp("benefits", store_features=feats)])
    items = page.locator(".section-benefits .grid > div")
    s.check(checks, "item_count", items.count(), items.count() == 4)
    s.check(checks, "img_only_with_image", js(page, "[...document.querySelectorAll('.section-benefits .grid > div')].map(d => d.querySelectorAll('img').length)"), js(page, "[...document.querySelectorAll('.section-benefits .grid > div')].map(d => d.querySelectorAll('img').length)") == [1, 0, 1, 1])
    s.check(checks, "h3_only_when_title", js(page, "[...document.querySelectorAll('.section-benefits .grid > div')].map(d => d.querySelectorAll('h3').length)"), js(page, "[...document.querySelectorAll('.section-benefits .grid > div')].map(d => d.querySelectorAll('h3').length)") == [1, 1, 0, 1])
    s.check(checks, "p_only_when_description", js(page, "[...document.querySelectorAll('.section-benefits .grid > div')].map(d => d.querySelectorAll('p').length)"), js(page, "[...document.querySelectorAll('.section-benefits .grid > div')].map(d => d.querySelectorAll('p').length)") == [1, 0, 1, 0])
    s.check(checks, "title_escaped", page.locator("#pwn").count(), page.locator("#pwn").count() == 0)
    s.check(checks, "alt_is_title", page.locator(".section-benefits img").first.get_attribute("alt"), page.locator(".section-benefits img").first.get_attribute("alt") == "Free shipping")
    s.check(checks, "desktop_columns", len({round(b["x"]) for b in js(page, "[...document.querySelectorAll('.section-benefits .grid > div')].map(d => d.getBoundingClientRect().toJSON())")}), len({round(b["x"]) for b in js(page, "[...document.querySelectorAll('.section-benefits .grid > div')].map(d => d.getBoundingClientRect().toJSON())")}) == 4)
    s.shot("benefits-desktop", full=False)
    mobile(page)
    page.wait_for_timeout(400)
    cols = len({round(b["x"]) for b in js(page, "[...document.querySelectorAll('.section-benefits .grid > div')].map(d => d.getBoundingClientRect().toJSON())")})
    s.check(checks, "mobile_two_columns", cols, cols == 2)
    src = js(page, "document.querySelector('.section-benefits img').currentSrc")
    s.check(checks, "mobile_image_used", src, "b0-m" in src and "w=96" in src)
    s.shot("benefits-mobile", full=False)
    desktop(page)
    s.open("benefits-lazy", [comp("benefits", 1, store_features=feats[:1]), comp("benefits", 2, store_features=feats[:1]), comp("benefits", 3, store_features=feats[:1])])
    lz = js(page, "[...document.querySelectorAll('.section-benefits img')].map(i => i.getAttribute('loading'))")
    s.check(checks, "lazy_by_order", lz, lz == [None, None, "lazy"])
    s.open("benefits-empty", [comp("benefits")])
    s.check(checks, "empty_no_grid", page.locator(".section-benefits .grid").count(), page.locator(".section-benefits .grid").count() == 0)
    return s.verdict(checks)


# ── call to action ───────────────────────────────────────────────────────────
def call_to_action(page, base, out, checks):
    s = Session(page, base, out)
    s.open("cta-default", [comp("call-to-action")])
    sec = "section.section-call-to-action"
    s.check(checks, "default_heading", page.locator(f"{sec} h2").inner_text(), page.locator(f"{sec} h2").inner_text() == "هل أنت مستعد للبدء؟")
    s.check(checks, "default_button_text", page.locator(f"{sec} a.btn").inner_text(), page.locator(f"{sec} a.btn").inner_text() == "تسوق الآن")
    checks["default_button_href_attr"] = page.locator(f"{sec} a.btn").get_attribute("href")
    s.check(checks, "default_text_color", js(page, "document.querySelector('.section-call-to-action .flex-col.gap-4').style.color"), js(page, "document.querySelector('.section-call-to-action .flex-col.gap-4').style.color") in ("rgb(0, 0, 0)", "#000000"))
    s.check(checks, "no_bg_image_by_default", page.locator(f"{sec} img").count(), page.locator(f"{sec} img").count() == 0)
    s.shot("cta-default")
    s.open("cta-custom", [comp("call-to-action", heading="Join", description="Now", button_url="/products", text_color="#ff0000", background_color="#00ff00", background_image=img("cta-bg"))])
    s.check(checks, "bg_color", js(page, "getComputedStyle(document.querySelector('.section-call-to-action')).backgroundColor"), js(page, "getComputedStyle(document.querySelector('.section-call-to-action')).backgroundColor") == "rgb(0, 255, 0)")
    s.check(checks, "text_color", js(page, "getComputedStyle(document.querySelector('.section-call-to-action h2')).color"), js(page, "getComputedStyle(document.querySelector('.section-call-to-action h2')).color") == "rgb(255, 0, 0)")
    s.check(checks, "button_href", page.locator(f"{sec} a.btn").get_attribute("href"), page.locator(f"{sec} a.btn").get_attribute("href") == "/products")
    im = page.locator(f"{sec} img")
    s.check(checks, "bg_image_alt_and_width", [im.get_attribute("alt"), im.get_attribute("src")[:20]], im.get_attribute("alt") == "Join" and "w=2220" in im.get_attribute("src"))
    s.shot("cta-custom")
    s.open("cta-blank", [comp("call-to-action", heading=" ", description="  ", button_text="")])
    s.check(checks, "blank_hides_all_text", page.locator(f"{sec} h2, {sec} p, {sec} a").count(), page.locator(f"{sec} h2, {sec} p, {sec} a").count() == 0)
    s.open("cta-xss", [comp("call-to-action", heading='<img id="pwn" src=x onerror="window.__pwn=1">', background_color='red;" onmouseover="window.__pwn=2')])
    s.check(checks, "heading_not_html", page.locator("#pwn").count(), page.locator("#pwn").count() == 0)
    s.check(checks, "style_attr_cannot_be_broken", js(page, "document.querySelector('.section-call-to-action').hasAttribute('onmouseover')"), not js(page, "document.querySelector('.section-call-to-action').hasAttribute('onmouseover')"))
    return s.verdict(checks)


# ── logo & social ────────────────────────────────────────────────────────────
CONTACT_ALL = {"facebook": "fb", "instagram": "ig", "twitter": "tw", "snapchat": "sc", "tiktok": "tt", "youtube": "yt", "linkedin": "li"}
EXPECTED_HREFS = {
    "Facebook": "https://www.facebook.com/fb",
    "Instagram": "https://www.instagram.com/ig",
    "LinkedIn": "https://www.linkedin.com/company/li",
    "X": "https://twitter.com/tw",
    "YouTube": "https://www.youtube.com/yt",
    "Snapchat": "https://www.snapchat.com/add/sc",
    "TikTok": "https://www.tiktok.com/@tt",
}


def logo_social(page, base, out, checks):
    s = Session(page, base, out)
    sec = "section.section-logo-social"
    store = {"name": "Acme <i id=pwn>Co</i>", "logo": "store-logo", "settings": {"contact": {**CONTACT_ALL, "title": "Find us"}}}
    s.open("logo-social-full", [comp("logo-social")], store=store)
    links = js(page, "[...document.querySelectorAll('.section-logo-social a')].map(a => [a.querySelector('.sr-only').textContent, a.getAttribute('href'), a.getAttribute('target'), a.getAttribute('rel')])")
    s.check(checks, "seven_links", len(links), len(links) == 7)
    s.check(checks, "hrefs", {k: h for k, h, *_ in links}, {k: h for k, h, *_ in links} == EXPECTED_HREFS)
    s.check(checks, "new_tab_noopener", [(t, r) for *_, t, r in links], all(t == "_blank" and r == "noopener" for *_, t, r in links))
    s.check(checks, "contact_title_used", page.locator(f"{sec} span.text-sm").inner_text(), page.locator(f"{sec} span.text-sm").inner_text() == "Find us")
    imgs = js(page, "[...document.querySelectorAll('.section-logo-social img')].map(i => [i.alt, i.getAttribute('src')])")
    s.check(checks, "store_logo_used_for_desktop_and_mobile", imgs, len(imgs) == 1 and "store-logo" in imgs[0][1] and imgs[0][0] == "Acme <i id=pwn>Co</i>")
    s.check(checks, "store_name_alt_not_html", page.locator("#pwn").count(), page.locator("#pwn").count() == 0)
    h = js(page, "document.querySelector('.section-logo-social').offsetHeight")
    s.check(checks, "desktop_min_height_280", h, h >= 280)
    s.shot("logo-social-full", full=False)
    mobile(page)
    page.wait_for_timeout(300)
    hm = js(page, "document.querySelector('.section-logo-social').offsetHeight")
    s.check(checks, "mobile_min_height_200", hm, hm >= 200)
    desktop(page)
    # no socials, no contact title -> no block; no logo -> store name heading
    s.open("logo-social-bare", [comp("logo-social")], store={"name": "Bare Store", "settings": {"contact": {}}})
    s.check(checks, "no_social_block", page.locator(f"{sec} a").count() + page.locator(f"{sec} span.text-sm").count(), page.locator(f"{sec} a").count() + page.locator(f"{sec} span.text-sm").count() == 0)
    s.check(checks, "name_heading_without_logo", [page.locator(f"{sec} img").count(), page.locator(f"{sec} h2").inner_text()], page.locator(f"{sec} img").count() == 0 and page.locator(f"{sec} h2").inner_text() == "Bare Store")
    # default title text when none given
    s.open("logo-social-follow", [comp("logo-social")], store={"name": "S", "settings": {"contact": {"facebook": "x"}}})
    s.check(checks, "follow_us_default", page.locator(f"{sec} span.text-sm").inner_text(), page.locator(f"{sec} span.text-sm").inner_text() == "Follow us")
    # handle with markup stays inside the attribute
    s.open("logo-social-xss", [comp("logo-social")], store={"name": "S", "settings": {"contact": {"instagram": 'a" onmouseover="window.__pwn=1'}}})
    s.check(checks, "handle_cannot_break_attribute", js(page, "document.querySelector('.section-logo-social a').hasAttribute('onmouseover')"), not js(page, "document.querySelector('.section-logo-social a').hasAttribute('onmouseover')"))
    # the section's own logo branch reads settings the section schema does not declare
    s.open("logo-social-settings-logo", [comp("logo-social", logo_logo_desktop=img("sec-d"), logo_logo_mobile=img("sec-m"))], store={"name": "S", "logo": "store-logo", "settings": {"contact": {}}})
    checks["undeclared_logo_settings_honoured_if_injected"] = page.locator(f"{sec} img").count()
    return s.verdict(checks)


JOURNEYS = {
    "home-sections-live-home": live_home,
    "home-sections-hero": hero,
    "home-sections-carousel": carousel,
    "home-sections-categories": categories,
    "home-sections-products": products,
    "home-sections-testimonials": testimonials,
    "home-sections-partners": partners,
    "home-sections-gallery": gallery,
    "home-sections-video": video,
    "home-sections-countdown": countdown,
    "home-sections-benefits": benefits,
    "home-sections-call-to-action": call_to_action,
    "home-sections-logo-social": logo_social,
}

# Recorded product bugs (drive.py exits 0 with FINDING while exactly these checks fail). Vitrin renders
# .jinja with select_autoescape() (sdk/jinja.py), so autoescape is OFF: merchant text in section
# settings, category names and store contact handles reaches the page as HTML.
_UNESCAPED = "vitrin renders .jinja without autoescape: merchant text in this section is written as HTML"
KNOWN = {
    "home-sections-hero": ({"D_no_injected_img", "D_no_script_ran", "D_heading_literal"}, _UNESCAPED),
    "home-sections-call-to-action": ({"heading_not_html", "style_attr_cannot_be_broken"}, _UNESCAPED),
    "home-sections-categories": ({"name_escaped", "name_literal"}, _UNESCAPED),
    "home-sections-benefits": ({"title_escaped"}, _UNESCAPED),
    "home-sections-testimonials": ({"xss_text_not_executed", "name_escaped"}, _UNESCAPED),
    "home-sections-video": ({"title_escaped"}, _UNESCAPED),
    "home-sections-logo-social": ({"store_name_alt_not_html", "handle_cannot_break_attribute"}, _UNESCAPED),
    "home-sections-countdown": (
        {"garbage_content_hidden", "garbage_cannot_inject_js"},
        "countdown end_date is written raw into new Date(\"...\"): a quote in it breaks out and runs script",
    ),
}
