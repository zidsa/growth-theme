#!/usr/bin/env python3
"""Template properties for the content-pages group: render the real .jinja files over a
bounded matrix of data and assert what the page must (and must not) contain.

Usage: uv run --no-project --with jinja2 python -I render_props.py [--root DIR] [--verbose]
  exit 0 = every property matched the outcome recorded in EXPECTED (and in SKILL.md)
  exit 1 = a property changed; the line says which (CHANGED <property>)

Fidelity notes (read before trusting a result):
  * vitrin builds its environment with `autoescape=select_autoescape()` (sdk/jinja.py), which
    only covers .html/.htm/.xml, so every `.jinja` theme template renders UNESCAPED. This
    harness uses autoescape=False to match; production confirms it (live /shipping-and-payment
    emits the literal "Shipping & Payment"). `tojson` is Jinja's own, which does escape < > & '.
  * `layout.jinja` is a stub (other group's file). Every `templates/*` and `components/*`
    file under test is the real file, unmodified.
  * vitrin's `_()` / `image_url()` / `url_for()` / `asset_url` are replaced by pure stand-ins.
"""

import argparse
import sys

sys.dont_write_bytecode = True
import json
import re
import sys
from html.parser import HTMLParser
from itertools import product
from pathlib import Path

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[3]

EXPECTED = {
    "FaqAccordionShape": "holds",
    "PageShape": "holds",
    "ShippingRowsMatchData": "holds",
    "ShippingPageSections": "holds",
    "PaymentAndBanks": "holds",
    "JsonIslandIsInert": "holds",
    "FaqTextEscaping": "violation",
    "PageTitleEscaping": "violation",
    "ShippingTextEscaping": "violation",
}

LAYOUT_STUB = (
    "<title>{% block title %}{% endblock %}</title>"
    "{% block content %}{% endblock %}{% block footer_scripts %}{% endblock %}"
)


# ── environment ─────────────────────────────────────────────────────────────


