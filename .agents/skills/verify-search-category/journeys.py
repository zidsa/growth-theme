"""Shopper journeys for the search-category group (products, category, brands, search, filters).

drive.py loads JOURNEYS from every verify-*/journeys.py:
    uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py search-category-products

Every journey takes (page, base, out, checks) and returns True when the promise
it states holds. `checks` is written to summary.json verbatim, so put the numbers
you compared in it.
"""

import re
from urllib.parse import urlsplit, parse_qsl, urlencode

AJAX = "XMLHttpRequest"


# ── helpers ─────────────────────────────────────────────────────────────────

def _count_line(page):
    """The products-header "N out of M products" line as [N, M] (or None)."""
    return page.evaluate(
        """() => {
        for (const s of document.querySelectorAll('#products-content span')) {
          const t = s.textContent.replace(/\\s+/g, ' ').trim();
          const m = t.match(/^(\\d+)\\s*(?:out of|من)\\s*(\\d+)/);
          if (m && /product|منتج/i.test(t)) return [Number(m[1]), Number(m[2])];
        }
        return null;
      }"""
    )


def _cards(page):
    """One entry per product card: {href, id}."""
    return page.evaluate(
        """() => [...document.querySelectorAll('[data-product-card]')].map((c) => {
          const a = c.querySelector('a[href]');
          return {id: c.getAttribute('data-product-card'), href: a && a.getAttribute('href')};
        })"""
    )


def _paths(cards):
    return [urlsplit(c["href"] or "").path for c in cards]


def _api(page, base, path) -> dict:
    r = page.request.get(base + path)
    if not r.ok:
        return {"_status": r.status}
    return r.json()


def _api_list(page, base, path) -> list:
    r = page.request.get(base + path)
    if not r.ok:
        return []
    body = r.json()
    return body if isinstance(body, list) else body.get("results", [])


def _api_for_page(page, base, extra=None) -> dict:
    """The listing API answer for the filters the page shows (+ scope the page adds server-side).

    A brand page sets `brand=<uuid>` on the API call from its route, not from the
    query string, so journeys on a brand page pass it in `extra`.
    """
    query = dict(parse_qsl(urlsplit(page.url).query))
    query.update(extra or {})
    return _api(page, base, "/api/v1/products?" + urlencode(query, doseq=True))


def _brand_id(page, base, slug):
    body = _api(page, base, "/api/v1/brands?page_size=100")
    for b in body.get("results", []):
        if b["slug"] == slug:
            return b["id"]
    return None


def _chips(page):
    return page.evaluate(
        """() => [...document.querySelectorAll('button.badge[data-filter-type]')].map((b) => ({
          type: b.dataset.filterType, slug: b.dataset.filterSlug, value: b.dataset.filterValue,
          text: b.textContent.replace(/\\s+/g, ' ').trim()}))"""
    )


def _open_drawer(page):
    page.evaluate(
        """() => {
        const b = [...document.querySelectorAll('button[commandfor="filters-drawer"]')]
          .find((e) => e.offsetParent !== null);
        if (b) b.click();
      }"""
    )
    page.wait_for_function("() => document.getElementById('filters-drawer')?.open === true", timeout=10000)


def _apply(page, base):
    """Submit the drawer and wait for the AJAX re-render it triggers."""
    with page.expect_response(
        lambda r: r.url.startswith(base) and r.request.headers.get("x-requested-with") == AJAX,
        timeout=20000,
    ) as seen:
        page.evaluate("() => document.querySelector('#filters-drawer button[type=submit]').click()")
    page.wait_for_timeout(400)
    return seen.value.status


def _pick_sort(page, base, value):
    page.locator("#sort-select button").first.click()
    page.wait_for_timeout(300)
    with page.expect_response(
        lambda r: r.url.startswith(base) and r.request.headers.get("x-requested-with") == AJAX,
        timeout=20000,
    ) as seen:
        page.locator(f'#sort-select el-option[value="{value}"]').first.click()
    page.wait_for_timeout(400)
    return seen.value.status


def _marker(page):
    page.evaluate("() => { window.__verifyMarker = 'kept'; }")


def _marker_kept(page):
    return page.evaluate("() => window.__verifyMarker === 'kept'")


def _goto(page, url):
    resp = page.goto(url, wait_until="load")
    page.wait_for_timeout(300)
    return resp


# ── products listing ────────────────────────────────────────────────────────

