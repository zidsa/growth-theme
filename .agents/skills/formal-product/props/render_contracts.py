"""Template contracts for formal-product: render the real .jinja files with
generated data and check the promises the DOM must keep.

Runs on plain Jinja2 (same setup as tests/repro: no autoescape for .jinja, None
prints as ""). No server and no store data: every case is built here, so the
check is the same on any machine and on any store.

Exit 0 when every property matched its recorded outcome; exit 1 with
`CHANGED <property>` when one moved.
"""

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from jinja2 import ChainableUndefined, FileSystemLoader, select_autoescape
from jinja2.sandbox import SandboxedEnvironment


# ── harness ──────────────────────────────────────────────────────────────────


class Data(dict):
    """A dict whose missing keys read as None, like a pydantic model with defaults."""

    def __missing__(self, key):
        return None


class ThemeLoader(FileSystemLoader):
    """Load theme files; swap layout.jinja for the block skeleton and stub vitrin:."""

    LAYOUT = (
        "{% block title %}{% endblock %}"
        "{% block content %}{% endblock %}"
        "{% block footer_scripts %}{% endblock %}"
    )

    def get_source(self, environment, template):
        if template == "layout.jinja":
            return self.LAYOUT, template, lambda: True
        if template.startswith("vitrin:"):
            return "", template, lambda: True
        return super().get_source(environment, template)


def make_env(root):
    def image_url(src, **kwargs):
        # Mirror the CDN transform so a template that forgets to resize is visible.
        width = kwargs.get("w")
        parts = [f"w={width}"] if width else []
        if kwargs.get("h"):
            parts.append(f"h={kwargs['h']}")
        if kwargs.get("f"):
            parts.append(f"f={kwargs['f']}")
        return f"{src}?{'&'.join(parts)}" if parts else src

    env = SandboxedEnvironment(
        loader=ThemeLoader(str(root)),
        undefined=ChainableUndefined,
        autoescape=select_autoescape(),
        finalize=lambda value: "" if value is None else value,
    )
    env.globals.update(
        _=lambda text, *a, **k: text,
        image_url=image_url,
        url_for=lambda endpoint, **kwargs: "/" + str(kwargs.get("slug") or endpoint),
        safeget=lambda obj, path, default=None: default,
    )
    env.filters["asset_url"] = lambda value, *a, **k: value
    return env


class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, {k: (v if v is not None else "") for k, v in attrs}))

    def handle_data(self, data):
        self.text.append(data)

    def with_attr(self, name):
        return [attrs for _tag, attrs in self.tags if name in attrs]

    def visible_text(self):
        return " ".join(" ".join(self.text).split())


def scan(html):
    parser = Scan()
    parser.feed(html)
    return parser


def widths(html):
    return [float(n) for n in re.findall(r"width:\s*([0-9.]+)%", html)]


def has_hidden(attrs):
    return "hidden" in (attrs.get("class") or "").split()


# ── generated data ───────────────────────────────────────────────────────────


def media(count, alt=None):
    items = []
    for i in range(count):
        items.append(
            Data(
                {
                    "image": Data(
                        {
                            "thumbnail": f"https://media.test/{i}-thumb.jpg",
                            "medium": f"https://media.test/{i}-medium.jpg",
                            "large": f"https://media.test/{i}-large.jpg",
                            "full_size": f"https://media.test/{i}.jpg",
                        }
                    ),
                    "alt_text": alt if alt is not None else f"Angle {i}",
                }
            )
        )
    return items


def product(**overrides):
    base = Data(
        {
            "id": "11111111-1111-4111-8111-111111111111",
            "slug": "sample-product",
            "name": "Sample Product",
            "images": [],
            "media": [],
            "rating": None,
            "reviews": None,
            "questions": None,
            "bundle_offer": None,
            "sku": "SKU-1",
            "quantity": 10,
            "is_infinite": False,
            "in_stock": True,
            "has_options": False,
            "has_fields": False,
            "is_taxable": True,
            "can_be_preordered": False,
            "effective_preorder_campaign": None,
            "preorder_campaign": None,
            "preorder_stock_behavior": None,
            "discount_percentage": 0,
            "formatted_price": "100.00 SAR",
            "formatted_sale_price": None,
            "short_description": None,
            "description": None,
            "categories": [],
            "variants": [],
            "related_products": [],
            "shipping_badges": [],
            "badge": None,
            "custom_user_input_fields": [],
            "custom_option_fields": [],
            "product_class": None,
        }
    )
    base.update(overrides)
    if not overrides.get("selected_product"):
        base["selected_product"] = Data(
            {
                "id": base["id"] + "-selected",
                "in_stock": base["in_stock"],
                "quantity": base["quantity"],
                "media": base["images"],
                "attributes": [],
                "formatted_price": base["formatted_price"],
                "formatted_sale_price": base["formatted_sale_price"],
                "sku": base["sku"],
            }
        )
    return base


