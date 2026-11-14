"""INQUIRY-803 repro: the home categories section must let the browser pick a
category image that fits the slide (srcset + sizes), and keep the 768w file for
high-density screens (CR-32487 raised it from 400 for sharpness).

Renders the real sections/categories.jinja with plain Jinja2, the same harness
as test_inquiry_728_oos_markup.py.

Run: python3 -m pytest tests/repro/test_inquiry_803_category_srcset.py -q
"""
import re

from test_inquiry_728_oos_markup import make_env


def image_url(src, w=None, q=None, f=None):
    return f"https://img.zid.store/img/w={w},q={q},f={f}/{src}"


def render():
    env = make_env()
    env.globals.update(image_url=image_url, safeget=lambda obj, key, default=None: obj.get(key, default))
    cats = [
        {"category": {"id": i, "slug": f"c{i}", "name": f"Cat {i}", "image": f"img{i}.jpg", "image_full_size": f"full{i}.jpg"}}
        for i in range(1, 5)
    ]
    return env.get_template("sections/categories.jinja").render(
        sectionId="s1", settings={"order": 1, "title": "Categories", "categories": cats, "display_more": False}
    )


def category_imgs(html):
    imgs = re.findall(r"<img\b[^>]*>", html, flags=re.S)
    return [i for i in imgs if "full" in i]


def test_harness_rendered_the_four_category_images():
    assert len(category_imgs(render())) == 4


def test_category_images_offer_smaller_files_for_small_slides():
    for img in category_imgs(render()):
        assert 'src="https://img.zid.store/img/w=768,' in img, f"src no longer the 768w file: {img}"
        srcset = re.search(r'srcset="([^"]*)"', img)
        assert srcset, f"no srcset on category image: {img}"
        candidates = re.findall(r"(\S+)\s+(\d+)w\b", srcset.group(1))
        for url, n in candidates:
            assert f"w={n}," in url, f"{n}w descriptor points at another file: {url}"
        widths = sorted(int(n) for _, n in candidates)
        assert widths and widths[0] <= 320, f"no DPR1 candidate for a 304px slide: {widths}"
        assert 768 in widths, f"768w (CR-32487 sharpness) dropped: {widths}"
        sizes = re.search(r'\bsizes="([^"]+)"', img)
        assert sizes, f"no sizes on category image: {img}"
        assert "304px" in sizes.group(1) and "1024px" in sizes.group(1), f"sizes off the CSS slide widths: {sizes.group(1)}"
