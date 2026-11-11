""""Template properties for the search/category group.

Renders the real .jinja files with plain Jinja2 configured the way vitrin renders
them (autoescape OFF for .jinja -- see sdk/jinja.py `select_autoescape()`), then
checks what a shopper's browser would parse.

Run: uv run --no-project --with jinja2 python -I templates.py [--root DIR]
Prints one `PROP <id> PASS|FAIL` line per property, then details.
"""

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from jinja2 import ChainableUndefined, ChoiceLoader, DictLoader, FileSystemLoader, PrefixLoader
from jinja2 import nodes
from jinja2 import select_autoescape
from jinja2.ext import Extension
from jinja2.sandbox import SandboxedEnvironment

BASE = "https://shop.test"


class Stub(ChainableUndefined):
    def __call__(self, *a, **k):
        return Stub()

    def __str__(self):
        return ""


class VitrinTags(Extension):
    """vitrin_head / vitrin_body / template_components / ai_component emit platform markup."""

    tags = {"vitrin_head", "vitrin_body", "template_components", "ai_component"}

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        while parser.stream.current.type != "block_end":
            next(parser.stream)
        return nodes.Output([nodes.TemplateData("")], lineno=lineno)


class QP:
    """The subset of vitrin's session.query_params these templates use."""

    def __init__(self, pairs=()):
        self.pairs = list(pairs)

    def get(self, key, default=None):
        for k, v in self.pairs:
            if k == key:
                return v
        return default

    def getlist(self, key):
        return [v for k, v in self.pairs if k == key]

    def __contains__(self, key):
        return any(k == key for k, _ in self.pairs)

    def __bool__(self):
        return bool(self.pairs)


def url_for(name, **kw):
    """vitrin's url_for for the routes these templates link to."""
    if name == "home":
        return BASE + "/"
    if name == "list_brands":
        return BASE + "/brands"
    if name == "list_categories":
        return BASE + "/categories"
    if name == "category_details":
        return f"{BASE}/categories/{kw['category_id']}/{kw['slug']}"
    return BASE + "/" + name


def make_env(root):
    loader = ChoiceLoader(
        [FileSystemLoader(str(root)), PrefixLoader({"vitrin": DictLoader({})}), DictLoader({})]
    )
    env = SandboxedEnvironment(
        loader=loader,
        undefined=Stub,
        autoescape=select_autoescape(),  # OFF for .jinja, exactly like vitrin
        finalize=lambda v: "" if v is None else v,
        extensions=["jinja2.ext.do", "jinja2.ext.i18n", VitrinTags],
    )
    real = env.get_template

    def get_template(name, *a, **k):
        if isinstance(name, str) and name.startswith("vitrin:"):
            return env.from_string("")
        return real(name, *a, **k)

    env.get_template = get_template
    env.install_null_translations(newstyle=True)
    env.globals.update(
        _=lambda s, *a, **k: s,
        url_for=url_for,
        image_url=lambda src, **k: src,
        store={"name": "Test store", "settings": {}},
    )
    for f in ("asset_url", "money", "format_price", "currency", "tojson_safe", "t"):
        env.filters.setdefault(f, lambda v, *a, **k: v)
    return env


def render(env, template, **ctx):
    ctx.setdefault("store", {"name": "Test store", "settings": {}})
    ctx.setdefault(
        "session",
        {"lang": "en", "currency": "SAR", "query_params": QP(),
         "locale": {"language": {"direction": "ltr"}}},
    )
    return env.get_template(template).render(**ctx)


def path(href):
    return re.sub(r"^https?://[^/]+", "", href or "")


class Cards(HTMLParser):
    """Collect every <a> with its href, nested h3/h4 text and <img> count."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors, self._open, self._tag = [], None, None
        self.h1 = 0
        self.images = []
        self.attrs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.attrs.append(a)
        if tag == "h1":
            self.h1 += 1
        if tag == "a":
            self._open = {"href": a.get("href", ""), "text": "", "imgs": 0,
                          "img_alts": [], "aria": a.get("aria-label")}
        elif tag == "img":
            self.images.append(a)
            if self._open is not None:
                self._open["imgs"] += 1
                self._open["img_alts"].append(a.get("alt"))
        elif tag in ("h3", "h4") and self._open is not None:
            self._tag = tag

    def handle_endtag(self, tag):
        if tag == "a" and self._open is not None:
            self.anchors.append(self._open)
            self._open = None
        elif tag in ("h3", "h4"):
            self._tag = None

    def handle_data(self, data):
        if self._open is not None and self._tag:
            self._open["text"] += data


def parse(html):
    p = Cards()
    p.feed(html)
    return p


def card_anchors(html):
    """Anchors that are cards: they hold an h3/h4 (name under / beside the image)."""
    return [a for a in parse(html).anchors if a["text"].strip()]


def content_region(html):
    """The #products-content block of a listing page (the search dialog lives elsewhere)."""
    i = html.find('id="products-content"')
    if i < 0:
        return html
    rest = html[i:]
    cut = len(rest)
    for marker in ('id="quick-view"', "<script"):
        j = rest.find(marker)
        if 0 <= j < cut:
            cut = j
    return rest[:cut]


