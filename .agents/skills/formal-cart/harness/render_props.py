#!/usr/bin/env python3
"""Template properties for the cart group: render the real .jinja files over a bounded
matrix of cart/store states and assert what the page must (and must not) contain.

Usage: uv run --no-project --with jinja2 python -I render_props.py [--root DIR] [--verbose]
  exit 0 = every property matched the outcome recorded in EXPECTED (and in SKILL.md)
  exit 1 = a property changed; the line says which and what it saw

Fidelity notes (read these before trusting a result):
  * vitrin renders `.jinja` with `autoescape=select_autoescape()` — which only covers
    `.html/.xml` — so the theme's templates render UNESCAPED. This harness uses
    autoescape=False to match production, and `TotalsTextEscaping` in js_props.mjs
    covers the client path of the same promise.
  * `layout.jinja` and the `vitrin:*` partials are replaced by minimal stubs: they are
    other groups' files and the properties here concern the cart's own markup. Every
    `components/*` and `templates/*` file under test is the real file, unmodified.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[3]

EXPECTED = {
    "CartPageShape": "holds",
    "TotalsRows": "holds",
    "DiscountSign": "holds",
    "CouponSectionState": "holds",
    "SectionGating": "holds",
    "ProgressWidth": "violation",  # finding: the percentage is emitted unclamped
    "CartTextEscaping": "violation",  # finding: API strings are written as markup
}

FINDINGS = {
    "ProgressWidth": "the free-shipping percentage is written into the bar width unclamped "
    "(202% on store 1's cart, so the bar and truck run off the card).",
    "CartTextEscaping": "order-summary.jinja/coupon-code.jinja write cart API strings into the page "
    "unescaped (vitrin renders .jinja with autoescape off).",
}

LAYOUT_STUB = "{% block content %}{% endblock %}{% block footer_scripts %}{% endblock %}"

VITRIN_STUBS = {
    "vitrin:cart/progressive_discount.jinja": "",
    "vitrin:v2/cart/products_list.jinja": (
        '{% for p in cart.products %}<div data-cart-line="{{ p.id }}">'
        '<div data-qty-input="q-{{ p.id }}"><input data-qty-value value="{{ p.quantity }}"></div>'
        "</div>{% endfor %}"
    ),
    "vitrin:cart/customer_wallet_progress.jinja": "",
    "vitrin:shared/bank_discounts.jinja": "",
    "vitrin:cart/payment_widgets.jinja": "",
    "vitrin:checkout/apple-pay-quick-checkout.jinja": "",
    "vitrin:cart/gift-card.jinja": "",
}


# ── fixtures ────────────────────────────────────────────────────────────────


def totals(discount="-22.00 SAR", subtotal_code="sub_totals_before_vat"):
    rows = [
        {"code": subtotal_code, "title": "المجموع الفرعي", "value_string": "198.00 SAR"},
        {"code": "products_discount", "title": "الخصم", "value_string": discount},
        {"code": "vat", "title": "ضريبة القيمة المضافة", "value_string": "26.40 SAR"},
        {"code": "total", "title": "المجموع", "value_string": "202.40 SAR"},
    ]
    return rows


def cart_state(**over):
    state = {
        "products_count": 1,
        "products": [{"id": 11, "product_id": "prod-11", "quantity": 1, "name": "P"}],
        "totals": totals(),
        "coupon": None,
        "gift_card_details": {},
        "loyalty_applied_redemption_method": None,
        "currency": {"cart_currency": {"code": "SAR"}},
        "total_value": 202.4,
        "free_shipping_rule": None,
        "id": "cart-1",
    }
    state.update(over)
    return state


def store_state(**over):
    store = {
        "name": "Store",
        "settings": {
            "checkout": {
                "is_coupon_form_enabled": True,
                "is_loyalty_enabled": True,
                "gift_order_settings": {
                    "is_gift_order_enabled": "1",
                    "is_gift_order_customer_motivation_enabled": "1",
                },
            },
            "general": {"availability": {"closed_now": False}},
        },
    }
    for key, value in over.items():
        if key == "checkout":
            store["settings"]["checkout"].update(value)
        elif key == "closed_now":
            store["settings"]["general"]["availability"]["closed_now"] = value
    return store


def context(cart=None, store=None, **extra):
    ctx = {
        "cart": cart if cart is not None else cart_state(),
        "store": store if store is not None else store_state(),
        "settings": {},
        "session": {"currency": {"code": "SAR"}, "template": "cart_page", "lang": {"code": "ar"}},
    }
    ctx.update(extra)
    return ctx


# ── environment ─────────────────────────────────────────────────────────────


def make_env(root: Path) -> Environment:
    loaders = [
        DictLoader({"layout.jinja": LAYOUT_STUB, **VITRIN_STUBS}),
        FileSystemLoader(str(root)),
    ]
    env = Environment(loader=ChoiceLoader(loaders), autoescape=False)
    env.globals["url_for"] = lambda name, **kw: {"home": "/", "cart_page": "/cart"}.get(name, f"/{name}")
    env.globals["asset_url"] = lambda path: f"/assets/{path}?v=test"
    env.filters["asset_url"] = env.globals["asset_url"]
    env.globals["csrf_token"] = lambda: "csrf"
    return env


def gettext(message, **kwargs):
    """`_(...)` as vitrin installs it: a %-format template, formatted when args are given."""
    return message % kwargs if kwargs else message


# ── properties ──────────────────────────────────────────────────────────────


def render(env, name, **ctx):
    template = env.get_template(name)
    template.globals["_"] = gettext
    return template.render(**ctx)


def amounts(block):
    return re.findall(r"-?\d[\d,]*\.\d{2}", block)


def tally(failures, name, condition, detail):
    if not condition:
        failures.append(f"{name}: {detail}")


def prop_cart_page_shape(env):
    failures = []
    for count, label in [(0, "empty"), (1, "one line"), (3, "three lines")]:
        cart = cart_state(products_count=count, products=[{"id": 1, "product_id": "p1", "quantity": 1}] * count)
        html = render(env, "templates/cart.jinja", **context(cart))
        name = f"cart page [{label}]"
        tally(failures, name, html.count("data-cart-controller") <= 1, "unexpected controller marker")
        tally(failures, name, html.count("/assets/dist/cart-controller.js") == 1, "controller script not emitted once")
        tally(failures, name, "CartPage.init(" in html, "CartPage.init call missing")
        if count == 0:
            tally(failures, name, 'class="cart-empty' in html, "empty state missing")
            tally(failures, name, "data-cart-totals" not in html, "totals rendered on an empty cart")
            tally(failures, name, "data-cart-products-list" not in html, "product list rendered on an empty cart")
            tally(failures, name, "data-checkout-buttons" not in html, "checkout offered on an empty cart")
            tally(failures, name, "data-coupon-section" not in html, "coupon form on an empty cart")
        else:
            tally(failures, name, 'class="cart-empty' not in html, "empty state on a filled cart")
            tally(failures, name, html.count("data-cart-products-list") == 1, "product list not emitted once")
            tally(failures, name, html.count("data-cart-totals") == 1, "totals not emitted once")
            tally(failures, name, "data-checkout-buttons" in html, "no checkout button")
    return "CartPageShape", failures


def prop_totals_rows(env):
    failures = []
    cases = [
        ("four rows", totals()),
        ("no discount row", [t for t in totals() if t["code"] != "products_discount"]),
        ("discount above subtotal", totals(discount="-250.00 SAR")),
        ("sub_totals code", totals(subtotal_code="sub_totals")),
    ]
    for label, rows in cases:
        cart = cart_state(totals=rows, products_count=2)
        block = render(env, "components/cart/order-summary.jinja", cart=cart)
        for row in rows:
            if row["code"] == "total":
                continue
            value = row["value_string"]
            if row["code"] in ("discount", "coupon_discount", "products_discount"):
                value = value if value.startswith("-") else "-" + value
            tally(failures, f"{label} {row['code']}", value in block, f"missing {value!r}")
            if row["code"] != "products_discount":
                tally(failures, f"{label} {row['code']}", row["title"] in block, "title missing")

        total = next(r for r in rows if r["code"] == "total")
        tally(failures, label, block.count("font-semibold") == 2, "total row is not the only bold row")
        last_bold = block.rfind("font-semibold")
        others = [block.find(r["value_string"]) for r in rows if r["code"] != "total"]
        tally(failures, label, last_bold > max(others), "total row is not after the other rows")
        tally(failures, label, total["value_string"] in block[last_bold:], "total value missing")
        tally(failures, label, "--" not in block, "a money value carries a double sign")
        expected_items = any(r["code"] == "sub_totals" for r in rows)
        tally(
            failures,
            f"{label} items count",
            ("data-cart-items-count" in block) == expected_items,
            "item-count node does not follow the sub_totals row",
        )
    return "TotalsRows", failures


def prop_discount_sign(env):
    failures = []
    for value in ["-22.00 SAR", "22.00 SAR", "0.00 SAR", "-0.00 SAR"]:
        cart = cart_state(totals=totals(discount=value))
        block = render(env, "components/cart/order-summary.jinja", cart=cart)
        want = value if value.startswith("-") else "-" + value
        tally(failures, f"discount {value}", want in block, f"expected {want!r} in the summary")
        tally(failures, f"discount {value}", "--" not in block, "double sign")
    # A coupon row keeps its own code and shows the discount once.
    cart = cart_state(coupon={"code": "SAVE10"}, totals=totals(discount="-30.00 SAR"))
    block = render(env, "components/cart/order-summary.jinja", cart=cart)
    tally(failures, "coupon row", "SAVE10" in block, "coupon code missing")
    tally(failures, "coupon row", block.count("-30.00 SAR") == 1, "coupon discount rendered more than once")
    return "DiscountSign", failures


def prop_coupon_section_state(env):
    failures = []
    applied = render(
        env,
        "components/cart/coupon-code.jinja",
        cart=cart_state(coupon={"code": "SAVE10"}),
        store=store_state(),
    )
    tally(failures, "applied", "data-applied-coupon" in applied, "no applied-coupon chip")
    tally(failures, "applied", "SAVE10" in applied, "applied code missing")
    tally(failures, "applied", "data-coupon-delete-btn" in applied, "no remove button")
    tally(failures, "applied", "data-coupon-input" not in applied, "apply form still shown")

    empty = render(env, "components/cart/coupon-code.jinja", cart=cart_state(), store=store_state())
    tally(failures, "no coupon", "data-coupon-input" in empty, "no apply input")
    tally(failures, "no coupon", "data-coupon-submit-btn" in empty, "no apply button")
    tally(failures, "no coupon", re.search(r'disabled[^>]*data-coupon-submit-btn|data-coupon-submit-btn[^>]*disabled', empty) is not None, "apply button is not disabled")
    tally(failures, "no coupon", "data-applied-coupon" not in empty, "chip shown without a coupon")

    off = render(
        env,
        "components/cart/coupon-code.jinja",
        cart=cart_state(),
        store=store_state(checkout={"is_coupon_form_enabled": False}),
    )
    tally(failures, "form disabled", "data-coupon-section" not in off, "coupon section rendered while disabled")
    return "CouponSectionState", failures


def prop_section_gating(env):
    failures = []
    for gift in ("1", "0"):
        for loyalty in (True, False):
            for coupon in (True, False):
                store = store_state(
                    checkout={
                        "is_loyalty_enabled": loyalty,
                        "is_coupon_form_enabled": coupon,
                        "gift_order_settings": {
                            "is_gift_order_enabled": gift,
                            "is_gift_order_customer_motivation_enabled": gift,
                        },
                    }
                )
                html = render(env, "templates/cart.jinja", **context(cart_state(), store))
                label = f"gift={gift} loyalty={loyalty} coupon={coupon}"
                tally(failures, f"{label} gift", ("data-gift-order-section" in html) == (gift == "1"), "gift section gating")
                tally(failures, f"{label} loyalty", ("data-loyalty-section" in html) == bool(loyalty), "loyalty gating")
                tally(failures, f"{label} coupon", ("data-coupon-section" in html) == bool(coupon), "coupon gating")

    closed = render(env, "templates/cart.jinja", **context(cart_state(), store_state(closed_now=True)))
    tally(failures, "store closed", 'href="/checkout"' not in closed, "checkout link stays open")
    tally(failures, "store closed", "Store is closed" in closed, "no closed notice")

    # The gift-card block only appears while no gift card line exists yet.
    with_card = render(
        env,
        "templates/cart.jinja",
        **context(cart_state(gift_card_details={"card_product_id": "9", "card_design": "d"})),
    )
    tally(failures, "gift line", "data-gift-card-display" not in with_card, "gift display next to a gift line")
    return "SectionGating", failures


def prop_progress_width(env):
    failures = []
    cases = {
        "min_not_reached 40": ("min_not_reached", 40, "10.00 SAR"),
        "min_not_reached 100": ("min_not_reached", 100, "0.00 SAR"),
        "applied": ("applied", 100, "0.00 SAR"),
        "max_exceeded 202": ("max_exceeded", 202, "-102.40 SAR"),
        "max_exceeded 350": ("max_exceeded", 350, "-250.00 SAR"),
    }
    for label, (status, pct, remaining) in cases.items():
        cart = cart_state(
            free_shipping_rule={
                "code": "free_shipping",
                "subtotal_condition": {
                    "status": status,
                    "products_subtotal_percentage_from_min": pct,
                    "remaining": remaining,
                },
            }
        )
        block = render(env, "components/cart/shipping-progress.jinja", cart=cart)
        widths = re.findall(r"width:\s*([\d.]+)%", block)
        offsets = re.findall(r"inset-inline-start:\s*calc\(([\d.]+)% - 12px\)", block)
        tally(failures, f"{label} bar", bool(widths), "no progress bar")
        for width in widths + offsets:
            tally(failures, f"{label} width", 0 <= float(width) <= 100, f"width {width}% outside the track")
    return "ProgressWidth", failures


def prop_cart_text_escaping(env):
    """The same promise as js_props.mjs > TotalsTextEscaping, on the server render.

    vitrin renders `.jinja` with select_autoescape(), which only escapes .html/.xml, so
    these templates write API strings raw. The harness reproduces that (autoescape=False);
    the property is about what the page contains, not how the template spells it.
    """
    failures = []
    payload = "<img src=x onerror=window.__pwned=1>"
    cases = {
        "order summary title": ("components/cart/order-summary.jinja",
                                cart_state(totals=[{"code": "sub_totals", "title": payload, "value_string": "1.00 SAR"},
                                                   {"code": "total", "title": "Total", "value_string": "1.00 SAR"}])),
        "order summary value": ("components/cart/order-summary.jinja",
                                cart_state(totals=[{"code": "sub_totals", "title": "Sub", "value_string": "1.00 SAR"},
                                                   {"code": "total", "title": "Total", "value_string": payload}])),
        "coupon code": ("components/cart/coupon-code.jinja", cart_state(coupon={"code": payload})),
        "gift card code": ("components/cart/order-summary.jinja",
                           cart_state(gift_card_details={"code": payload},
                                      totals=[{"code": "sub_totals", "title": "Sub", "value_string": "1.00 SAR"},
                                              {"code": "discount", "title": "Discount", "value_string": "-1.00 SAR"},
                                              {"code": "total", "title": "Total", "value_string": "0.00 SAR"}])),
    }
    for label, (template, cart) in cases.items():
        block = render(env, template, cart=cart, store=store_state())
        tally(failures, label, payload not in block, f"{label} was written into the page as markup")
    return "CartTextEscaping", failures


PROPERTIES = [
    prop_cart_page_shape,
    prop_totals_rows,
    prop_discount_sign,
    prop_coupon_section_state,
    prop_section_gating,
    prop_progress_width,
    prop_cart_text_escaping,
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if not (root / "templates/cart.jinja").exists():
        print(f"not a growth-theme checkout: {root}", file=sys.stderr)
        return 2
    env = make_env(root)

    changed = 0
    for prop in PROPERTIES:
        try:
            name, failures = prop(env)
        except Exception as exc:  # a template that no longer compiles is a change too
            name, failures = prop.__name__.removeprefix("prop_").title().replace("_", ""), [f"raised {exc!r}"]
            got = "error"
        else:
            got = "holds" if not failures else "violation"
        want = EXPECTED[name]
        if got == want:
            print(f"ok       {name}: {got}")
            if got == "violation" and name in FINDINGS:
                print(f"FINDING: {FINDINGS[name]}")
        else:
            changed += 1
            print(f"CHANGED  {name}: recorded {want}, now {got}")
            for line in failures[:3]:
                print(f"         {line}")
    print(
        f"template properties: {len(PROPERTIES)} checks, "
        + ("every outcome matches the record" if changed == 0 else f"{changed} outcome(s) changed")
    )
    return 0 if changed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
