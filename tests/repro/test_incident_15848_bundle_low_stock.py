"""INCIDENT-15848 repro: a dynamic bundle's quantity is a 1/0 in-stock flag, so its page never carries a low-stock badge.

The badge must be absent, not just hidden: on load the platform calls productOptionsChanged,
and variants.js shows any [data-low-stock-badge] it finds when quantity < threshold.

Run: python3 -m pytest tests/repro/test_incident_15848_bundle_low_stock.py -q
"""
import re

import pytest

from test_inquiry_728_oos_markup import in_stock_product, make_env

LOW_STOCK_SETTINGS = {"products": {"low_stock_label_enabled": True, "low_stock_quantity_threshold": 5}}


def render_with_quantity_one(product_class):
    product = in_stock_product()
    product["product_class"] = product_class
    product["selected_product"].update(is_infinite=False, quantity=1)
    return make_env().get_template("templates/product.jinja").render(
        product=product,
        store={"name": "Test Store", "settings": LOW_STOCK_SETTINGS},
        session={"lang": "en", "template": "product_details", "locale": {"language": {"direction": "ltr"}}},
    )


def test_dynamic_bundle_has_no_low_stock_badge():
    html = render_with_quantity_one("dynamic_bundle")
    assert "data-in-stock" in html, "harness did not render the product actions"
    assert "data-low-stock-badge" not in html


@pytest.mark.parametrize("product_class", [None, "voucher"])
def test_other_products_still_show_low_stock_badge(product_class):
    badge = re.search(r'data-low-stock-badge\s+class="([^"]*)"', render_with_quantity_one(product_class))
    assert badge, "low-stock badge missing"
    assert "!hidden" not in badge.group(1).split()