def carousel_roots(html):
    """The ids on the carousel root divs only (not the ones inside <style> selectors)."""
    return re.findall(r'\sdata-subcategories-carousel="([^"]+)"', html)


# ── fixtures ────────────────────────────────────────────────────────────────

def category(i, name=None, slug=None, image=None, image_full=None, subs=()):
    return {
        "id": 100 + i,
        "name": name or f"Category {i}",
        "slug": slug or f"category-{i}",
        "image": image,
        "image_full_size": image_full,
        "description": f"About {i}",
        "sub_categories": list(subs),
        "products_count": i,
    }


def brand(i, name=None, display=None, slug=None, logo=None, count=None):
    return {
        "id": f"b{i}",
        "name": name or f"brand{i}",
        "display_name": display,
        "slug": slug or f"brand-{i}",
        "logo": logo,
        "description": None,
        "products_count": count,
    }


def product(i, brand_obj=None):
    return {
        "id": f"p{i}",
        "name": f"Product {i}",
        "slug": f"product-{i}",
        "brand": brand_obj,
        "price": 10.0 + i,
        "formatted_price": f"{10 + i}.00 SAR",
        "images": [],
        "categories": [],
        "in_stock": True,
        "is_infinite": True,
        "has_options": False,
        "selected_product": {"id": f"s{i}", "in_stock": True, "quantity": None, "is_infinite": True},
    }


class Products:
    def __init__(self, results, count=None, page=1, page_size=24, filters=None):
        self.results = results
        self.count = len(results) if count is None else count
        self.page = page
        self.page_size = page_size
        self.filters = filters


# ── properties ──────────────────────────────────────────────────────────────

def prop_cards_own_record(env):
    """Each card links to, and names, its own record."""
    problems = []
    cats = [category(0, "Alpha", "alpha"), category(1, "بيتا", "beta"), category(2, "Gamma", "gamma")]
    grid = "".join(
        render(env, "components/categories/category-card.jinja", category=c, index=i)
        for i, c in enumerate(cats)
    )
    got = [(path(a["href"]), a["text"].strip()) for a in card_anchors(grid)]
    want = [(f"/categories/{c['id']}/{c['slug']}", c["name"]) for c in cats]
    if got != want:
        problems.append(f"category-card: {got} != {want}")

    subs = [category(3, "Sub A", "sub-a", image="https://img/a.jpg"),
            category(4, "Sub B", "sub-b", image_full="https://img/b-full.jpg")]
    slides = "".join(render(env, "components/categories/subcategory-card.jinja", subcategory=s, index=i)
                     for i, s in enumerate(subs))
    got = [(path(a["href"]), a["text"].strip(), a["imgs"]) for a in card_anchors(slides)]
    want = [(f"/categories/{s['id']}/{s['slug']}", s["name"], 1) for s in subs]
    if got != want:
        problems.append(f"subcategory-card: {got} != {want}")
    # image_full_size is the big one; the card must not fall back to the small image
    if "https://img/b-full.jpg" not in slides:
        problems.append("subcategory-card: did not use image_full_size")

    brands = [brand(0, "acme", "ACME", "acme", "https://img/acme.png", 5),
              brand(1, "nomad", None, "nomad", None, 0)]
    html = "".join(render(env, "components/brands/brand-card.jinja", brand=b, index=i)
                   for i, b in enumerate(brands))
    got = [(path(a["href"]), a["text"].split("(")[0].strip(), a["imgs"]) for a in card_anchors(html)]
    want = [("/brands/acme", "ACME", 1), ("/brands/nomad", "nomad", 0)]
    if got != want:
        problems.append(f"brand-card: {got} != {want}")

    # product-brand: nothing without a brand, one link with it
    if render(env, "components/brands/product-brand.jinja", product=product(0)).strip():
        problems.append("product-brand: rendered markup for a product without a brand")
    html = render(env, "components/brands/product-brand.jinja",
                  product=product(1, brand(7, "acme", "ACME", "acme", "https://img/acme.png")))
    links = [a for a in parse(html).anchors]
    if len(links) != 1 or path(links[0]["href"]) != "/brands/acme" or "ACME" not in html:
        problems.append(f"product-brand: {links}")
    return problems