def rating(counts, total=None, average=4.2):
    """counts = [n1, n2, n3, n4, n5]."""
    data = Data({"average": average, "total_count": total if total is not None else sum(counts)})
    for index, count in enumerate(counts, start=1):
        data[f"ratings_{index}"] = Data({"count": count})
    return data


def review(comment, name="Shopper", created="2026-01-27 21:19:21", stars=5):
    return Data(
        {
            "customer": Data({"name": name}),
            "created_at": created,
            "rating": stars,
            "comment": comment,
            "images": [],
            "reply": None,
        }
    )


def reviews_block(results, total=None, pages=1, page=1):
    return Data(
        {
            "count": total if total is not None else len(results),
            "results": results,
            "pages_count": pages,
            "page": page,
        }
    )


def question(text, name=None, is_anonymous=False, answers=None):
    return Data(
        {
            "question": text,
            "name": name,
            "is_anonymous": is_anonymous,
            "answers": answers or [],
        }
    )


def answer(text):
    return Data({"answer": text, "images": []})


class Url:
    """The bits of request.url the pagination macro asks for."""

    def include_query_params(self, **kwargs):
        return "/products?" + "&".join(f"{k}={v}" for k, v in kwargs.items())


SESSION = Data({"query_params": Data({"page_size": "24", "page": "1"}), "url": Url()})


STORE = Data(
    {
        "name": "Test Store",
        "logo": None,
        "settings": Data({"products": Data({"reviews_enabled": True, "low_stock_label_enabled": False})}),
    }
)


# ── properties ───────────────────────────────────────────────────────────────


def p9_pdp(root):
    """Every PDP renders one buy box whose visible actions match what can be sold,
    and one gallery whose zoom targets are the image media, in order."""
    env = make_env(root)
    template = env.get_template("templates/product.jinja")
    cases = {
        "simple-in-stock": product(images=media(3)),
        "options-in-stock": product(images=media(4), has_options=True),
        "out-of-stock": product(images=media(1), quantity=0, in_stock=False),
        "preorder-out-of-stock": product(
            images=media(2),
            quantity=0,
            in_stock=False,
            can_be_preordered=True,
            effective_preorder_campaign=Data({"id": "c1"}),
        ),
        "no-media": product(images=[]),
    }
    problems = []
    for name, item in cases.items():
        can_buy = bool(item["selected_product"]["in_stock"] or item["can_be_preordered"])
        try:
            html = template.render(product=item, store=STORE, session=SESSION, is_share_link=False)
        except Exception as exc:
            problems.append(f"{name}: render raised {type(exc).__name__}: {exc}")
            continue
        page = scan(html)
        if html.count('id="product-id"') != 1:
            problems.append(f"{name}: {html.count('id=' + chr(34) + 'product-id' + chr(34))} #product-id")
        in_stock = [a for a in page.with_attr("data-in-stock")]
        if len(in_stock) != 1:
            problems.append(f"{name}: {len(in_stock)} data-in-stock blocks")
        elif has_hidden(in_stock[0]) == can_buy:
            problems.append(f"{name}: buy box hidden={has_hidden(in_stock[0])} but can_buy={can_buy}")
        for block in page.with_attr("data-out-of-stock"):
            if has_hidden(block) != can_buy:
                problems.append(f"{name}: out-of-stock hidden={has_hidden(block)} but can_buy={can_buy}")
        forms = page.with_attr("data-add-to-cart-form")
        if len(forms) != 1:
            problems.append(f"{name}: {len(forms)} add-to-cart forms")
        images = item["images"]
        links = [a for a in page.with_attr("data-pswp-width")]
        if len(links) != len(images):
            problems.append(f"{name}: {len(links)} zoom links for {len(images)} images")
        triggers = sorted(int(a["data-lightbox-trigger"]) for a in page.with_attr("data-lightbox-trigger"))
        if triggers != list(range(len(images))):
            problems.append(f"{name}: lightbox triggers {triggers} for {len(images)} images")
        for link in links:
            if "w=1600" not in (link.get("href") or ""):
                problems.append(f"{name}: zoom href is not resized: {link.get('href')}")
            if not link.get("data-pswp-width") or not link.get("data-pswp-height"):
                problems.append(f"{name}: zoom link without intrinsic size")
        sticky_stock = [a for a in page.with_attr("data-sticky-cta-in-stock")]
        if len(sticky_stock) != 1:
            problems.append(f"{name}: {len(sticky_stock)} sticky in-stock blocks")
        elif has_hidden(sticky_stock[0]) == can_buy:
            problems.append(f"{name}: sticky hidden={has_hidden(sticky_stock[0])} but can_buy={can_buy}")
    return ("holds" if not problems else "FAIL"), "; ".join(problems) or f"{len(cases)} products"