def make_env(root: Path) -> Environment:
    env = Environment(
        loader=ChoiceLoader([DictLoader({"layout.jinja": LAYOUT_STUB}), FileSystemLoader(str(root))]),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["_"] = lambda s, **kw: s % kw if kw else s
    env.globals["url_for"] = lambda name, **kw: "/" if name == "home" else f"/{name}"
    env.globals["image_url"] = lambda src, **kw: f"/img?src={src}"
    env.filters["asset_url"] = lambda path: f"/assets/{path}?v=t"
    return env


def render(env, name, **ctx):
    ctx.setdefault("store", {"name": "S", "settings": {}})
    ctx.setdefault("session", {"lang": "en"})
    return env.get_template(name).render(**ctx)


# ── html helpers ────────────────────────────────────────────────────────────


class Elements(HTMLParser):
    """Collects (tag, attrs) for every start tag; <script> bodies stay opaque text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []

    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))


def elements(html):
    p = Elements()
    p.feed(html)
    return p.items


def text_of(html):
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def leaked(html, field):
    """True when a payload for `field` became a real <i id="SINK-field"> element."""
    return any(t == "i" and a.get("id") == f"SINK-{field}" for t, a in elements(html))


def payload(field):
    # Breaks out of an attribute value AND opens an element in text context.
    return f'"><i id="SINK-{field}">'


def island(html):
    m = re.search(r'<script type="application/json" id="shipping-methods-data">(.*?)</script>', html, re.S)
    return m.group(1) if m else None


# ── fixtures ────────────────────────────────────────────────────────────────


def method(i, n_cities=2, cost=1, cod=(True, 0), image=True, name=None):
    costs = [
        [],
        [{"title": "", "cost": 10, "cost_string": f"c{i}a SAR"}],
        [
            {"title": "from", "cost": 10, "cost_string": f"c{i}a SAR"},
            {"title": "to", "cost": 20, "cost_string": f"c{i}b SAR"},
        ],
    ][cost]
    fees = [[], [{"cod_fee_string": f"f{i}a SAR"}], [{"cod_fee_string": f"f{i}a SAR"}, {"cod_fee_string": f"f{i}b SAR"}]][
        cod[1]
    ]
    return {
        "id": i,
        "name": name or f"method_{i}_end",
        "image": f"http://img/{i}.png" if image else None,
        "cod_enabled": cod[0],
        "cod_fee": fees,
        "cost": costs,
        "delivery_option_cities": [{"name": f"city_{i}_{k}_end"} for k in range(n_cities)],
    }


def bank(i, logo=True, beneficiary=True, account=True, iban=True, name=None):
    return {
        "bank": {"name": name or f"bank_{i}_end", "logo": f"http://img/b{i}.png" if logo else None},
        "beneficiary_name": f"ben_{i}_end" if beneficiary else None,
        "account_number": f"acct{i}" if account else None,
        "iban": f"SA{i:020d}" if iban else None,
    }


def pay_method(i, icons=1, name=True):
    return {"name": f"pay_{i}_end" if name else None, "icons": [f"http://img/p{i}_{k}.png" for k in range(icons)]}


def page_ctx(methods=(), pays=(), banks=(), **store_settings):
    return {
        "shipping_methods": list(methods),
        "payment_methods": list(pays),
        "banks": list(banks),
        "store": {"name": "S", "settings": store_settings},
    }


# ── properties ──────────────────────────────────────────────────────────────


def tally(failures, label, cond, detail):
    if not cond:
        failures.append(f"{label}: {detail}")


def prop_faq_accordion_shape(env):
    failures = []
    for n in (0, 1, 2, 5):
        faqs = [{"question": f"q{k}", "answer": f"<p>a{k}</p>"} for k in range(n)]
        html = render(env, "templates/faqs.jinja", faqs=faqs)
        els = elements(html)
        buttons = [a for t, a in els if t == "button" and a.get("commandfor", "").startswith("faq-")]
        panels = [a for t, a in els if t == "el-disclosure"]
        label = f"faqs[{n}]"
        tally(failures, label, len(buttons) == n and len(panels) == n, f"{len(buttons)} buttons / {len(panels)} panels")
        tally(failures, label, [b["commandfor"] for b in buttons] == [p.get("id") for p in panels], "button/panel ids differ")
        tally(failures, label, len({p.get("id") for p in panels}) == len(panels), "duplicate panel id")
        tally(failures, label, html.count("<h1") == 1, "not exactly one h1")
        if n:
            tally(failures, label, buttons[0]["aria-expanded"] == "true" and "hidden" not in panels[0], "first not open")
            tally(
                failures,
                label,
                all(b["aria-expanded"] == "false" for b in buttons[1:]) and all("hidden" in p for p in panels[1:]),
                "others not closed",
            )
            tally(failures, label, all(f"<p>a{k}</p>" in html for k in range(n)), "an answer is missing/escaped")
            tally(failures, label, "No FAQs available" not in html, "empty state shown with data")
        else:
            tally(failures, label, "No FAQs available" in html, "empty state missing")
    return failures


def prop_page_shape(env):
    failures = []
    for title, content in [("About", "<p>x</p>"), ("Terms & Conditions", "<h2>a</h2><ul><li>b</li></ul>"), ("T", "")]:
        html = render(env, "templates/page.jinja", page={"title": title, "content": content})
        label = f"page[{title}]"
        tally(failures, label, html.count("<h1") == 1, "not exactly one h1")
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        tally(failures, label, bool(h1) and h1.group(1).strip() == title, "h1 != title")
        tally(failures, label, f"<title>{title} – S</title>" in html, "title tag != 'title – store'")
        tally(failures, label, len(re.findall(r'aria-current="page"', html)) == 1, "breadcrumb current != 1")
        m = re.search(r'aria-current="page"[^>]*>\s*(.*?)\s*</span>', html, re.S)
        tally(failures, label, bool(m) and m.group(1) == title, "breadcrumb current != title")
        body = re.search(r'<div class="prose prose-theme[^"]*">(.*)</div>\s*</div>\s*</section>', html, re.S)
        tally(failures, label, bool(body) and body.group(1) == content, "content not rendered verbatim in prose block")
    return failures


def _row_checks(failures, label, html, m, mobile):
    n = len(m["delivery_option_cities"])
    attr = "data-cities-trigger-mobile" if mobile else "data-cities-trigger"
    triggers = [a for t, a in elements(html) if t == "button" and attr in a]
    txt = text_of(html)
    tally(failures, label, len(triggers) == (1 if n > 3 else 0), f"{len(triggers)} '+N more' triggers for {n} cities")
    if n > 3 and triggers:
        tally(failures, label, triggers[0].get("data-method-id") == str(m["id"]), "trigger carries wrong method id")
        tally(failures, label, triggers[0].get("data-method-name") == m["name"], "trigger carries wrong method name")
    if n > 3:
        tally(failures, label, f"{n - 3} more" in txt, "'N more' count wrong")
    tally(failures, label, ("All areas" in txt) == (n == 0), "'All areas' iff no cities")
    shown = [c["name"] for c in m["delivery_option_cities"]]
    tally(failures, label, all((c in txt) == (k < 3) for k, c in enumerate(shown)), "preview is not the first 3 cities")
    tally(failures, label, m["name"] in txt, "method name missing")
    if m["cost"]:
        tally(failures, label, all(c["cost_string"] in txt for c in m["cost"]) and "Free" not in txt, "cost strings")
    else:
        tally(failures, label, "Free" in txt, "no cost should read Free")
    fees = [f["cod_fee_string"] for f in m["cod_fee"]]
    if m["cod_enabled"]:
        tally(failures, label, "Not supported" not in txt, "COD enabled but 'Not supported'")
        tally(failures, label, all(f in txt for f in fees), "COD fee missing")
        tally(failures, label, ("Available" in txt) == (not fees), "'Available' iff COD on with no fee")
    else:
        tally(failures, label, "Not supported" in txt, "COD off must read Not supported")
        tally(failures, label, not any(f in txt for f in fees) and "Available" not in txt, "COD off but fee/Available shown")
    imgs = [a for t, a in elements(html) if t == "img"]
    tally(failures, label, len(imgs) == (1 if m["image"] else 0), "method image iff image set")


def prop_shipping_rows(env):
    failures = []
    cod_opts = [(False, 0), (False, 1), (True, 0), (True, 1), (True, 2)]
    i = 0
    for n, cost, cod, image in product((0, 1, 3, 4, 10), (0, 1, 2), cod_opts, (True, False)):
        i += 1
        m = method(i, n, cost, cod, image)
        label = f"method[cities={n},cost={cost},cod={cod},image={image}]"
        _row_checks(failures, label + " table", render(env, "components/shipping-payment/shipping-table.jinja", shipping_methods=[m]), m, False)
        _row_checks(failures, label + " cards", render(env, "components/shipping-payment/shipping-cards-mobile.jinja", shipping_methods=[m]), m, True)
    for tpl in ("shipping-table", "shipping-cards-mobile"):
        html = render(env, f"components/shipping-payment/{tpl}.jinja", shipping_methods=[])
        tally(failures, tpl + "[empty]", "No shipping options available" in html, "empty state missing")
        tally(failures, tpl + "[empty]", not any(t == "button" for t, _ in elements(html)), "button in empty state")
    many = [method(k, 5) for k in range(1, 8)]
    for tpl in ("shipping-table", "shipping-cards-mobile"):
        html = render(env, f"components/shipping-payment/{tpl}.jinja", shipping_methods=many)
        names = [m["name"] for m in many]
        order = [html.index(n) for n in names]
        tally(failures, tpl + "[7]", order == sorted(order), "methods not in API order")
        tally(failures, tpl + "[7]", all(html.count(n) >= 1 for n in names), "a method is missing")
    return failures


def prop_shipping_page_sections(env):
    failures = []
    for with_banks, with_pays in product((True, False), repeat=2):
        ctx = page_ctx([method(1, 5), method(2, 1)], [pay_method(1)] if with_pays else [], [bank(1)] if with_banks else [])
        html = render(env, "templates/shipping_payment.jinja", **ctx)
        els = elements(html)
        label = f"page[banks={with_banks},pays={with_pays}]"
        ids = [a["id"] for _, a in els if "id" in a]
        tally(failures, label, len(ids) == len(set(ids)), f"duplicate ids {sorted({i for i in ids if ids.count(i) > 1})}")
        for need in ("shipping-options", "payment-options", "cities-dialog", "cities-search-input", "shipping-methods-data"):
            tally(failures, label, ids.count(need) == 1, f"id {need} x{ids.count(need)}")
        tally(failures, label, ids.count("bank-accounts") == (1 if with_banks else 0), "bank section iff banks")
        buttons = {a["commandfor"]: a for t, a in els if t == "button" and a.get("command") == "--toggle"}
        tally(failures, label, set(buttons) == ({"shipping-options", "payment-options"} | ({"bank-accounts"} if with_banks else set())), "toggle buttons")
        panels = {a["id"]: a for t, a in els if t == "el-disclosure" and "id" in a}
        tally(failures, label, buttons["shipping-options"]["aria-expanded"] == "true" and "hidden" not in panels["shipping-options"], "shipping not open by default")
        for other in ("payment-options", "bank-accounts"):
            if other in buttons:
                tally(failures, label, buttons[other]["aria-expanded"] == "false" and "hidden" in panels[other], f"{other} not closed by default")
        tally(failures, label, html.count("shipping-payment.js") == 1 and "defer" in html, "script tag not emitted once with defer")
        # every close control targets the dialog that exists
        closes = [a for t, a in els if t == "button" and a.get("command") == "close"]
        tally(failures, label, closes and all(a.get("commandfor") == "cities-dialog" for a in closes), "close button targets wrong id")
        # every hook shipping-payment.js queries exists exactly once
        for hook in ("data-cities-dialog-title", "data-cities-list-container", "data-cities-search", "data-cities-empty"):
            tally(failures, label, sum(hook in a for _, a in els) == 1, f"hook {hook} x{sum(hook in a for _, a in els)}")
        # every trigger resolves in the island, otherwise the click silently does nothing
        data = json.loads(island(html))
        known = {str(m["id"]) for m in data}
        for t, a in els:
            if t == "button" and ("data-cities-trigger" in a or "data-cities-trigger-mobile" in a):
                tally(failures, label, a.get("data-method-id") in known, f"trigger id {a.get('data-method-id')} not in island")
    return failures


def prop_payment_and_banks(env):
    failures = []
    for icons, named, desc in product((0, 1, 3), (True, False), (None, "pay_desc_end")):
        methods = [pay_method(1, icons, named), pay_method(2, 2, True)]
        html = render(env, "components/shipping-payment/payment-methods.jinja", payment_methods=methods, store={"name": "S", "settings": {"payment_description": desc}})
        label = f"payments[icons={icons},named={named},desc={desc}]"
        imgs = [a for t, a in elements(html) if t == "img"]
        tally(failures, label, len(imgs) == icons + 2, f"{len(imgs)} icons for {icons + 2} given")
        tally(failures, label, all(a.get("alt") for a in imgs), "an icon has an empty alt")
        tally(failures, label, ("pay_desc_end" in html) == bool(desc), "description iff set")
        tally(failures, label, "No payment methods available" not in html, "empty state with data")
    html = render(env, "components/shipping-payment/payment-methods.jinja", payment_methods=[], store={"name": "S", "settings": {"payment_description": "d_end"}})
    tally(failures, "payments[empty]", "No payment methods available" in html and "d_end" not in html, "empty state / stray description")
    for logo, ben, acct, iban in product((True, False), repeat=4):
        b = bank(1, logo, ben, acct, iban)
        html = render(env, "components/shipping-payment/bank-accounts.jinja", banks=[b, bank(2)])
        els = elements(html)
        copies = [a for t, a in els if t == "button" and "data-copy-btn" in a]
        want = {v for v in (b["account_number"], b["iban"], "acct2", bank(2)["iban"]) if v}
        label = f"bank[logo={logo},ben={ben},acct={acct},iban={iban}]"
        tally(failures, label, len(copies) == len(want) and {a["data-copy-value"] for a in copies} == want, "copy buttons != account/iban values")
        tally(failures, label, ("ben_1_end" in html) == ben, "beneficiary iff set")
        tally(failures, label, len([1 for t, a in els if t == "img"]) == (1 if logo else 0) + 1, "logo iff set")
        tally(failures, label, b["bank"]["name"] in html, "bank name missing")
        tally(failures, label, all(a.get("aria-label") for a in copies), "copy button without aria-label")
    html = render(env, "components/shipping-payment/bank-accounts.jinja", banks=[])
    tally(failures, "banks[empty]", "No bank accounts available" in html and "data-copy-btn" not in html, "empty state")
    return failures


def prop_json_island(env):
    failures = []
    nasty = ["</script><i id=x>", "<!--", "&amp; ' \" \\ \u2028", "]]></script>", "</SCRIPT >"]
    for name in nasty:
        m = method(1, 5, name=name)
        m["delivery_option_cities"][0]["name"] = name
        html = render(env, "templates/shipping_payment.jinja", **page_ctx([m]))
        raw = island(html)
        label = f"island[{name!r}]"
        try:
            data = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{label}: island is not JSON ({exc})")
            continue
        tally(failures, label, data[0]["name"] == name and data[0]["delivery_option_cities"][0]["name"] == name, "round-trip changed the data")
        tally(failures, label, "</" not in raw and "<!--" not in raw, "raw '</' or '<!--' inside the script body")
    return failures


def _sink_prop(env, render_fn, fields):
    """Run `render_fn` with each field poisoned; return the sorted list of fields that became markup."""
    return sorted(f for f in fields if leaked(render_fn(f), f))


def prop_faq_escaping(env):
    out = _sink_prop(env, lambda f: render(env, "templates/faqs.jinja", faqs=[{"question": payload(f), "answer": "a"}]), ["question"])
    return out


def prop_page_escaping(env):
    def r(f):
        return render(env, "templates/page.jinja", page={"title": payload(f), "content": "c"})

    # one poisoned title, three sinks: h1, <title>, breadcrumb
    html = r("title")
    sinks = []
    if re.search(r"<h1[^>]*>\s*\"><i id=\"SINK-title\">", html):
        sinks.append("h1")
    if re.search(r"<title>\"><i id=\"SINK-title\">", html):
        sinks.append("title-tag")
    if re.search(r"aria-current=\"page\"[^>]*>\s*\"><i id=\"SINK-title\">", html):
        sinks.append("breadcrumb")
    return sinks


def prop_shipping_escaping(env):
    """Poison one field at a time through the full page; returns the fields that become markup."""
    sinks = []
    plans = {
        "method.name": lambda p: page_ctx([method(1, 5, name=p)]),
        "city.name": lambda p: page_ctx([{**method(1, 2), "delivery_option_cities": [{"name": p}]}]),
        "cost_string": lambda p: page_ctx([{**method(1), "cost": [{"title": "", "cost": 1, "cost_string": p}]}]),
        "cod_fee_string": lambda p: page_ctx([{**method(1, cod=(True, 0)), "cod_fee": [{"cod_fee_string": p}]}]),
        "method.image": lambda p: page_ctx([{**method(1), "image": p}]),
        "payment.name": lambda p: page_ctx(pays=[{"name": p, "icons": ["http://i/1.png"]}]),
        "payment_description": lambda p: page_ctx(pays=[pay_method(1)], payment_description=p),
        "bank.name": lambda p: page_ctx(banks=[{**bank(1), "bank": {"name": p, "logo": None}}]),
        "beneficiary_name": lambda p: page_ctx(banks=[{**bank(1), "beneficiary_name": p}]),
        "account_number": lambda p: page_ctx(banks=[{**bank(1), "account_number": p}]),
        "iban": lambda p: page_ctx(banks=[{**bank(1), "iban": p}]),
    }
    for field, make in plans.items():
        tag = field.replace(".", "_")
        html = render(env, "templates/shipping_payment.jinja", **make(payload(tag)))
        if leaked(html, tag):
            sinks.append(field)
    return sorted(sinks)


# ── runner ──────────────────────────────────────────────────────────────────

HOLDS = [
    ("FaqAccordionShape", prop_faq_accordion_shape, "templates/faqs.jinja"),
    ("PageShape", prop_page_shape, "templates/page.jinja"),
    ("ShippingRowsMatchData", prop_shipping_rows, "components/shipping-payment/shipping-table.jinja, shipping-cards-mobile.jinja"),
    ("ShippingPageSections", prop_shipping_page_sections, "templates/shipping_payment.jinja, components/shipping-payment/cities-dialog.jinja"),
    ("PaymentAndBanks", prop_payment_and_banks, "components/shipping-payment/payment-methods.jinja, bank-accounts.jinja"),
    ("JsonIslandIsInert", prop_json_island, "components/shipping-payment/shipping-table.jinja (#shipping-methods-data)"),
]
SINKS = [
    ("FaqTextEscaping", prop_faq_escaping, "faq.question is written as markup"),
    ("PageTitleEscaping", prop_page_escaping, "page.title is written as markup"),
    ("ShippingTextEscaping", prop_shipping_escaping, "merchant/API strings are written as markup"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    env = make_env(root)
    bad = 0
    for name, fn, where in HOLDS:
        failures = fn(env)
        got = "holds" if not failures else "violation"
        if got != EXPECTED[name]:
            bad += 1
            print(f"CHANGED  {name}: recorded {EXPECTED[name]}, now {got} ({where})")
            for f in failures[:6]:
                print(f"           {f}")
        else:
            print(f"ok       {name}: {got} ({where})")
    for name, fn, what in SINKS:
        sinks = fn(env)
        got = "violation" if sinks else "holds"
        if got != EXPECTED[name]:
            bad += 1
            print(f"CHANGED  {name}: recorded {EXPECTED[name]}, now {got}")
            print("           if the code was fixed, update EXPECTED here and in SKILL.md and the finding.")
        else:
            print(f"ok       {name}: {got} as recorded")
            print(f"FINDING: {name}: {what}; leaking sinks: {', '.join(sinks)}")
    print(f"templates: {'every property matches its recorded outcome' if not bad else str(bad) + ' changed'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
