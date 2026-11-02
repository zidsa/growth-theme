"""INQUIRY-728 repro: an in-stock product page must not ship out-of-stock markup.

Renders the real templates/product.jinja (through layout.jinja) with plain
Jinja2. Vitrin-only globals and `vitrin:` includes are stubbed; the stock
conditions under test are the theme's own.

Run: python3 -m pytest tests/repro/test_inquiry_728_oos_markup.py -q
"""
import re
from pathlib import Path

import pytest
from jinja2 import ChainableUndefined, ChoiceLoader, DictLoader, FileSystemLoader, PrefixLoader
from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.sandbox import SandboxedEnvironment

ROOT = Path(__file__).resolve().parents[2]


class Stub(ChainableUndefined):
    def __call__(self, *a, **k):
        return Stub()


class VitrinTagStubs(Extension):
    """Vitrin's own tags render platform head/body/sections; they are out of scope here."""

    tags = {"vitrin_head", "vitrin_body", "template_components", "ai_component"}

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        while parser.stream.current.type != "block_end":
            next(parser.stream)
        return nodes.Output([nodes.TemplateData("")], lineno=lineno)


def make_env():
    stub_vitrin = PrefixLoader({"vitrin": DictLoader({})})
    env = SandboxedEnvironment(
        loader=ChoiceLoader([FileSystemLoader(str(ROOT)), stub_vitrin, DictLoader({})]),
        undefined=Stub,
        autoescape=True,
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols", "jinja2.ext.i18n", VitrinTagStubs],
    )

    real_get = env.get_template

    def get_template(name, *a, **k):
        if isinstance(name, str) and name.startswith("vitrin:"):
            return env.from_string("")
        return real_get(name, *a, **k)

    env.get_template = get_template
    env.install_null_translations(newstyle=True)
    env.globals.update(
        _=lambda s, *a, **k: s,
        url_for=lambda *a, **k: "/",
        safeget=lambda obj, path, default=None: default,
    )
    for name in ("currency", "money", "format_price", "asset_url", "image_url", "tojson_safe", "t", "translate"):
        env.filters.setdefault(name, lambda v, *a, **k: v)
    return env


def in_stock_product():
    selected = {"id": "sel-1", "in_stock": True, "quantity": None, "is_infinite": True}
    return {
        "id": "prod-1",
        "name": "Test Service",
        "slug": "test-service",
        "in_stock": True,
        "is_infinite": True,
        "has_options": False,
        "can_be_preordered": False,
        "effective_preorder_campaign": None,
        "preorder_campaign": None,
        "selected_product": selected,
        "images": [],
        "categories": [],
        "price": 99.0,
        "formatted_price": "99.00 SAR",
    }


def render(env, product):
    return env.get_template("templates/product.jinja").render(
        product=product,
        store={"name": "Test Store", "settings": {}},
        session={"lang": "en", "template": "product_details", "locale": {"language": {"direction": "ltr"}}},
    )


@pytest.fixture(scope="module")
def html():
    return render(make_env(), in_stock_product())


def test_render_reached_the_buy_box(html):
    assert "data-in-stock" in html, "harness did not render the product actions"


def test_exactly_one_notify_me_dialog(html):
    assert len(re.findall(r'id="notify-me-dialog"', html)) == 1


def test_no_out_of_stock_markup_when_can_buy(html):
    assert "data-out-of-stock" not in html
    assert "data-sticky-cta-out-of-stock" not in html


def test_no_notify_me_text_on_product_controls_when_can_buy(html):
    # The dialog itself may stay; the buy box and sticky bar must not offer it.
    controls = re.sub(r'<el-dialog id="notify-me-dialog-wrapper">.*?</el-dialog>', "", html, flags=re.S)
    assert "Notify me when available" not in controls


def test_out_of_stock_product_still_offers_notify_me():
    product = in_stock_product()
    product.update(in_stock=False, is_infinite=False, quantity=0)
    product["selected_product"].update(in_stock=False, is_infinite=False, quantity=0)
    oos = render(make_env(), product)
    assert re.search(r'class="[^"]*"\s+data-out-of-stock', oos)
    assert "data-sticky-cta-out-of-stock" in oos
    assert 'id="notify-me-dialog"' in oos