def p10_reviews(root):
    """The reviews page renders every distribution without dividing by zero, keeps
    each bar inside its track, and lists exactly the reviews it was given."""
    env = make_env(root)
    template = env.get_template("templates/reviews.jinja")
    cases = {
        "no-ratings": {"rating": rating([0, 0, 0, 0, 0], total=0), "reviews": reviews_block([], total=0)},
        "normal": {
            "rating": rating([2, 1, 3, 4, 5], total=15),
            "reviews": reviews_block([review("Great"), review("Fine", stars=4)]),
        },
        "counts-exceed-total": {
            "rating": rating([9, 9, 9, 9, 9], total=10),
            "reviews": reviews_block([review("Odd")]),
        },
        "many-pages": {
            "rating": rating([0, 0, 0, 0, 2], total=2),
            "reviews": reviews_block([review("Page one")], total=40, pages=4, page=1),
        },
    }
    problems = []
    for name, payload in cases.items():
        item = product(images=media(1), **payload)
        try:
            html = template.render(product=item, store=STORE, session=SESSION)
        except Exception as exc:
            problems.append(f"{name}: render raised {type(exc).__name__}: {exc}")
            continue
        page = scan(html)
        marks = [w for w in widths(html)]
        if any(w < 0 or w > 100 for w in marks):
            problems.append(f"{name}: bar widths outside 0..100: {[w for w in marks if w < 0 or w > 100]}")
        expected = len(payload["reviews"]["results"])
        stamps = page.with_attr("data-time-ago-date")
        if len(stamps) != expected:
            problems.append(f"{name}: {len(stamps)} review timestamps for {expected} reviews")
        if expected and not all(s.get("data-time-ago-date") for s in stamps):
            problems.append(f"{name}: timestamp without its raw date")
        text = page.visible_text()
        if expected == 0 and "No reviews yet" not in text:
            problems.append(f"{name}: empty state missing")
        if payload["reviews"]["pages_count"] > 1 and "page=" not in html:
            problems.append(f"{name}: pagination missing for {payload['reviews']['pages_count']} pages")
    # Every relative timestamp needs the script that fills it. The PDP block
    # ships both the script and its labels; the reviews page does not, so it
    # prints the raw date (the verify-product journey shows this live).
    component = env.get_template("components/products/product-reviews.jinja")
    block = reviews_block([review("Great")], total=1)
    component_html = component.render(
        product=product(rating=rating([0, 0, 0, 0, 1], total=1), reviews=block), store=STORE, session=SESSION
    )
    if "js/time-ago.js" not in component_html:
        problems.append("product-reviews component lost its time-ago script")
    if "data-time-ago-labels" not in component_html:
        problems.append("product-reviews component lost its labels block")
    page_html = template.render(
        product=product(rating=rating([0, 0, 0, 0, 1], total=1), reviews=block), store=STORE, session=SESSION
    )
    stamps = page_html.count("data-time-ago-date")
    finding = ""
    if stamps and "js/time-ago.js" not in page_html:
        finding = (
            f"templates/reviews.jinja emits {stamps} data-time-ago-date values but loads no "
            "js/time-ago.js, so the reviews page shows raw timestamps"
        )
    if problems:
        return "FAIL", "; ".join(problems[:4])
    if finding:
        return "finding", finding + f" ({len(cases)} rating distributions)"
    return "holds", f"{len(cases)} rating distributions, timestamps converted"