def prop_cards_escape(env):
    """A quote in a merchant name never leaves its attribute."""
    problems = []
    evil = 'x" onerror="alert(1)'
    cases = [
        ("components/categories/category-card.jinja", {"category": category(0, evil, "slug", image="https://img/a.jpg"), "index": 0}, "name"),
        ("components/categories/subcategory-card.jinja", {"subcategory": category(0, evil, "slug", image="https://img/a.jpg"), "index": 0}, "name"),
        ("components/brands/brand-card.jinja", {"brand": brand(0, evil, None, "slug", "https://img/a.png", 1), "index": 0}, "aria/alt"),
        ("components/categories/category-hero.jinja", {"title": evil, "image": "https://img/a.jpg"}, "alt"),
    ]
    for tpl, ctx, where in cases:
        html = render(env, tpl, **ctx)
        alts = [i.get("alt") for i in parse(html).images]
        if not alts:
            problems.append(f"{tpl}: no image rendered (harness case)")
        elif any(a != evil for a in alts):
            problems.append(f"{tpl}: alt={alts[0]!r} != {evil!r} (attribute broke)")
        # an event handler that carries the payload is the injected one; the
        # templates' own onerror="this.style.display='none'" is not
        injected = [
            a for a in parse(html).attrs
            if any(k.startswith("on") and "alert(1)" in str(v) for k, v in a.items())
        ]
        if injected:
            problems.append(f"{tpl}: name text became an event handler: {injected[0]}")
    # product-brand aria-label
    html = render(env, "components/brands/product-brand.jinja",
                  product=product(1, brand(0, evil, evil, "slug", "https://img/a.png")))
    anchors = parse(html).anchors
    if not anchors or anchors[0]["aria"] != evil:
        problems.append(f"product-brand: aria-label={anchors[0]['aria'] if anchors else None!r} != {evil!r}")
    return problems


def prop_hero(env):
    """One <h1> carrying the title; a background image iff one was given."""
    problems = []
    for title, image, want_h1, want_img in [("Shoes", "https://img/x.jpg", 1, 1),
                                            ("Shoes", None, 1, 0),
                                            (None, "https://img/x.jpg", 0, 1)]:
        html = render(env, "components/categories/category-hero.jinja", title=title, image=image)
        p = parse(html)
        if p.h1 != want_h1:
            problems.append(f"hero(title={title!r}, image={bool(image)}): h1={p.h1} != {want_h1}")
        if len(p.images) != want_img:
            problems.append(f"hero(title={title!r}, image={bool(image)}): imgs={len(p.images)} != {want_img}")
        if want_img and title and p.images[0].get("alt") != title:
            problems.append(f"hero: alt={p.images[0].get('alt')!r} != {title!r}")
    return problems


def prop_carousel(env):
    """One slide per subcategory, self-scoped styles, absent when empty."""
    problems = []
    subs = [category(i, f"Sub {i}", f"sub-{i}", image=f"https://img/{i}.jpg") for i in range(3)]
    html = render(env, "components/categories/subcategories-carousel.jinja",
                  subcategories=subs, title="Parent", carousel_id="c-one",
                  more_url=BASE + "/categories/1/parent")
    slides = re.findall(r'class="subcategories-embla__slide"', html)
    if len(slides) != len(subs):
        problems.append(f"slides={len(slides)} != {len(subs)}")
    links = [path(a["href"]) for a in parse(html).anchors if a["text"].strip()]
    want = [f"/categories/{s['id']}/{s['slug']}" for s in subs]
    if [l for l in links if l != "/categories/1/parent"] != want:
        problems.append(f"carousel slide links {links} != {want}")
    if "/categories/1/parent" not in [path(a["href"]) for a in parse(html).anchors]:
        problems.append("carousel: missing the View all link")
    if 'data-subcategories-carousel="c-one"' not in html:
        problems.append("carousel: missing its own data attribute")
    if '[data-subcategories-carousel="c-one"]' not in html:
        problems.append("carousel: <style> does not target its own id")
    if render(env, "components/categories/subcategories-carousel.jinja",
              subcategories=[], carousel_id="c-empty").strip():
        problems.append("carousel: rendered markup for zero subcategories")

    # two carousels on one page must not share ids or style scopes
    page = ""
    for i, cid in enumerate(["c-a", "c-b"]):
        page += render(env, "components/categories/subcategories-carousel.jinja",
                       subcategories=subs, title=f"P{i}", carousel_id=cid)
    ids = carousel_roots(page)
    if ids != ["c-a", "c-b"]:
        problems.append(f"two carousels: root ids {ids}")
    for cid in ("c-a", "c-b"):
        if page.count(f'[data-subcategories-carousel="{cid}"]') < 4:
            problems.append(f"two carousels: style scope for {cid} missing")
    return problems