def products(page, base, out, checks):
    """All-products page: 24 cards, the header total equals the API, paging works."""
    _goto(page, base + "/products")
    checks["url"] = page.url
    cards = _cards(page)
    checks["cards_page1"] = len(cards)
    checks["count_line_page1"] = _count_line(page)
    api = _api(page, base, "/api/v1/products?page_size=1")
    checks["api_count"] = api.get("count")
    page.screenshot(path=out / "1-products.png", full_page=False)
    first_page = _paths(cards)

    # next page: a plain link, so the page reloads
    next_link = page.locator('#product-pagination a[data-slot="pagination-next"]').first
    checks["next_href"] = next_link.get_attribute("href")
    next_link.click()
    page.wait_for_url(re.compile(r"[?&]page=2(&|$)"), timeout=15000)
    page.wait_for_load_state("load")
    page.wait_for_timeout(300)
    cards2 = _cards(page)
    checks["cards_page2"] = len(cards2)
    checks["count_line_page2"] = _count_line(page)
    checks["current_page"] = page.evaluate(
        """() => {const e = document.querySelector('#product-pagination [aria-current="page"]');
                  return e ? e.textContent.trim() : null}"""
    )
    checks["overlap"] = len(set(first_page) & set(_paths(cards2)))
    page.screenshot(path=out / "2-page-2.png")

    line = checks["count_line_page1"]
    return (
        checks["cards_page1"] == 24
        and bool(line) and line[0] == checks["cards_page1"] and line[1] == checks["api_count"]
        and checks["cards_page2"] == 24
        and checks["current_page"] == "2"
        and checks["overlap"] == 0
    )


def per_page(page, base, out, checks):
    """Changing 'products on page' re-renders without leaving the page."""
    _goto(page, base + "/products")
    _marker(page)
    page.locator("#per-page-select button").first.click()
    page.wait_for_timeout(300)
    with page.expect_response(
        lambda r: r.url.startswith(base) and r.request.headers.get("x-requested-with") == AJAX,
        timeout=20000,
    ) as seen:
        page.locator('#per-page-select el-option[value="12"]').first.click()
    page.wait_for_timeout(500)
    checks["ajax_status"] = seen.value.status
    checks["url"] = page.url
    checks["page_size_param"] = dict(parse_qsl(urlsplit(page.url).query)).get("page_size")
    checks["cards"] = len(_cards(page))
    checks["count_line"] = _count_line(page)
    checks["stayed_on_page"] = _marker_kept(page)
    page.screenshot(path=out / "per-page-12.png")
    return (
        checks["ajax_status"] == 200
        and checks["page_size_param"] == "12"
        and checks["cards"] == 12
        and checks["stayed_on_page"]
    )


# ── filters ─────────────────────────────────────────────────────────────────

def filter_attribute(page, base, out, checks):
    """Ticking one attribute in the drawer filters the grid in place, and its chip removes it."""
    _goto(page, base + "/brands/thumbsup")
    checks["cards_before"] = len(_cards(page))
    _marker(page)
    _open_drawer(page)
    box = page.evaluate(
        """() => {
        const i = document.querySelector('#filters-drawer input[type=checkbox][name^="attributes"]');
        if (!i) return null;
        i.click();
        return {name: i.name, value: i.value, checked: i.checked,
                label: i.closest('label')?.textContent.trim()};
      }"""
    )
    checks["picked"] = box
    if not box:
        return False
    checks["apply_status"] = _apply(page, base)
    checks["drawer_closed"] = page.evaluate("() => !document.getElementById('filters-drawer')?.open")
    checks["url"] = page.url
    params = dict(parse_qsl(urlsplit(page.url).query))
    checks["url_param"] = params.get(box["name"])
    checks["chips"] = _chips(page)
    checks["stayed_on_page"] = _marker_kept(page)
    checks["brand_id"] = _brand_id(page, base, "thumbsup")
    api = _api_for_page(page, base, {"brand": checks["brand_id"]})
    checks["api_count"] = api.get("count")
    checks["cards_after"] = len(_cards(page))
    checks["count_line"] = _count_line(page)
    page.screenshot(path=out / "1-filtered.png")

    ok = (
        checks["apply_status"] == 200
        and checks["drawer_closed"]
        and checks["url_param"] == box["value"]
        and any(c["type"] == "attribute" and c["value"] == box["value"] for c in checks["chips"])
        and checks["stayed_on_page"]
        and checks["count_line"] is not None
        and checks["count_line"][0] == checks["cards_after"]
        and checks["count_line"][1] == checks["api_count"]
    )

    # the chip's X must remove exactly that filter
    if checks["chips"]:
        with page.expect_response(
            lambda r: r.url.startswith(base) and r.request.headers.get("x-requested-with") == AJAX,
            timeout=20000,
        ):
            page.locator('button.badge[data-filter-type="attribute"]').first.click()
        page.wait_for_timeout(400)
        checks["url_after_remove"] = page.url
        checks["cards_after_remove"] = len(_cards(page))
        checks["chips_after_remove"] = _chips(page)
        checks["param_after_remove"] = dict(parse_qsl(urlsplit(page.url).query)).get(box["name"])
        page.screenshot(path=out / "2-chip-removed.png")
        ok = (
            ok
            and checks["param_after_remove"] is None
            and checks["cards_after_remove"] == checks["cards_before"]
            and not checks["chips_after_remove"]
        )
    return ok