def p11_questions(root):
    """An anonymous question never publishes the asker's name, and every answer
    stays under the question it answers."""
    env = make_env(root)
    problems = []
    cases = {
        "mixed": [
            question("Is it waterproof?", name="Secret Shopper", is_anonymous=True,
                     answers=[answer("Yes, IPX7.")]),
            question("Does it fit a 15 inch laptop?", name="Public Shopper",
                     answers=[answer("It fits up to 16 inch.")]),
            question("When does it ship?", name="Third Shopper", answers=[]),
        ],
        "empty": [],
    }
    for template_name, field in (
        ("templates/questions.jinja", "questions"),
        ("components/products/product-questions.jinja", "questions"),
    ):
        template = env.get_template(template_name)
        for case, items in cases.items():
            block = Data({"count": len(items), "results": items, "pages_count": 1, "page": 1})
            try:
                html = template.render(product=product(questions=block), questions=block, store=STORE, session=SESSION)
            except Exception as exc:
                problems.append(f"{template_name}/{case}: render raised {type(exc).__name__}: {exc}")
                continue
            if "Secret Shopper" in html:
                problems.append(f"{template_name}/{case}: anonymous asker's name is in the page")
            if case == "mixed":
                if "Public Shopper" not in html:
                    problems.append(f"{template_name}/{case}: named asker is missing")
                order = [html.find("Is it waterproof?"), html.find("Yes, IPX7."),
                         html.find("Does it fit a 15 inch laptop?")]
                if not (order[0] < order[1] < order[2]):
                    problems.append(f"{template_name}/{case}: answer is not under its own question")
            else:
                text = scan(html).visible_text()
                if "No questions yet" not in text and "no questions yet" not in text.lower():
                    problems.append(f"{template_name}/{case}: empty state missing")
    return ("holds" if not problems else "FAIL"), "; ".join(problems) or "2 templates x 2 fixtures"


def p12_card(root):
    """A product card shows exactly one cart action, and it is the action the
    product's stock and options allow."""
    env = make_env(root)
    template = env.get_template("components/products/product-card.jinja")
    cases = {
        "in-stock-simple": product(images=media(1)),
        "in-stock-options": product(images=media(1), has_options=True),
        "in-stock-fields": product(images=media(1), has_fields=True),
        "out-of-stock": product(images=media(1), quantity=0, in_stock=False),
        "preorder": product(
            images=media(1), quantity=0, in_stock=False, can_be_preordered=True,
            effective_preorder_campaign=Data({"id": "c1"}),
        ),
    }
    problems = []
    for name, item in cases.items():
        try:
            html = template.render(product=item, store=STORE, index=0)
        except Exception as exc:
            problems.append(f"{name}: render raised {type(exc).__name__}: {exc}")
            continue
        page = scan(html)
        add = page.with_attr("data-add-to-cart")
        quick = page.with_attr("data-open-quick-view")
        notify = page.with_attr("data-notify-me-trigger")
        actions = len(add) + len(quick) + len(notify)
        out_of_stock = (
            item["is_infinite"] is False
            and (item["quantity"] or 0) <= 0
            and not item["can_be_preordered"]
        )
        if actions != 1:
            problems.append(f"{name}: {actions} cart actions (add={len(add)} quick={len(quick)} notify={len(notify)})")
        elif out_of_stock and not notify:
            problems.append(f"{name}: out of stock without a notify-me trigger")
        elif not out_of_stock and notify:
            problems.append(f"{name}: notify-me trigger on a buyable product")
        elif not out_of_stock:
            wants_quick = item["has_options"] or item["has_fields"]
            if wants_quick and not quick:
                problems.append(f"{name}: options product without quick view")
            if not wants_quick and not add:
                problems.append(f"{name}: simple product without add to cart")
            if add and add[0].get("data-add-to-cart") != item["id"]:
                problems.append(f"{name}: add to cart carries {add[0].get('data-add-to-cart')}")
            if quick and quick[0].get("data-product-id") != item["id"]:
                problems.append(f"{name}: quick view carries {quick[0].get('data-product-id')}")
        if notify and notify[0].get("data-notify-me-trigger") != item["id"]:
            problems.append(f"{name}: notify me carries {notify[0].get('data-notify-me-trigger')}")
        sold_out_badge = item["in_stock"] is False or (
            item["is_infinite"] is False and item["quantity"] is not None and item["quantity"] <= 0
        )
        has_badge = "OUT OF STOCK" in page.visible_text()
        if has_badge != bool(sold_out_badge):
            problems.append(f"{name}: out-of-stock badge={has_badge} but sold out={bool(sold_out_badge)}")
    return ("holds" if not problems else "FAIL"), "; ".join(problems) or f"{len(cases)} products"


PROPERTIES = [
    ("P9", "pdp-buybox-contract", p9_pdp, "holds"),
    ("P10", "reviews-page-contract", p10_reviews, "finding"),
    ("P11", "questions-anonymity", p11_questions, "holds"),
    ("P12", "product-card-action", p12_card, "holds"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    failed = 0
    for pid, name, check, expected in PROPERTIES:
        if args.only and pid != args.only:
            continue
        try:
            verdict, detail = check(root)
        except Exception as exc:
            verdict, detail = "FAIL", f"harness error: {type(exc).__name__}: {exc}"
        if verdict == expected:
            print(f"{'FINDING' if verdict == 'finding' else 'PASS'} {pid} {name} :: {detail}")
        else:
            failed += 1
            print(f"CHANGED {pid} {name} :: expected {expected}, got {verdict} :: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
