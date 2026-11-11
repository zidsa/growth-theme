"""DOM-level properties for the search/category group JS modules.

Imports the real source modules (assets/js/features/*.js) into a bare Chromium
page with a fixture built from the templates' own markup, then drives them the
way the theme drives them. Any module that needs a bare import (price-slider ->
nouislider) gets that import resolved to the same file the bundle uses, exactly
as vite does at build time.

Run: uv run --no-project --with playwright python -I browser.py [--root DIR]
Prints one `PROP <id> PASS|FAIL` line per property.
"""

import argparse
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME = os.environ.get(
    "CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)

FIXTURE = """<!doctype html>
<html dir="rtl" lang="ar">
<head><meta charset="utf-8"><title>fixture</title></head>
<body>
  <dialog id="filters-drawer"></dialog>
  <div id="products-content"></div>

  <div data-search-results class="hidden">
    <div data-search-products></div>
    <div data-search-loading class="hidden"></div>
    <div data-search-empty class="hidden"></div>
  </div>

  <form id="drawer-form" method="GET" action="">
    <input type="hidden" name="sort_by" value="popularity_order">
    <input type="hidden" name="order" value="asc">
    <label><input type="checkbox" name="availability" value="in_stock"></label>
    <label><input type="checkbox" name="attributes[ar-اللون-en-2][]" value="ابيض"></label>
    <label><input type="checkbox" name="attributes[ar-اللون-en-2][]" value="أسود"></label>
    <label><input type="checkbox" name="attributes[ar-الماركة-en-brand][]" value="جري"></label>
    <input type="text" id="form_from_price" name="from_price">
    <input type="text" id="form_to_price" name="to_price">
    <input type="radio" name="sort_option" value="price-asc">
  </form>

  <div id="slider-host"></div>
</body></html>"""



def source(root: Path, rel: str) -> str:
    return (root / rel).read_text()


def module_url(page, code: str) -> str:
    """Make an ES module out of `code` and return a URL the page can import."""
    return page.evaluate(
        """(code) => URL.createObjectURL(new Blob([code], {type: "text/javascript"}))""",
        code,
    )


def price_slider_module(page, root: Path):
    """price-slider.js with its bare `nouislider` import pointed at node_modules."""
    noui = source(root, "node_modules/nouislider/dist/nouislider.mjs")
    noui_url = module_url(page, noui)
    code = source(root, "assets/js/features/price-slider.js").replace(
        'from "nouislider"', f'from "{noui_url}"'
    )
    return module_url(page, code)


# ── property: product search results never turn text into markup ────────────

def prop_search_escape(page, root: Path):
    import_url = module_url(page, source(root, "assets/js/features/search.js"))
    return page.evaluate(
        """async (url) => {
        const problems = [];
        const mod = await import(url);
        const SearchManager = mod.default;
        const sm = new SearchManager();
        sm.productsContainer = document.querySelector("[data-search-products]");
        sm.resultsContainer = document.querySelector("[data-search-results]");
        sm.loadingContainer = document.querySelector("[data-search-loading]");
        sm.emptyContainer = document.querySelector("[data-search-empty]");

        const evil = 'x" onerror="window.__pwned=1';
        const products = [
          {id: "1", url: "/products/a?x=1", image: "https://img.test/a.jpg",
           name: evil, price: "10.00 SAR", salePrice: null, hasOptions: false,
           rating: null, badges: [evil]},
          {id: "2", url: "/products/b", image: null,
           name: "منتج <b>عادي</b>", price: "20.00 SAR", salePrice: "15.00 SAR",
           hasOptions: true, rating: {average: 4.5, total_count: 3}, badges: []},
        ];
        sm.showResults(products);

        const box = document.querySelector("[data-search-products]");
        const anchors = [...box.querySelectorAll("a")];
        if (anchors.length !== products.length)
          problems.push(`${anchors.length} result cards for ${products.length} products`);
        if (box.querySelectorAll("[onerror]").length)
          problems.push("a product field created an onerror attribute");
        if (box.querySelectorAll("img[onerror], script").length)
          problems.push("a product field created an element");

        const first = anchors[0];
        const alt = first?.querySelector("img")?.getAttribute("alt");
        if (alt !== evil) problems.push(`img alt=${JSON.stringify(alt)} != name`);
        const h3 = first?.querySelector("h3")?.textContent;
        if (h3 !== evil) problems.push(`name rendered as ${JSON.stringify(h3)}`);
        const badge = first?.querySelector("span.rounded")?.textContent;
        if (badge !== evil) problems.push(`badge rendered as ${JSON.stringify(badge)}`);

        const second = anchors[1];
        const h3b = second?.querySelector("h3")?.textContent ?? "";
        if (h3b !== products[1].name)
          problems.push(`second name rendered as ${JSON.stringify(h3b)}`);
        if (second?.querySelector("img")) problems.push("image rendered for a product without one");
        if (window.__pwned) problems.push("product name executed script");
        return problems;
      }""",
        import_url,
    )


# ── property: the price slider always shows the interval in its inputs ──────

def prop_price_slider(page, root: Path):
    mod = price_slider_module(page, root)
    pairs = ["", "0", "50", "100", "5000", "20000", "99999"]
    return page.evaluate(
        """async ([url, pairs]) => {
        const problems = [];
        const mod = await import(url);
        const MIN = 0, MAX = 20000;
        const host = document.getElementById("slider-host");
        const clamp = (v) => Math.min(Math.max(v, MIN), MAX);

        for (const from of pairs) {
          for (const to of pairs) {
            const q = new URLSearchParams();
            if (from !== "") q.set("from_price", from);
            if (to !== "") q.set("to_price", to);
            history.replaceState(null, "", "/products" + (q.toString() ? "?" + q : ""));

            host.innerHTML = `<div id="price-slider" data-price-slider data-min-input="price_min_drawer" data-max-input="price_max_drawer" data-min-price="0" data-max-price="20000"></div>
              <input type="text" id="price_min_drawer" name="from_price">
              <input type="text" id="price_max_drawer" name="to_price">`;
            mod.initPriceSliders();

            const el = document.getElementById("price-slider");
            const minIn = document.getElementById("price_min_drawer");
            const maxIn = document.getElementById("price_max_drawer");
            const got = el.noUiSlider.get().map(Number);
            const a = minIn.value === "" ? MIN : clamp(Number(minIn.value.replace(/,/g, "")));
            const b = maxIn.value === "" ? MAX : clamp(Number(maxIn.value.replace(/,/g, "")));
            const want = [Math.min(a, b), Math.max(a, b)];
            const tag = `from_price=${from || "-"} to_price=${to || "-"}`;
            if (got[0] > got[1]) problems.push(`${tag}: handles crossed ${JSON.stringify(got)}`);
            if (got[0] !== want[0] || got[1] !== want[1])
              problems.push(`${tag}: handles ${JSON.stringify(got)} != the boxes ${JSON.stringify([a, b])} (${minIn.value}|${maxIn.value})`);
            el.noUiSlider.destroy();
          }
        }

        // dragging the boxes: typing a value moves the matching handle
        history.replaceState(null, "", "/products");
        host.innerHTML = `<div id="price-slider" data-price-slider data-min-input="price_min_drawer" data-max-input="price_max_drawer" data-min-price="0" data-max-price="20000"></div>
          <input type="text" id="price_min_drawer" name="from_price">
          <input type="text" id="price_max_drawer" name="to_price">`;
        mod.initPriceSliders();
        const el = document.getElementById("price-slider");
        const maxIn = document.getElementById("price_max_drawer");
        maxIn.value = "3,000";
        maxIn.dispatchEvent(new Event("change"));
        const after = el.noUiSlider.get().map(Number);
        if (after[1] !== 3000 || after[0] !== 0)
          problems.push(`typing 3,000 in To left handles ${JSON.stringify(after)}`);
        el.noUiSlider.destroy();
        return problems;
      }""",
        [mod, pairs],
    )


# ── property: Apply applies exactly the fields the drawer shows ─────────────

def prop_filter_form(page, root: Path):
    mod = module_url(page, source(root, "assets/js/features/product-filter.js"))
    cases = [
        {
            "name": "price set, no attribute",
            "url": "/brands/acme",
            "fill": {"from_price": "100", "to_price": ""},
            "checked": [],
            "want": {"from_price": "100", "sort_by": "popularity_order", "order": "asc"},
            "absent": ["to_price"],
        },
        {
            "name": "price box cleared",
            "url": "/brands/acme?from_price=100",
            "fill": {"from_price": "", "to_price": ""},
            "checked": [],
            "want": {"sort_by": "popularity_order", "order": "asc"},
            "absent": ["from_price", "to_price"],
        },
        {
            "name": "attributes + availability + sort radio",
            "url": "/brands/acme",
            "fill": {"from_price": "", "to_price": ""},
            "checked": ["ابيض", "أسود", "in_stock"],
            "pick_radio": True,
            "want": {
                "attributes[ar-اللون-en-2][]": ["ابيض", "أسود"],
                "availability": "in_stock",
                "sort_by": "popularity_order",
                "order": "asc",
            },
            "absent": ["sort_option", "from_price"],
        },
        {
            "name": "nothing changed keeps q, drops page",
            "url": "/brands/acme?page=3&q=x",
            "fill": {"from_price": "", "to_price": ""},
            "checked": [],
            "want": {"q": "x", "sort_by": "popularity_order", "order": "asc"},
            "absent": ["page"],
        },
    ]
    return page.evaluate(
        """async ([url, cases]) => {
        const problems = [];
        const { ProductFilter } = await import(url).then((m) => ({ ProductFilter: m.default }));
        window.fetch = async () => new Response('<div id="products-content"></div>', {status: 200});
        const form = document.getElementById("drawer-form");

        for (const c of cases) {
          history.replaceState(null, "", c.url);
          for (const box of form.querySelectorAll("input[type=checkbox]")) {
            box.checked = c.checked.includes(box.value);
          }
          const radio = form.querySelector("input[name=sort_option]");
          radio.checked = !!c.pick_radio;
          for (const [k, v] of Object.entries(c.fill)) {
            form.querySelector(`[name=${k}]`).value = v;
          }
          const pf = new ProductFilter();
          await pf.submitDrawerForm({preventDefault() {}, target: form});
          const params = new URLSearchParams(location.search);
          for (const [k, v] of Object.entries(c.want)) {
            const got = params.getAll(k);
            const want = Array.isArray(v) ? v : [v];
            if (JSON.stringify(got) !== JSON.stringify(want))
              problems.push(`${c.name}: ${k}=${JSON.stringify(got)} != ${JSON.stringify(want)} (${location.search})`);
          }
          for (const k of c.absent) {
            if (params.has(k)) problems.push(`${c.name}: ${k} should be gone, got ${params.get(k)} (${location.search})`);
          }
        }
        return problems;
      }""",
        [mod, cases],
    )


PROPS = {
    "search-escape": prop_search_escape,
    "price-slider-order": prop_price_slider,
    "filter-form-url": prop_filter_form,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if not (root / "assets/js/features/search.js").exists():
        sys.exit(f"CHANGED harness: {root} is not a growth-theme checkout")

    failed = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        ctx = browser.new_context(locale="ar-SA", viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        # A real origin (about:blank cannot push history state), served from memory.
        page.route(
            "https://fixture.test/**",
            lambda r: r.fulfill(body=FIXTURE, content_type="text/html; charset=utf-8"),
        )

        def fresh():
            errors.clear()
            page.goto("https://fixture.test/products", wait_until="load")

        for name, fn in PROPS.items():
            if args.only and args.only != name:
                continue
            fresh()  # every property starts from a clean document
            try:
                problems = fn(page, root)
            except Exception as exc:
                print(f"PROP {name} ERROR")
                print(f"  harness error: {exc!r}")
                failed += 1
                continue
            if errors:
                problems = list(problems) + [f"page error: {errors.pop(0)}"]
            print(f"PROP {name} {'FAIL' if problems else 'PASS'}")
            for pr in list(problems)[:12]:
                print(f"  - {pr}")
            failed += bool(problems)
        browser.close()
    sys.exit(0 if not failed else 0)  # check.sh reads the PROP lines


if __name__ == "__main__":
    main()