def filter_zero_results(page, base, out, checks):
    """A filter that matches nothing still leaves the shopper a way to relax it."""
    _goto(page, base + "/brands/thumbsup")
    checks["cards_before"] = len(_cards(page))
    _open_drawer(page)
    page.evaluate(
        """() => {
        const i = document.getElementById('price_min_drawer');
        i.value = '1000000';
        i.dispatchEvent(new Event('input', {bubbles: true}));
        i.dispatchEvent(new Event('change', {bubbles: true}));
      }"""
    )
    checks["apply_status"] = _apply(page, base)
    checks["url"] = page.url
    checks["cards"] = len(_cards(page))
    checks["count_line"] = _count_line(page)
    checks["empty_text"] = page.evaluate(
        """() => {const p = [...document.querySelectorAll('#products-content p')]
                    .find((e) => /No products|لا توجد/.test(e.textContent));
                  return p ? p.textContent.trim() : null}"""
    )
    checks["filter_button_present"] = page.evaluate(
        """() => [...document.querySelectorAll('button[commandfor="filters-drawer"]')]
                   .some((b) => b.offsetParent !== null)"""
    )
    checks["drawer_present"] = page.evaluate("() => !!document.getElementById('filters-drawer')")
    page.screenshot(path=out / "1-zero-results.png", full_page=False)
    conds = {
        "apply_ok": checks["apply_status"] == 200,
        "zero_cards": checks["cards"] == 0,
        "drawer_present": checks["drawer_present"],
        "filter_button_present": checks["filter_button_present"],
    }
    checks["failed_checks"] = [k for k, ok in conds.items() if not ok]
    return not checks["failed_checks"]


def filter_price(page, base, out, checks):
    """A price range typed in the drawer becomes from_price/to_price and filters the grid."""
    _goto(page, base + "/products")
    _open_drawer(page)
    page.evaluate(
        """() => {
        const set = (id, v) => {const i = document.getElementById(id);
          i.value = v; i.dispatchEvent(new Event('input', {bubbles: true}));
          i.dispatchEvent(new Event('change', {bubbles: true}));};
        set('price_min_drawer', '100');
        set('price_max_drawer', '500');
      }"""
    )
    checks["slider_handles"] = page.evaluate(
        """() => {const s = document.querySelector('[data-price-slider]');
                  return s && s.noUiSlider ? s.noUiSlider.get() : null}"""
    )
    checks["apply_status"] = _apply(page, base)
    checks["url"] = page.url
    q = dict(parse_qsl(urlsplit(page.url).query))
    checks["from_price"], checks["to_price"] = q.get("from_price"), q.get("to_price")
    checks["chips"] = _chips(page)
    api = _api_for_page(page, base)
    checks["api_count"] = api.get("count")
    checks["cards"] = len(_cards(page))
    checks["count_line"] = _count_line(page)
    page.screenshot(path=out / "1-price-filtered.png")
    line = checks["count_line"]
    return (
        checks["apply_status"] == 200
        and checks["from_price"] == "100"
        and checks["to_price"] == "500"
        and line is not None
        and line[0] == checks["cards"]
        and line[1] == checks["api_count"]
        and any(c["type"] == "price" for c in checks["chips"])
    )


