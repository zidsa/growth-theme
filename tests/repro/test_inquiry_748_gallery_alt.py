"""INQUIRY-748 repro: the product gallery prints each image's own alt text.

Also checks that every attribute escaped with `| e` in the gallery and the
sticky bar reads back unchanged when its value has quotes, "&amp;" or "<".

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
# "&amp;" and "<" read back changed unless the template escapes them. No quotes:
# src/srcset come from image_url() unescaped, so a quote would break the tag.
QUOTED_SRC = "https://media.test/box-large.jpg?v=1&amp;tag=<x>"


class Stub(ChainableUndefined):
    def __call__(self, *a, **k):
        return Stub()


class ImageAlts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lightbox, self.slides, self.media_srcs, self.sticky = [], [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "data-pswp-width" in attrs:
            self.lightbox.append(attrs.get("data-alt"))
        elif tag == "img" and "data-lightbox-trigger" in attrs:
            self.slides.append(attrs.get("alt"))
            self.media_srcs.append(attrs.get("data-media-src"))
        elif tag == "img" and "data-sticky-cta-image" in attrs:
            self.sticky.append((attrs.get("data-media-src"), attrs.get("alt")))


def render(template, media):
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
    parser.feed(env.get_template(template).render(product=product))
    return parser


def render_gallery(media):
    return render("components/products/product-gallery.jinja", media)


def image(name, alt_text, large=None):
    return {"image": {"large": large or f"https://media.test/{name}-large.jpg", "full_size": f"https://media.test/{name}.jpg", "thumbnail": f"https://media.test/{name}-thumb.jpg"}, "alt_text": alt_text}


def test_gallery_images_carry_their_own_alt_text():
    alts = render_gallery(
        [image("front", "Lamp from the front"), image("side", None), image("box", QUOTED_ALT), image("top", "")]
    )

    expected = ["Lamp from the front", f"{PRODUCT_NAME} - Image 2", QUOTED_ALT, f"{PRODUCT_NAME} - Image 4"]
    assert alts.slides == expected
    assert alts.lightbox == expected


def test_gallery_media_src_survives_special_characters():
    gallery = render_gallery([image("front", "Front"), image("box", "Box", large=QUOTED_SRC)])

    assert gallery.media_srcs == ["https://media.test/front-large.jpg", QUOTED_SRC]


def test_sticky_bar_escapes_image_src_and_product_name():
    thumb = "https://media.test/thumb.jpg?v=1&amp;tag=<x>"
    media = [{"image": {"thumbnail": thumb}, "alt_text": None}]

    sticky = render("components/products/sticky-product-actions.jinja", media)

    assert sticky.sticky == [(thumb, PRODUCT_NAME)]
