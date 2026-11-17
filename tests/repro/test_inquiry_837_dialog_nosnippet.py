"""INQUIRY-837 repro: hidden dialog text must not become a Google snippet.

Google showed "+966 Saudi Arabia ... Syria +963" as a store's search snippet
because the global notify-me dialog server-renders the phone country list on
every page. Google honours data-nosnippet on div/span/section only, so
the dialog must sit inside such a wrapper.

Run: python3 -m pytest tests/repro/test_inquiry_837_dialog_nosnippet.py -q
"""
from html.parser import HTMLParser

import pytest

from test_inquiry_728_oos_markup import in_stock_product, make_env, render


@pytest.fixture(scope="module")
def html():
    return render(make_env(), in_stock_product())


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Snippetable(HTMLParser):
    """Collects text and attribute values Google may use, skipping data-nosnippet subtrees."""

    def __init__(self):
        super().__init__()
        self.stack, self.out = [], []

    def hidden(self):
        return any(self.stack)

    def handle_starttag(self, tag, attrs):
        names = dict(attrs)
        if not self.hidden():
            self.out.extend(v for v in names.values() if v)
        if tag in VOID:
            return
        self.stack.append(self.hidden() or ("data-nosnippet" in names and tag in ("div", "span", "section")))

    def handle_endtag(self, tag):
        if tag not in VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if not self.hidden():
            self.out.append(data)


def snippetable(html):
    p = Snippetable()
    p.feed(html)
    return " ".join(p.out)


def test_page_still_renders_the_country_picker(html):
    assert 'data-country-name="Syria"' in html
    assert "Notify me when available" in html


def test_dialog_country_list_is_not_snippetable(html):
    text = snippetable(html)
    assert "Syria" not in text
    assert "+963" not in text
    assert "Notify me when available" not in text


def test_page_content_stays_snippetable(html):
    assert "Test Service" in snippetable(html)