def filter_price_clear(page, base, out, checks):
    """Clearing the price boxes removes the price filter (from_price/to_price leave the URL)."""
    _goto(page, base + "/products?from_price=100&to_price=500")
    checks["cards_before"] = len(_cards(page))
    checks["chips_before"] = _chips(page)
    _open_drawer(page)
    checks["inputs_before"] = page.evaluate(
        """() => [document.getElementById('price_min_drawer').value,
                  document.getElementById('price_max_drawer').value]"""
    )
    page.evaluate(
        """() => {
        for (const id of ['price_min_drawer', 'price_max_drawer']) {
          const i = document.getElementById(id);
          i.value = '';
          i.dispatchEvent(new Event('input', {bubbles: true}));
          i.dispatchEvent(new Event('change', {bubbles: true}));
        }}"""
    )
    checks["apply_status"] = _apply(page, base)
    checks["url"] = page.url
    q = dict(parse_qsl(urlsplit(page.url).query))
    checks["from_price"], checks["to_price"] = q.get("from_price"), q.get("to_price")
    checks["chips_after"] = _chips(page)
    checks["cards_after"] = len(_cards(page))
    page.screenshot(path=out / "1-price-cleared.png")
    conds = {
        "apply_ok": checks["apply_status"] == 200,
        "from_price_cleared": checks["from_price"] is None,
        "to_price_cleared": checks["to_price"] is None,
        "price_chip_gone": not any(c["type"] == "price" for c in checks["chips_after"]),
    }
    checks["failed_checks"] = [k for k, ok in conds.items() if not ok]
    return not checks["failed_checks"]


def filter_sort(page, base, out, checks):
    """The sort menu re-orders the same filtered grid in place and keeps the other filters."""
    _goto(page, base + "/brands/thumbsup?attributes%5Bar-%D8%A7%D9%84%D9%84%D9%88%D9%86-en-2%5D%5B%5D=%D8%A7%D8%A8%D9%8A%D8%B6")
    checks["url_before"] = page.url
    checks["cards_before"] = len(_cards(page))
    checks["label_before"] = page.evaluate(
        "() => document.querySelector('#sort-select el-selectedcontent')?.textContent.trim()"
    )
    _marker(page)
    checks["sort_status"] = _pick_sort(page, base, "price-desc")
    checks["url"] = page.url
    q = dict(parse_qsl(urlsplit(page.url).query))
    checks["sort_by"], checks["order"] = q.get("sort_by"), q.get("order")
    checks["attribute_kept"] = [v for k, v in parse_qsl(urlsplit(page.url).query) if k.startswith("attributes[")]
    checks["label_after"] = page.evaluate(
        "() => document.querySelector('#sort-select el-selectedcontent')?.textContent.trim()"
    )
    checks["stayed_on_page"] = _marker_kept(page)
    api = _api_for_page(page, base, {"brand": _brand_id(page, base, "thumbsup")})
    checks["api_slugs"] = [p.get("slug") for p in api.get("results", [])][:5]
    checks["rendered_paths"] = [urlsplit(h or "").path.rsplit("/", 1)[-1] for h in
                                [c["href"] for c in _cards(page)]][:5]
    page.screenshot(path=out / "1-sorted.png")
    return (
        checks["sort_status"] == 200
        and checks["sort_by"] == "price"
        and checks["order"] == "desc"
        and checks["attribute_kept"]
        and checks["label_after"] != checks["label_before"]
        and checks["stayed_on_page"]
        and checks["rendered_paths"] == checks["api_slugs"]
    )


# ── search dialog ───────────────────────────────────────────────────────────