def prop_listing(env):
    """One card per record; count text and empty state follow the data."""
    problems = []
    pages = [("templates/products.jinja", {}),
             ("templates/brand.jinja", {"brand": brand(0, "acme", "ACME", "acme")}),
             ("templates/category.jinja", {"category": category(0, "Alpha", "alpha")})]
    for tpl, extra in pages:
        for n, total in [(0, 0), (1, 1), (3, 7)]:
            prods = Products([product(i) for i in range(n)], count=total)
            html = render(env, tpl, products=prods, **extra)
            region = content_region(html)
            cards = len(re.findall(r"data-product-card=", region))
            if cards != n:
                problems.append(f"{tpl} n={n}: {cards} cards")
            empty = "No results found" in region or "No products found" in region
            if empty != (n == 0):
                problems.append(f"{tpl} n={n}: empty-state={empty}")
            text = " ".join(html.split())
            m = re.search(r"(\d+)\s*out of\s*(\d+)\s*products", text)
            if n and not m:
                problems.append(f"{tpl} n={n}: no 'N out of M products' count line")
            elif m and (int(m.group(1)), int(m.group(2))) != (n, total):
                problems.append(f"{tpl} n={n}: count line {m.groups()} != ({n}, {total})")
    # brands / categories listings
    html = render(env, "templates/brands.jinja", brands=Products([brand(i) for i in range(3)], count=3))
    if len(re.findall(r'class="group flex flex-col gap-4"', html)) != 3:
        problems.append("brands.jinja: card count")
    if "No brands found" in html:
        problems.append("brands.jinja: empty state with results")
    html = render(env, "templates/brands.jinja", brands=Products([], count=0))
    if "No brands found" not in html:
        problems.append("brands.jinja: no empty state without brands")

    cats = [category(0, "A", "a", subs=[category(5, "s", "s")]), category(1, "B", "b")]
    html = render(env, "templates/categories.jinja", categories=cats)
    if len(re.findall(r'class="group flex flex-col gap-4"', html)) != 2:
        problems.append("categories.jinja: card count")
    if carousel_roots(html) != ["subcategories-100"]:
        problems.append(f"categories.jinja: carousel roots {carousel_roots(html)} != ['subcategories-100']")
    html = render(env, "templates/categories.jinja", categories=[])
    if "No categories found" not in html:
        problems.append("categories.jinja: no empty state without categories")
    return problems


def prop_filter_recovery(env):
    """A brand/category page with zero results still offers the filters."""
    problems = []
    for tpl, extra in [("templates/brand.jinja", {"brand": brand(0, "acme", "ACME", "acme")}),
                       ("templates/category.jinja", {"category": category(0, "Alpha", "alpha")})]:
        html = render(env, tpl, products=Products([], count=0,
                                                  filters={"attributes": []}), **extra)
        if "No products found" not in html:
            problems.append(f"{tpl}: harness did not reach the empty state")
        if "filters-drawer" not in html:
            problems.append(f"{tpl}: zero results -> no filter drawer, shopper cannot relax the filter")
    return problems


PROPS = {
    "cards-own-record": prop_cards_own_record,
    "cards-escape": prop_cards_escape,
    "hero-h1-image": prop_hero,
    "carousel-scope": prop_carousel,
    "listing-grid": prop_listing,
    "filter-recovery": prop_filter_recovery,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if not (root / "templates" / "products.jinja").exists():
        sys.exit(f"CHANGED harness: {root} is not a growth-theme checkout")
    env = make_env(root)
    failed = 0
    for name, fn in PROPS.items():
        if args.only and args.only != name:
            continue
        try:
            problems = fn(env)
        except Exception as exc:  # a harness error, not a property failure
            print(f"PROP {name} ERROR")
            print(f"  harness error: {exc!r}")
            failed += 1
            continue
        print(f"PROP {name} {'FAIL' if problems else 'PASS'}")
        for p in problems[:8]:
            print(f"  - {p}")
        failed += bool(problems)
    sys.exit(0 if not failed else 0)  # check.sh reads the PROP lines, not the exit code


if __name__ == "__main__":
    main()
