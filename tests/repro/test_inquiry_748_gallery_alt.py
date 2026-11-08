"""INQUIRY-748 repro: the product gallery prints each image's own alt text.

Renders the real components/products/product-gallery.jinja with plain Jinja2,
set up the way vitrin renders theme files: no autoescape for .jinja and None
printed as "".

Run: python3 -m pytest tests/repro/test_inquiry_748_gallery_alt.py -q
"""
from html.parser import HTMLParser
from pathlib import Path

from jinja2 import ChainableUndefined, FileSystemLoader, select_autoescape
from jinja2.sandbox import SandboxedEnvironment

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_NAME = 'Sample 12" Lamp'
QUOTED_ALT = 'Box with "quotes" &amp; <tags>'


class Stub(ChainableUndefined):
    def __call__(self, *a, **k):
        return Stub()


class ImageAlts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lightbox, self.slides = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "data-pswp-width" in attrs:
            self.lightbox.append(attrs.get("data-alt"))
        elif tag == "img" and "data-lightbox-trigger" in attrs:
            self.slides.append(attrs.get("alt"))


def render_gallery(media):
    env = SandboxedEnvironment(
        loader=FileSystemLoader(str(ROOT)),
        undefined=Stub,
        autoescape=select_autoescape(),
        finalize=lambda v: "" if v is None else v,
    )
    env.globals.update(_=lambda s, *a, **k: s, image_url=lambda src, **k: src)
    env.filters["asset_url"] = lambda v, *a, **k: v
    product = {"name": PRODUCT_NAME, "images": media, "selected_product": {"media": media}}
    parser = ImageAlts()
    parser.feed(env.get_template("components/products/product-gallery.jinja").render(product=product))
    return parser


def image(name, alt_text):
    return {"image": {"large": f"https://media.test/{name}-large.jpg", "full_size": f"https://media.test/{name}.jpg", "thumbnail": f"https://media.test/{name}-thumb.jpg"}, "alt_text": alt_text}


def test_gallery_images_carry_their_own_alt_text():
    alts = render_gallery(
        [image("front", "Lamp from the front"), image("side", None), image("box", QUOTED_ALT), image("top", "")]
    )

    expected = ["Lamp from the front", f"{PRODUCT_NAME} - Image 2", QUOTED_ALT, f"{PRODUCT_NAME} - Image 4"]
    assert alts.slides == expected
    assert alts.lightbox == expected