def search(page, base, out, checks):
    """Typing in the header search shows live results and hands off to /products?q=..."""
    _goto(page, base + "/products")
    page.locator('button[commandfor="search-dialog"]').first.click()
    page.wait_for_function("() => document.getElementById('search-dialog')?.open === true", timeout=10000)
    _marker(page)
    field = page.locator("[data-search-input]")
    field.fill("منتج")
    page.wait_for_function(
        """() => {
        const r = document.querySelector('[data-search-results]');
        const l = document.querySelector('[data-search-loading]');
        return r && !r.classList.contains('hidden') && l && l.classList.contains('hidden');
      }""",
        timeout=30000,
    )
    page.wait_for_timeout(200)
    checks["results"] = page.evaluate(
        """() => [...document.querySelectorAll('[data-search-products] a')]
                   .map((a) => a.getAttribute('href'))"""
    )
    checks["empty_hidden"] = page.evaluate(
        "() => document.querySelector('[data-search-empty]').classList.contains('hidden')"
    )
    checks["all_link"] = page.evaluate(
        """() => {const a = document.querySelector('[data-search-all-link]');
                  return a ? {href: a.getAttribute('href'), text: a.textContent.trim().replace(/\\s+/g, ' ')} : null}"""
    )
    checks["stayed_on_page"] = _marker_kept(page)
    page.screenshot(path=out / "1-search-results.png")

    ok = (
        len(checks["results"]) > 0
        and len(checks["results"]) <= 8
        and all("/products/" in (h or "") for h in checks["results"])
        and checks["empty_hidden"]
        and checks["all_link"] is not None
        and "منتج" in checks["all_link"]["text"]
        and checks["all_link"]["href"] == base + "/products?q=%D9%85%D9%86%D8%AA%D8%AC"
        and checks["stayed_on_page"]
    )

    # the "search for ..." link lands on the listing filtered by q
    page.locator("[data-search-all-link]").click()
    page.wait_for_url(re.compile(r"/products\?.*q="), timeout=15000)
    page.wait_for_load_state("load")
    page.wait_for_timeout(300)
    checks["url"] = page.url
    checks["count_line"] = _count_line(page)
    checks["cards"] = len(_cards(page))
    api = _api_for_page(page, base)
    checks["api_count"] = api.get("count")
    checks["first_result_paths"] = [urlsplit(c["href"] or "").path for c in _cards(page)][:3]
    page.screenshot(path=out / "2-search-page.png")
    return (
        ok
        and checks["cards"] > 0
        and checks["count_line"] is not None
        and checks["count_line"][1] == checks["api_count"]
        and checks["count_line"][0] == checks["cards"]
    )


# ── categories and brands listings ──────────────────────────────────────────

def categories(page, base, out, checks):
    """The categories page: one card per category, carousels only for parents, cards lead to their category."""
    api = _api_list(page, base, "/api/v1/categories")
    by_id = {str(c["id"]): c for c in api}
    parents = [c for c in api if c.get("sub_categories")]
    checks["api_categories"] = len(api)
    checks["api_parents_with_children"] = len(parents)

    _goto(page, base + "/categories")
    page.wait_for_timeout(500)
    checks["h1"] = page.evaluate("() => [...document.querySelectorAll('h1')].map((h) => h.textContent.trim())")
    cards = page.evaluate(
        """() => [...document.querySelectorAll('div.grid > a[href*="/categories/"]')]
                   .map((a) => ({href: a.getAttribute('href'), name: a.querySelector('h3')?.textContent.trim()}))"""
    )
    checks["cards"] = len(cards)
    checks["carousels"] = page.evaluate("() => document.querySelectorAll('[data-subcategories-carousel]').length")
    checks["unique_carousel_ids"] = page.evaluate(
        "() => new Set([...document.querySelectorAll('[data-subcategories-carousel]')].map((e) => e.dataset.subcategoriesCarousel)).size"
    )
    sample = []
    for card in cards[:12]:
        cid = urlsplit(card["href"]).path.split("/")[2]
        want = by_id.get(cid)
        sample.append(
            {
                "href": card["href"],
                "id_matches": bool(want) and card["name"] == want["name"],
                "slug_matches": bool(want) and urlsplit(card["href"]).path.endswith("/" + want["slug"]),
            }
        )
    checks["sample"] = sample
    page.screenshot(path=out / "1-categories.png")

    # a subcategory slide opens that subcategory's own page
    first_parent = parents[0]
    first_child = first_parent["sub_categories"][0]
    checks["clicked"] = {"parent": first_parent["name"], "child": first_child["name"]}
    slide = page.locator(f'[data-subcategories-carousel="subcategories-{first_parent["id"]}"] .subcategories-embla__slide a').first
    slide.click()
    page.wait_for_load_state("load")
    page.wait_for_timeout(300)
    checks["child_url"] = page.url
    checks["child_h1"] = page.evaluate("() => document.querySelector('h1')?.textContent.trim()")
    checks["breadcrumb"] = page.evaluate(
        """() => [...document.querySelectorAll('nav[aria-label="breadcrumb"] li')]
                   .map((li) => li.textContent.trim()).filter(Boolean)"""
    )
    page.screenshot(path=out / "2-subcategory.png")
    return (
        checks["cards"] == checks["api_categories"]
        and checks["carousels"] == checks["api_parents_with_children"]
        and checks["unique_carousel_ids"] == checks["carousels"]
        and len(checks["h1"]) == 1
        and all(s["id_matches"] and s["slug_matches"] for s in sample)
        and checks["child_h1"] == first_child["name"]
        and any(first_parent["name"] in crumb for crumb in checks["breadcrumb"])
    )


