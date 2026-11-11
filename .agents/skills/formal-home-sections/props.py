"""formal-home-sections: bounded-exhaustive property checks over templates/home + sections/*.

Renders the REAL templates with plain Jinja2 (harness = ../verify-home-sections/render.py:make_env)
over generated settings and prints one line per property:

    RESULT <id> holds
    RESULT <id> finding <stable counterexample key>

Run by check.sh, which compares the lines with expected.txt. Nothing is random; the "seed" is the
fixed enumeration order. Usage: ROOT=<repo> uv run --no-project --with jinja2 python -I props.py [id...]
"""

import importlib.util
import itertools
import json
import os
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(os.environ.get("ROOT") or Path(__file__).resolve().parents[3])
os.environ["ROOT"] = str(ROOT)
_spec = importlib.util.spec_from_file_location("render", ROOT / ".agents/skills/verify-home-sections/render.py")
render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render)
ENV = render.make_env()
SECTIONS = ["benefits", "call-to-action", "carousel", "categories", "countdown", "gallery", "hero",
            "logo-social", "partners", "products", "testimonials", "video"]


# ── plumbing ─────────────────────────────────────────────────────────────────
class Dom(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.els, self.scripts, self._in_script, self.text = [], [], False, []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.els.append((tag, dict(attrs)))
        self._in_script = tag == "script"
        if tag == "script":
            self.scripts.append("")

    def handle_endtag(self, tag):
        self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.scripts[-1] += data
        else:
            self.text.append(data)

    def q(self, tag=None, **attr):
        return [(t, a) for t, a in self.els if (tag is None or t == tag) and all(a.get(k) == v for k, v in attr.items())]

    def count(self, tag):
        return sum(1 for t, _ in self.els if t == tag)


def schema(section):
    return json.loads((ROOT / "sections" / f"{section}.schema.json").read_text())["settings"]


def defaults(section):
    return {s["id"]: s["default"] for s in schema(section) if "default" in s}


STORE = {"name": "Fixture Store", "settings": {}}


def section_html(section, settings=None, order=1, store=None, sid=None):
    s = {**defaults(section), **(settings or {}), "order": order}
    return ENV.get_template(f"sections/{section}.jinja").render(
        settings=s, sectionId=sid or f"{section}-x", store=store or STORE,
        session={"lang": "ar", "locale": {"language": {"direction": "rtl"}}},
    )


def home_html(components, store=None):
    comps = [{"template": f"sections/{n}.jinja", "settings": {**defaults(n), **st}, "section_id": f"{n}-{i}"} for i, (n, st) in enumerate(components, 1)]
    return ENV.get_template("templates/home.jinja").render(
        store=store or STORE, components=comps, session={"lang": "ar", "locale": {"language": {"direction": "rtl"}}})


def product(i, name=None):
    return {"id": f"p{i}", "slug": f"p-{i}", "name": name or f"Product {i}", "in_stock": True, "is_infinite": True,
            "quantity": 5, "price": 10.0, "formatted_price": "10.00 SAR", "images": [], "selected_product": {"in_stock": True},
            "categories": []}


results = []


def report(pid, counterexamples):
    results.append((pid, sorted(set(counterexamples))))


# ── P1 escaping (all 12 sections + home h1) ─────────────────────────────────
PAYLOADS = ['<b id="pwn">x</b>"\'><img id=pwn src=x onerror=pwn()>', "</script><script id=pwn>pwn()</script>", "\" onmouseover=\"pwn()"]
TEXTLIKE = {"text", "textarea", "url", "image", "color", "video"}


def hostile_variants(section):
    """Every text-like field alone gets each payload (bounded-exhaustive, one field at a time)."""
    for f in schema(section):
        if f["type"] in TEXTLIKE:
            for p in PAYLOADS:
                yield f"{f['id']}", {f["id"]: p}
        if f["type"] == "list":
            for sub in f.get("settings", []):
                if sub["type"] in TEXTLIKE | {"category"}:
                    for p in PAYLOADS:
                        item = {s["id"]: ("benign" if s["type"] in TEXTLIKE else s.get("default")) for s in f["settings"]}
                        item[sub["id"]] = p
                        if sub["type"] == "category":
                            item[sub["id"]] = {"id": "c1", "slug": "s", "name": p, "image_full_size": p}
                        yield f"{f['id']}[].{sub['id']}", {f["id"]: [item]}


def injected(dom, baseline_scripts):
    bad = []
    for tag, a in dom.els:
        if a.get("id") == "pwn":
            bad.append(f"element id=pwn <{tag}>")
        for k in a:
            if k.startswith("on"):
                bad.append(f"attr {k} on <{tag}>")
    if len(dom.scripts) != baseline_scripts:
        bad.append(f"script count {len(dom.scripts)} != {baseline_scripts}")
    return bad


def p1_escaping():
    ce = []
    for sec in SECTIONS:
        base_settings = {}
        if sec == "products":
            base_settings = {"products": {"results": [product(1)]}}
        if sec == "video":
            base_settings = {"video": "v.mp4"}  # the play-button script exists only with a video
        baseline = len(Dom(section_html(sec, base_settings)).scripts)
        for label, st in hostile_variants(sec):
            st = {**base_settings, **st}
            for bad in injected(Dom(section_html(sec, st)), baseline):
                ce.append(f"{sec}.{label}: {bad}")
    # data that is not a schema text field: category names, product names, store name, store contact handles
    cats = [{"category": {"id": "c1", "slug": "s", "name": p, "image_full_size": p}} for p in PAYLOADS]
    for bad in injected(Dom(section_html("categories", {"categories": cats})), 0):
        ce.append(f"categories.category.name: {bad}")
    pr = {"results": [product(i, p) for i, p in enumerate(PAYLOADS)]}
    for layout in ("carousel", "grid", "list"):
        for bad in injected(Dom(section_html("products", {"products": pr, "layout": layout})), 0):
            ce.append(f"products[{layout}].product.name: {bad}")
    for p in PAYLOADS:
        st = {"name": p, "settings": {"contact": {k: p for k in ("facebook", "instagram", "twitter", "snapchat", "tiktok", "youtube", "linkedin", "title")}}}
        for bad in injected(Dom(section_html("logo-social", store=st)), 0):
            ce.append(f"logo-social.store: {bad}")
        for bad in injected(Dom(home_html([], store=st)), 0):
            ce.append(f"home.h1.store.name: {bad}")
    report("P1-escaping", ce)


# ── P2 countdown script literal ──────────────────────────────────────────────
def p2_countdown_literal():
    """The merchant's end_date lands inside `new Date("...")` in an inline <script>. Escaping must not
    leave a raw quote, backslash or `</` that can end the string or the script."""
    ce = []
    for payload in PAYLOADS + ["\\", "2030-01-01\\", "a\nb"]:
        scripts = Dom(section_html("countdown", {"end_date": payload})).scripts
        body = scripts[0]
        lit = body.split('new Date("', 1)[1].split('")', 1)[0] if 'new Date("' in body else None
        if lit is None:
            ce.append(f"{payload!r}: literal terminator moved")
        elif "\\" in lit.replace("\\\\", ""):  # a lone backslash can escape the closing quote
            ce.append(f"{payload!r}: backslash survives into the JS string literal")
        elif "</" in lit or "\n" in lit:
            ce.append(f"{payload!r}: raw </ or newline in literal")
    report("P2-countdown-literal", ce)


# ── P3 template invariants over flag combinations ───────────────────────────
def blank(v):
    return v is None or not str(v).strip()


def p3_hero():
    ce = []
    for order, primary, heading, badge, btn, desc in itertools.product((1, 2, 3, 4), (True, False), ("H", " ", ""), ("B", ""), ("Go", " ", ""), ("D", "")):
        st = {"is_primary_hero": primary, "heading": heading, "badge_text": badge, "button_text": btn, "description": desc, "background_image": "i"}
        d = Dom(section_html("hero", st, order=order))
        key = f"order={order} primary={primary} heading={heading!r} btn={btn!r}"
        h1, h2 = d.count("h1"), d.count("h2")
        if h1 != int(primary and not blank(heading)) or h2 != int((not primary) and not blank(heading)):
            ce.append(f"{key}: h1={h1} h2={h2}")
        if len(d.q("a")) != int(not blank(btn)):
            ce.append(f"{key}: anchors={len(d.q('a'))}")
        img = d.q("img")[0][1]
        if (order > 2) != (img.get("loading") == "lazy") or (order <= 2) != (img.get("fetchpriority") == "high") or ("loading" in img and "fetchpriority" in img):
            ce.append(f"{key}: img hints {img.get('loading')}/{img.get('fetchpriority')}")
    report("P3a-hero-flags", ce)


def p3_carousel():
    ce = []
    for n, dots, autoplay, effect, order in itertools.product(range(0, 6), (True, False), (True, False), ("fade", "slide"), (1, 3)):
        slides = [{"background_image": f"i{k}", "heading": f"h{k}"} for k in range(n)]
        d = Dom(section_html("carousel", {"slides": slides, "show_dots": dots, "autoplay_enabled": autoplay, "transition_effect": effect}, order=order))
        key = f"n={n} dots={dots} autoplay={autoplay} effect={effect} order={order}"
        if len(d.q("div", **{"class": "embla__slide"})) != n and sum(1 for _, a in d.els if "embla__slide" in a.get("class", "").split()) != n:
            ce.append(f"{key}: slide count")
        marks = d.q("div", **{"data-carousel-dots": ""}) or [e for e in d.els if "data-carousel-dots" in e[1]]
        if bool(marks) != (dots and n > 1):
            ce.append(f"{key}: dots container={bool(marks)}")
        root = [a for _, a in d.els if "data-carousel" in a and "data-carousel-dots" not in a]
        if root:
            if (root[0].get("data-carousel-autoplay") not in (None, "")) != autoplay:
                ce.append(f"{key}: autoplay attr {root[0].get('data-carousel-autoplay')!r}")
            if (root[0].get("data-carousel-fade") == "true") != (effect == "fade"):
                ce.append(f"{key}: fade attr {root[0].get('data-carousel-fade')!r}")
        imgs = [a for t, a in d.els if t == "img"]
        highs = [i for i, a in enumerate(imgs) if a.get("fetchpriority") == "high"]
        if highs != ([0] if (order <= 2 and n) else []):
            ce.append(f"{key}: fetchpriority-high images {highs}")
    report("P3b-carousel-flags", ce)


def p3_gallery():
    ce = []
    for n in range(0, 9):
        for with_overlay in (True, False):
            items = [{"src": f"g{k}", "alt": "a", "image_title": "T" if with_overlay else "", "primary_button_text": "B" if with_overlay else "", "primary_button_url": "/u" if with_overlay else ""} for k in range(n)]
            d = Dom(section_html("gallery", {"gallery": items}))
            attr = [a["data-items-count"] for _, a in d.els if "data-items-count" in a]
            key = f"n={n} overlay={with_overlay}"
            if n == 0 and attr:
                ce.append(f"{key}: grid rendered for zero items")
            if n and (attr != [str(n)] or d.count("img") != n):
                ce.append(f"{key}: data-items-count={attr} imgs={d.count('img')}")
            if d.count("h3") != (n if with_overlay else 0):
                ce.append(f"{key}: h3={d.count('h3')}")
    report("P3c-gallery-count", ce)


def p3_data_present():
    """An element is rendered iff its data is present (products, categories, benefits, partners, testimonials, video, CTA)."""
    ce = []
    for k in range(0, 5):
        pr = {"results": [product(i) for i in range(k)]} if k else None
        for layout in ("carousel", "grid", "list"):
            d = Dom(section_html("products", {"products": pr, "layout": layout}))
            n_cards = sum(1 for _, a in d.els if "data-product-card" in a)
            if n_cards != k or (d.count("section") != int(k > 0)):
                ce.append(f"products layout={layout} k={k}: cards={n_cards} sections={d.count('section')}")
            if k:
                root = [e for e in d.els if "data-products-carousel" in e[1] or e[1].get("data-grid") in ("grid", "list")]
                if len(root) != 1:
                    ce.append(f"products layout={layout}: layout roots={len(root)}")
    for n in range(0, 5):
        cats = [{"category": {"id": f"c{i}", "slug": f"s{i}", "name": f"N{i}", "image_full_size": "i"}} for i in range(n)]
        for more in (True, False):
            d = Dom(section_html("categories", {"categories": cats, "display_more": more}))
            slides = sum(1 for _, a in d.els if "embla__slide" in a.get("class", "").split())
            links = [a["href"] for t, a in d.els if t == "a" and a.get("href") == "/categories"]
            if slides != n or bool(links) != more:
                ce.append(f"categories n={n} more={more}: slides={slides} viewall={len(links)}")
    for n in range(0, 4):
        feats = [{"image": "i", "title": "T", "description": "D"} for _ in range(n)]
        d = Dom(section_html("benefits", {"store_features": feats}))
        if d.count("h3") != n or d.count("img") != n:
            ce.append(f"benefits n={n}: h3={d.count('h3')} img={d.count('img')}")
        parts = [{"name": f"P{i}", "image": "i", "url": "https://x" if i % 2 else ""} for i in range(n)]
        d = Dom(section_html("partners", {"store_partners": parts}))
        if d.count("img") != n or d.count("a") != n // 2:
            ce.append(f"partners n={n}: img={d.count('img')} a={d.count('a')}")
        for r in range(0, 6):
            t = [{"rating": r, "text": "t", "name": "N"} for _ in range(n)]
            d = Dom(section_html("testimonials", {"testimonials": t}))
            arts = d.count("article")
            stars = sum(1 for tag, a in d.els if tag == "svg" and a.get("class") == "text-warning")
            if arts != n or stars != n * r:
                ce.append(f"testimonials n={n} rating={r}: articles={arts} filled={stars}")
    for url, auto, order in itertools.product(("", "v.mp4"), (True, False), (1, 3)):
        d = Dom(section_html("video", {"video": url, "autoplay": auto}, order=order))
        has_overlay = any("video-overlay" in a.get("class", "") for _, a in d.els)
        if d.count("video") != int(bool(url)) or has_overlay != (bool(url) and not auto):
            ce.append(f"video url={url!r} autoplay={auto}: video={d.count('video')} overlay={has_overlay}")
    for head, desc, btn in itertools.product(("H", " ", ""), ("D", " ", ""), ("B", " ", "")):
        d = Dom(section_html("call-to-action", {"heading": head, "description": desc, "button_text": btn}))
        if (d.count("h2"), d.count("p"), d.count("a")) != (int(not blank(head)), int(not blank(desc)), int(not blank(btn))):
            ce.append(f"cta head={head!r} desc={desc!r} btn={btn!r}: {(d.count('h2'), d.count('p'), d.count('a'))}")
    report("P3d-element-iff-data", ce)


# ── P4 links: a rendered CTA never has an empty href ────────────────────────
def p4_empty_href():
    """Every merchant-configurable CTA with its schema-default (empty) url must not render href=""."""
    ce = []
    ctas = {
        "hero": {"background_image": "i"},
        "countdown": {"end_date": "2099-01-01T00:00:00Z"},
        "call-to-action": {},
        "carousel": {"slides": [{"background_image": "i", "heading": "h", "button_text": "Go"}]},
        "gallery": {"gallery": [{"src": "i", "primary_button_text": "Go", "secondary_button_text": "More"}]},
    }
    for sec, st in ctas.items():
        for t, a in Dom(section_html(sec, st)).els:
            if t == "a" and a.get("href", None) == "":
                ce.append(f"{sec}: <a> with href=\"\" when button_url is the schema default")
                break
    report("P4-no-empty-href", ce)


# ── P5 one <h1> per home page ───────────────────────────────────────────────
def p5_single_h1():
    ce = []
    for names in ([], ["hero"], ["carousel"], ["hero", "hero"], ["call-to-action", "products"]):
        comps = [(n, {"background_image": "i", "slides": [{"background_image": "i", "heading": "s"}]} if n in ("hero", "carousel") else {}) for n in names]
        h1 = Dom(home_html(comps)).count("h1")
        if h1 != 1:
            ce.append(f"sections={names}: {h1} <h1> elements on the page")
    report("P5-single-h1", ce)


PROPS = {"P1-escaping": p1_escaping, "P2-countdown-literal": p2_countdown_literal, "P3a-hero-flags": p3_hero,
         "P3b-carousel-flags": p3_carousel, "P3c-gallery-count": p3_gallery, "P3d-element-iff-data": p3_data_present,
         "P4-no-empty-href": p4_empty_href, "P5-single-h1": p5_single_h1}

if __name__ == "__main__":
    want = sys.argv[1:] or list(PROPS)
    for pid in want:
        PROPS[pid]()
    for pid, ce in results:
        if not ce:
            print(f"RESULT {pid} holds")
        else:
            print(f"RESULT {pid} finding {len(ce)}")
            for c in ce[:12]:
                print(f"  counterexample: {c}")