def brands(page, base, out, checks):
    """The brands page: one card per brand, paging, and a card opens that brand's products."""
    api = _api(page, base, "/api/v1/brands?page_size=24")
    checks["api_count"] = api.get("count")
    checks["api_page1"] = [b["slug"] for b in api.get("results", [])]

    _goto(page, base + "/brands")
    cards = page.evaluate(
        """() => [...document.querySelectorAll('div.grid > a[href*="/brands/"]')]
                   .map((a) => ({href: a.getAttribute('href'), name: a.querySelector('h3')?.textContent.trim()}))"""
    )
    checks["cards_page1"] = len(cards)
    checks["slugs_page1"] = [urlsplit(c["href"]).path.split("/")[-1] for c in cards]
    checks["names_match"] = all(
        c["name"].startswith(b["display_name"] or b["name"])
        for c, b in zip(cards, api.get("results", []))
    )
    page.screenshot(path=out / "1-brands.png")

    page.locator('#product-pagination a[data-slot="pagination-next"]').first.click()
    page.wait_for_url(re.compile(r"[?&]page=2(&|$)"), timeout=15000)
    page.wait_for_load_state("load")
    page.wait_for_timeout(300)
    cards2 = page.evaluate(
        """() => [...document.querySelectorAll('div.grid > a[href*="/brands/"]')].map((a) => a.getAttribute('href'))"""
    )
    checks["cards_page2"] = len(cards2)
    checks["api_remaining"] = checks["api_count"] - checks["cards_page1"]

    page.goto(base + "/brands/thumbsup", wait_until="load")
    page.wait_for_timeout(300)
    checks["brand_url"] = page.url
    checks["brand_heading"] = page.evaluate("() => document.querySelector('#products-content h2')?.textContent.replace(/\\s+/g, ' ').trim()")
    checks["brand_cards"] = len(_cards(page))
    checks["brand_breadcrumb"] = page.evaluate(
        """() => [...document.querySelectorAll('nav[aria-label="breadcrumb"] li')]
                   .map((li) => li.textContent.trim()).filter(Boolean)"""
    )
    page.screenshot(path=out / "2-brand.png")

    # a product of this brand links back to the brand above its title
    page.locator('[data-product-card] a[href*="/products/"]').first.click()
    page.wait_for_load_state("load")
    page.wait_for_timeout(400)
    checks["product_url"] = page.url
    checks["product_brand"] = page.evaluate(
        """() => {const a = [...document.querySelectorAll('a[href$="/brands/thumbsup"]')]
                     .find((e) => e.querySelector("img, span"));
                   return a ? {href: a.getAttribute("href"), text: a.textContent.trim(),
                               label: a.getAttribute("aria-label"), img: !!a.querySelector("img")} : null}"""
    )
    page.screenshot(path=out / "3-product-brand.png")
    return (
        checks["cards_page1"] == len(checks["api_page1"])
        and checks["slugs_page1"] == checks["api_page1"]
        and checks["names_match"]
        and checks["cards_page2"] == checks["api_remaining"]
        and checks["brand_cards"] == 5
        and "THUMBSUP" in (checks["brand_heading"] or "")
        and "thumbsup" in checks["brand_breadcrumb"]
        and "/auth/login" not in checks["product_url"]
        and checks["product_brand"] is not None
        and "thumbsup" in (checks["product_brand"]["label"] or checks["product_brand"]["text"]).lower()
    )


JOURNEYS = {
    "search-category-products": products,
    "search-category-per-page": per_page,
    "search-category-filter-attribute": filter_attribute,
    "search-category-filter-price": filter_price,
    "search-category-filter-price-clear": filter_price_clear,
    "search-category-filter-zero": filter_zero_results,
    "search-category-sort": filter_sort,
    "search-category-search": search,
    "search-category-categories": categories,
    "search-category-brands": brands,
}

# Recorded product bugs (drive.py exits 0 with FINDING while exactly these checks fail).
KNOWN = {
    "search-category-filter-price-clear": (
        {"from_price_cleared", "to_price_cleared", "price_chip_gone"},
        "clearing the price filter keeps from_price/to_price in the URL and the price chip",
    ),
    "search-category-filter-zero": (
        {"drawer_present", "filter_button_present"},
        "a filter with zero results removes the filter button and drawer, so the shopper cannot undo it",
    ),
}
