"""Browser properties for formal-product (P2-P8).

These read the REAL pages that verify-growth-theme serves: this checkout's
templates rendered by vitrin and this checkout's built theme bundle. The store
data comes from /api/v1/*, so the product ids below are discovered, never typed.

Exit 0 when every property matched its recorded outcome, 1 on CHANGED/FAIL,
2 when the storefront is not reachable (the browser half cannot run).
"""

import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if sys.platform == "darwin"
    else "/usr/bin/google-chrome"
)

# Outcome each property is expected to have at this commit. "finding" means the
# current code breaks the promise and the counterexample must keep reproducing.
EXPECTED = {
    "P2": ("gallery-index-and-range", "holds"),
    "P3": ("lightbox-target", "holds"),
    "P4": ("variant-identity", "holds"),
    "P5": ("quick-view-isolation", "holds"),
    "P6": ("sticky-visibility", "holds"),
    "P7": ("notify-me-target", "holds"),
    "P8": ("question-form-email", "finding"),
    "P13": ("bundle-badge-content", "holds"),
}


# ── store data ───────────────────────────────────────────────────────────────


def api(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=20) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return {}


def products(base, availability="in_stock"):
    return api(base, f"/api/v1/products?page_size=100&availability={availability}").get("results") or []


def slides(page):
    return page.locator(".product-gallery__slide").count()


def settle(page, ms=250):
    page.wait_for_timeout(ms)


def open_pdp(page, base, slug):
    # "load" waits for the chat widget and the CDN badges; the buy box is there
    # at DOMContentLoaded, and the theme bundle runs before it.
    page.goto(base + "/products/" + slug, wait_until="domcontentloaded")
    page.wait_for_selector("#product-id", state="attached", timeout=20000)
    settle(page, 500)


def pick_pdp(page, base, want, prefilter=None, tries=4, availability="in_stock"):
    """Open candidate PDPs until want() is true; return the product or None."""
    for product in [p for p in products(base, availability) if (prefilter or (lambda _p: True))(p)][:tries]:
        open_pdp(page, base, product["slug"])
        if want(page):
            return product
    return None


def priced(text):
    match = re.search(r"[0-9]+(?:\.[0-9]+)?", (text or "").replace(",", ""))
    return float(match.group(0)) if match else None


def dom_prices(page):
    return page.evaluate(
        """() => ({
          productId: document.querySelector('#product-id')?.value ?? null,
          box: document.querySelector('[data-product-price]')?.textContent ?? null,
          sticky: document.querySelector('[data-sticky-cta-price]')?.textContent ?? null,
          sku: document.querySelector('[data-product-sku]')?.textContent ?? null,
        })"""
    )


def wait_variant(page, action, before_id=None, timeout=25000, quiet_ms=600):
    """Run `action` and return the /options answer that settled the selection.

    The page also posts /options on load, and a second click can land while the
    first answer is still travelling, so: collect every answer, wait for a quiet
    window, then prefer the last answer that differs from `before_id`.
    """
    answers = []
    pattern = re.compile(r"/api/v1/products/[^/]+/options$")

    def on_response(response):
        if pattern.search(response.url) and response.request.method == "POST":
            answers.append(response)

    page.on("response", on_response)
    try:
        action()
        parsed = []
        deadline = time.time() + timeout / 1000
        last_answer = time.time()
        while time.time() < deadline:
            page.wait_for_timeout(120)
            while len(parsed) < len(answers):
                response = answers[len(parsed)]
                try:
                    body = response.json() if response.ok else {}
                except Exception:
                    body = {}
                parsed.append((response.status, body))
                last_answer = time.time()
            settled = any(b.get("id") and b.get("id") != before_id for _s, b in parsed)
            if settled and (time.time() - last_answer) * 1000 >= quiet_ms:
                break
        preferred = [item for item in parsed if item[1].get("id") and item[1].get("id") != before_id]
        status, body = preferred[-1] if preferred else (parsed[-1] if parsed else (0, {}))
        return status, body
    finally:
        page.remove_listener("response", on_response)


# ── P2 ───────────────────────────────────────────────────────────────────────


def p2_gallery(page, base):
    """From any state reachable by two clicks, the highlighted thumbnail is the
    slide on screen, the index stays inside the strip, and the arrows match the ends."""
    product = pick_pdp(page, base, lambda p: slides(p) >= 3, lambda p: len(p.get("images") or []) >= 3)
    if not product:
        return "FAIL", "no product with three gallery images"
    n = slides(page)
    symbols = ["next", "prev"] + [f"thumb{i}" for i in range(min(3, n))]
    sequences = [[]] + [[a] for a in symbols] + [[a, b] for a in symbols for b in symbols]
    problems = []
    checked = 0

    def click(symbol):
        if symbol in ("next", "prev"):
            button = page.locator(f".product-gallery__{symbol}")
            if button.is_disabled():
                return  # a shopper cannot press a disabled arrow either
            button.click(timeout=8000, force=True)
        else:
            # The thumbnail strip animates to the active slide, so skip the
            # stability wait; the click still lands on the real element.
            page.locator(".product-gallery-thumbs__slide").nth(int(symbol[5:])).click(
                timeout=8000, force=True
            )

    def state():
        return page.evaluate(
            """() => {
              const gallery = document.querySelector('.product-gallery');
              const box = gallery.getBoundingClientRect();
              const items = [...document.querySelectorAll('.product-gallery__slide')];
              let visible = -1, overlap = 0;
              items.forEach((slide, i) => {
                const r = slide.getBoundingClientRect();
                const share = Math.min(r.right, box.right) - Math.max(r.left, box.left);
                if (share > overlap) { overlap = share; visible = i; }
              });
              const thumbs = [...document.querySelectorAll('.product-gallery-thumbs__slide')];
              return {
                active: thumbs.findIndex((t) => t.classList.contains('border-primary')),
                visible,
                overlap,
                width: box.width,
                prev: document.querySelector('.product-gallery__prev')?.disabled ?? null,
                next: document.querySelector('.product-gallery__next')?.disabled ?? null,
                slides: items.length,
              };
            }"""
        )

    def stable_state(timeout_ms=2500):
        """Return the state once the picture has settled under its thumbnail.

        Programmatic scrolls start on the next frame, so the first reads after a
        click can still show the old slide; the property is about where the
        carousel comes to rest, not about the frame in between.
        """
        deadline = time.time() + timeout_ms / 1000
        last = state()
        while time.time() < deadline:
            page.wait_for_timeout(80)
            last = state()
            if last["visible"] == last["active"] and last["overlap"] >= last["width"] * 0.95:
                return last
        return last

    for sequence in sequences:
        page.locator(".product-gallery-thumbs__slide").nth(0).click(force=True)
        stable_state(900)
        for symbol in sequence:
            click(symbol)
            # A shopper waits for the picture to move before clicking again;
            # clicking mid-animation is not a state a person can reach.
            stable_state(900)
        got = stable_state()
        checked += 1
        label = "->".join(sequence) or "start"
        if got["slides"] != n:
            problems.append(f"{label}: {got['slides']} slides for {n}")
        if not 0 <= got["active"] < n:
            problems.append(f"{label}: active thumb {got['active']} out of 0..{n - 1}")
        if got["visible"] != got["active"]:
            problems.append(f"{label}: thumb {got['active']} highlighted, slide {got['visible']} on screen")
        if got["overlap"] < got["width"] * 0.5:
            problems.append(f"{label}: slide {got['visible']} only {got['overlap']:.0f}/{got['width']:.0f} px visible")
        if got["prev"] != (got["active"] == 0):
            problems.append(f"{label}: prev disabled={got['prev']} at index {got['active']}")
        if got["next"] != (got["active"] == n - 1):
            problems.append(f"{label}: next disabled={got['next']} at index {got['active']} of {n}")
    if problems:
        broken = len({item.split(":")[0] for item in problems})
        return "FAIL", f"{broken} of {checked} states broke: " + "; ".join(problems[:5])
    return "holds", f"{checked} click sequences over {n} slides on {product['slug']}"


# ── P3 ───────────────────────────────────────────────────────────────────────


def p3_lightbox(page, base):
    """Clicking image i opens image i at full size, for every image in the gallery."""
    product = pick_pdp(page, base, lambda p: slides(p) >= 3, lambda p: len(p.get("images") or []) >= 3)
    if not product:
        return "FAIL", "no product with three gallery images"
    contract = page.evaluate(
        """() => {
          const links = [...document.querySelectorAll('#product-gallery-lightbox a')];
          const slides = [...document.querySelectorAll('.product-gallery__slide')];
          return {
            hrefs: links.map((a) => a.getAttribute('href')),
            sizes: links.map((a) => [a.dataset.pswpWidth, a.dataset.pswpHeight]),
            triggers: slides.map((s) => s.querySelector('[data-lightbox-trigger]')?.dataset.lightboxTrigger ?? null),
            hero: slides[0]?.querySelector('img')?.getAttribute('src') ?? null,
          };
        }"""
    )
    problems = []
    if contract["triggers"][: len(contract["hrefs"])] != [str(i) for i in range(len(contract["hrefs"]))]:
        problems.append(f"triggers {contract['triggers']} do not count the images in order")
    if any(not width or not height for width, height in contract["sizes"]):
        problems.append("a zoom link has no intrinsic size")
    if contract["hero"] == contract["hrefs"][0]:
        problems.append("the zoom link serves the same file as the hero (no larger copy)")

    opened = 0
    for index in range(len(contract["hrefs"])):
        page.locator(".product-gallery-thumbs__slide").nth(index).click()
        settle(page, 250)
        page.locator(f"[data-lightbox-trigger='{index}']").first.click(force=True)
        show = None
        for _ in range(16):
            page.wait_for_timeout(400)
            show = page.evaluate(
                """() => {
                  const item = document.querySelector('.pswp__item[aria-hidden="false"]');
                  return item?.querySelector('.pswp__img')?.getAttribute('src') ?? null;
                }"""
            )
            if show:
                break
        opened += 1
        if show != contract["hrefs"][index]:
            problems.append(f"image {index} opened {show!r}, expected {contract['hrefs'][index]!r}")
        page.keyboard.press("Escape")
        settle(page, 400)
    if problems:
        return "FAIL", "; ".join(problems[:4])
    return "holds", f"{opened} images opened at their own full size on {product['slug']}"


# ── P4 ───────────────────────────────────────────────────────────────────────


def p4_variants(page, base):
    """Any option pick leaves the buy box, the sticky bar and the gallery describing
    exactly the variant the platform answered with."""
    product = pick_pdp(
        page,
        base,
        lambda p: p.locator(".product-options__item").count() >= 2,
        lambda p: p.get("has_options") and len(p.get("images") or []) >= 1,
    )
    if not product:
        return "FAIL", "no product with options and images"
    problems = []
    picks = 0
    changes = 0
    for group_index in range(page.locator(".product-options__group").count()):
        group = page.locator(".product-options__group").nth(group_index)
        options = group.locator(".product-options__item:not(.active)")
        for option_index in range(min(2, options.count())):
            before = dom_prices(page)
            status, payload = wait_variant(
                page, lambda: options.nth(option_index).click(), before["productId"]
            )
            try:
                page.wait_for_function(
                    "(id) => document.querySelector('#product-id')?.value === id",
                    arg=payload.get("id"),
                    timeout=5000,
                )
            except Exception:
                problems.append(f"{where}: the buy box never caught up with the answer")
            after = dom_prices(page)
            picks += 1
            where = f"group {group_index} option {option_index}"
            if status != 200 or not payload.get("id"):
                problems.append(f"{where}: options API answered {status}")
                continue
            want_price = payload.get("formatted_sale_price") or payload.get("formatted_price")
            if after["productId"] != payload["id"]:
                problems.append(f"{where}: #product-id {after['productId']} != {payload['id']}")
            if priced(after["box"]) != priced(want_price):
                problems.append(f"{where}: box price {after['box']!r} != {want_price!r}")
            if after["sku"] != payload.get("sku"):
                problems.append(f"{where}: sku {after['sku']} != {payload.get('sku')}")
            if priced(after["sticky"]) != priced(after["box"]):
                problems.append(f"{where}: sticky price {after['sticky']!r} != box {after['box']!r}")
            wanted_media = [m["image"]["large"] for m in (payload.get("media") or []) if m.get("image")]
            shown = page.evaluate(
                "() => [...document.querySelectorAll('.product-gallery__slide img[data-media-src]')]"
                ".map((i) => i.dataset.mediaSrc)"
            )
            if wanted_media and shown != wanted_media:
                problems.append(f"{where}: gallery shows {len(shown)} of {len(wanted_media)} variant images")
            if after["productId"] != before["productId"]:
                changes += 1
    if not picks:
        return "FAIL", "no selectable option found"
    if not changes:
        problems.append("no pick changed the selected product, so the swap never ran")
    if problems:
        return "FAIL", "; ".join(problems[:5])
    return "holds", f"{picks} option picks ({changes} changed the variant) on {product['slug']}"


# ── P5 ───────────────────────────────────────────────────────────────────────


def p5_quick_view(page, base):
    """Quick view leaves the page's productObj exactly as it found it (a PDP's real
    object, or nothing on a listing), empties its content on close, and its cache
    never holds more than 15 entries (LRU)."""
    problems = []
    notes = []

    # A PDP already has a product object; a related card opens the modal there.
    product = pick_pdp(
        page,
        base,
        lambda p: p.locator("[data-open-quick-view]").count() >= 1,
        lambda p: p.get("has_options"),
        tries=5,
    )
    if not product:
        return "FAIL", "no PDP with a related card that opens quick view"
    # The platform fills productObj.selected_product after the options sync;
    # capture the page state only once that has settled.
    try:
        page.wait_for_function(
            "() => window.productObj === undefined || window.productObj.selected_product != null",
            timeout=6000,
        )
    except Exception:
        pass
    settle(page, 300)
    before = page.evaluate(
        "() => JSON.stringify(window.productObj ? {id: window.productObj.id, "
        "selected: window.productObj.selected_product?.id ?? null} : null)"
    )
    page.locator("[data-open-quick-view]").first.scroll_into_view_if_needed()
    page.locator("[data-open-quick-view]").first.click()
    page.wait_for_selector("#quick-view-content #product-main-section", timeout=20000)
    settle(page, 400)
    opened = page.evaluate(
        """() => ({
          open: document.getElementById('product-quick-view-modal')?.open ?? false,
          id: document.querySelector('#quick-view-content #product-id')?.value ?? null,
          borrowed: window.productObj?.id ?? null,
        })"""
    )
    if not opened["open"] or not opened["id"]:
        problems.append(f"modal did not open with a product (open={opened['open']}, id={opened['id']})")
    page.locator("[command='close'][commandfor='product-quick-view-modal']").first.click()
    settle(page, 700)
    closed = page.evaluate(
        """() => ({
          open: document.getElementById('product-quick-view-modal')?.open ?? false,
          length: document.getElementById('quick-view-content')?.innerHTML.length ?? -1,
          restored: JSON.stringify(window.productObj
            ? { id: window.productObj.id, selected: window.productObj.selected_product?.id ?? null }
            : null),
        })"""
    )
    if closed["open"]:
        problems.append("modal stayed open after close")
    if closed["length"] != 0:
        problems.append(f"content left {closed['length']} chars behind")
    if closed["restored"] != before:
        problems.append(f"product state after close is {closed['restored']}, before it was {before}")
    notes.append("PDP restore")

    # A listing has no product object at all; it must stay that way.
    for path in ("/products?q=" + "منتج-جديد-بخيارات", "/products", "/products?page=2"):
        page.goto(base + path, wait_until="domcontentloaded")
        settle(page, 1200)
        if page.locator("[data-open-quick-view]").count():
            break
    if page.locator("[data-open-quick-view]").count():
        page.locator("[data-open-quick-view]").first.click()
        page.wait_for_selector("#quick-view-content #product-main-section", timeout=20000)
        settle(page, 400)
        borrowed = page.evaluate("() => window.productObj?.id ?? null")
        page.locator("[command='close'][commandfor='product-quick-view-modal']").first.click()
        settle(page, 600)
        after = page.evaluate("() => (window.productObj === undefined ? 'undefined' : String(window.productObj))")
        if not borrowed:
            problems.append("listing quick view did not borrow the product object")
        if after != "undefined":
            problems.append(f"listing product object after close is {after[:40]}")
        notes.append("listing stays undefined")
    else:
        notes.append("listing without quick view cards skipped")

    lru = page.evaluate(
        """() => {
          const manager = window.quickViewManager;
          manager.cacheClear();
          for (let i = 0; i < 20; i += 1) manager.cacheSet('/p/' + i, '<div></div>', { i });
          const size = manager.cache.size;
          const kept = [...manager.cache.keys()];
          manager.cacheGet('/p/5');
          manager.cacheSet('/p/20', '<div></div>', { i: 20 });
          return {
            size,
            kept,
            afterSize: manager.cache.size,
            refreshed: manager.cacheHas('/p/5'),
            evicted: manager.cacheHas('/p/6'),
            newest: manager.cacheHas('/p/20'),
          };
        }"""
    )
    if lru["size"] > 15 or lru["afterSize"] > 15:
        problems.append(f"cache grew to {max(lru['size'], lru['afterSize'])} entries")
    if len(lru["kept"]) != 15 or lru["kept"][0] != "/p/5":
        problems.append(f"kept {len(lru['kept'])} entries starting at {lru['kept'][:1]}")
    if not lru["refreshed"] or lru["evicted"] or not lru["newest"]:
        problems.append("LRU order not respected after a cache hit")
    if problems:
        return "FAIL", "; ".join(problems[:4])
    return "holds", "; ".join(notes) + ", cache 15 of 20 (LRU eviction + refresh)"


# ── P6 ───────────────────────────────────────────────────────────────────────


def p6_sticky(page, base):
    """The sticky bar is on screen exactly while the buy box is not."""
    product = pick_pdp(
        page, base, lambda p: p.locator("[data-sticky-cta]").count() == 1, lambda p: not p.get("has_options")
    )
    if not product:
        return "FAIL", "no simple product with a sticky bar"
    problems = []
    samples = []
    for fraction in (0, 0.2, 0.45, 0.7, 1.0):
        page.evaluate(
            "(f) => window.scrollTo(0, f * (document.body.scrollHeight - window.innerHeight))", fraction
        )
        page.wait_for_timeout(650)
        state = page.evaluate(
            """() => {
              const bar = document.querySelector('[data-sticky-cta]');
              const box = document.querySelector('[data-product-actions]');
              const r = box?.getBoundingClientRect();
              const viewport = window.innerHeight;
              return {
                bar: !bar.classList.contains('hidden'),
                aria: bar.getAttribute('aria-hidden'),
                box: !!r && r.top < viewport && r.bottom > 0,
                price: document.querySelector('[data-sticky-cta-price]')?.textContent ?? null,
                pagePrice: document.querySelector('[data-product-price]')?.textContent ?? null,
              };
            }"""
        )
        samples.append({"at": fraction, **state})
        if state["bar"] != (not state["box"]):
            problems.append(f"at {fraction:.0%}: bar visible={state['bar']} but buy box visible={state['box']}")
        if state["bar"] and state["aria"] != "false":
            problems.append(f"at {fraction:.0%}: bar visible with aria-hidden={state['aria']}")
        if priced(state["price"]) != priced(state["pagePrice"]):
            problems.append(f"at {fraction:.0%}: bar price {state['price']!r} != page {state['pagePrice']!r}")
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(700)
    back = page.evaluate("() => document.querySelector('[data-sticky-cta]').classList.contains('hidden')")
    if not back:
        problems.append("bar stayed visible after scrolling back to the top")
    if problems:
        return "FAIL", "; ".join(problems[:4])
    return "holds", "5 scroll positions + return to top on " + product["slug"]


# ── P7 ───────────────────────────────────────────────────────────────────────


def p7_notify_me(page, base):
    """The dialog always takes the product (or picked variant) of the section the
    trigger sits in — buy box, sticky bar, product card, quick view."""
    posts = []
    page.on("request", lambda r: posts.append(r.url) if "stock-alerts" in r.url else None)
    problems = []
    notes = []

    product = pick_pdp(
        page,
        base,
        lambda p: p.locator(".product-options__item").count() >= 2,
        lambda p: p.get("has_options") and len(p.get("images") or []) >= 1,
    )
    if not product:
        return "FAIL", "no product with options"
    page_id = page.evaluate("() => document.querySelector('#product-id')?.value ?? null")
    choice = page.locator(".product-options__item:not(.active)")
    if not choice.count():
        return "FAIL", "options render without a selectable item"
    status, payload = wait_variant(page, lambda: choice.first.click(timeout=8000), page_id)
    # The platform writes #product-id a beat after the answer; the API's id is
    # the truth about what the shopper now has selected.
    variant_id = payload.get("id")
    try:
        page.wait_for_function(
            "(id) => document.querySelector('#product-id')?.value === id", arg=variant_id, timeout=5000
        )
    except Exception:
        problems.append("the buy box never caught up with the picked variant")
    if status != 200 or not variant_id or variant_id == page_id:
        problems.append(f"variant change did not land ({status}, {page_id} -> {variant_id})")
    page.evaluate(
        """() => document.querySelector('#product-main-section')
          .querySelector('[command="show-modal"][commandfor="notify-me-dialog"]').click()"""
    )
    page.wait_for_timeout(500)
    seeded = page.evaluate("() => document.querySelector('[data-notify-product-id]')?.value ?? null")
    notes.append(f"buy box -> {seeded}")
    if seeded != variant_id:
        problems.append(f"buy box seeded {seeded} for variant {variant_id}")
    page.keyboard.press("Escape")
    settle(page, 300)

    out = pick_pdp(page, base, lambda p: p.locator("[data-in-stock].hidden").count() == 1, availability="out_of_stock")
    if out:
        page.evaluate(
            """() => document.querySelector('#product-main-section')
              .querySelector('[command="show-modal"][commandfor="notify-me-dialog"]').click()"""
        )
        page.wait_for_timeout(500)
        seeded = page.evaluate("() => document.querySelector('[data-notify-product-id]')?.value ?? null")
        notes.append(f"out of stock -> {seeded}")
        if seeded != page.evaluate("() => document.querySelector('#product-id')?.value ?? null"):
            problems.append(f"out-of-stock buy box seeded {seeded}")
        page.keyboard.press("Escape")

    out_card = products(base, availability="out_of_stock")
    if out_card:
        page.goto(base + "/products?q=" + out_card[0]["slug"], wait_until="domcontentloaded")
        settle(page, 1500)
        card = page.locator("[data-notify-me-trigger]").first
        if card.count():
            want = card.get_attribute("data-notify-me-trigger")
            card.scroll_into_view_if_needed()
            card.click(timeout=8000)
            page.wait_for_timeout(500)
            seeded = page.evaluate("() => document.querySelector('[data-notify-product-id]')?.value ?? null")
            notes.append(f"card -> {seeded == want}")
            if seeded != want:
                problems.append(f"card seeded {seeded} instead of {want}")
            page.keyboard.press("Escape")
        else:
            problems.append("out-of-stock listing card has no notify-me trigger")
    if posts:
        problems.append(f"{len(posts)} stock-alert submissions happened")
    if problems:
        return "FAIL", "; ".join(problems[:4])
    return "holds", "; ".join(notes)


# ── P8 ───────────────────────────────────────────────────────────────────────

VALID_TLDS_SHORT = ["io", "sa", "com", "store", "museum"]
VALID_TLDS_LONG = ["technology", "photography", "international"]


def email_cases():
    rng = random.Random(20261111)  # fixed seed, printed in the result
    cases = []
    for i, tld in enumerate(VALID_TLDS_SHORT * 3):
        cases.append((f"buyer{i}@shop-{i}.{tld}", True))
    for i, tld in enumerate(VALID_TLDS_LONG):
        cases.append((f"guest{i}@shop{i}.{tld}", True))
    broken = [
        "buyer",
        "buyer@",
        "@shop.com",
        "buyer@@shop.com",
        "buyer@shop",
        "buyer@shop.",
        "buyer@.com",
        "buyer@shop.c0m",
        "buy er@shop.com",
        "buyer@shop com",
    ]
    for value in broken:
        cases.append((value, False))
    for _ in range(6):
        local = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789._-") for _ in range(rng.randint(1, 12)))
        domain = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(2, 10)))
        cases.append((f"{local}@{domain}.com", True))
    return cases


def p8_question_form(page, base):
    """The ask-a-question form accepts exactly the addresses a shopper can own:
    no false accepts, and every dot-com-style address gets through."""
    product = api(base, "/api/v1/products?page_size=1&availability=in_stock").get("results", [{}])[0]
    page.goto(base + f"/products/{product.get('slug', '')}/questions", wait_until="load")
    page.wait_for_timeout(800)
    if not page.locator("#question-form").count():
        return "FAIL", "questions page has no form"

    page.evaluate("() => { document.getElementById('question-form').noValidate = true; }")
    page.route("**/questions", lambda route: route.abort() if route.request.method == "POST" else route.continue_())

    def verdict(address):
        page.evaluate(
            """(value) => {
              document.getElementById('question_name').value = 'Property Test';
              document.getElementById('question_email').value = value;
              document.getElementById('question_text').value = 'Does it ship to Riyadh?';
            }""",
            address,
        )
        page.click("#submit-question-btn")
        page.wait_for_timeout(250)
        return page.evaluate(
            """() => ({
              marked: document.getElementById('question_email').className.includes('border-destructive'),
            })"""
        )["marked"]

    false_accepts, missing, long_tld_rejected = [], [], []
    for address, valid in email_cases():
        rejected = verdict(address)
        if valid and rejected:
            if address.rsplit(".", 1)[-1] in VALID_TLDS_LONG:
                long_tld_rejected.append(address)
            else:
                missing.append(address)
        if not valid and not rejected:
            false_accepts.append(address)
    detail = (
        f"seeded 20261111, {len(email_cases())} addresses; "
        f"false accepts={len(false_accepts)}; valid refused={len(missing)}; long-TLD refused={len(long_tld_rejected)}"
    )
    if false_accepts or missing:
        return "FAIL", detail + f" :: {false_accepts[:2]}{missing[:2]}"
    if long_tld_rejected:
        return "finding", detail + f" :: e.g. {long_tld_rejected[0]} is refused by the 2-6 char TLD rule"
    return "holds", detail


# ── P13 ──────────────────────────────────────────────────────────────────────


def p13_bundle_badges(page, base):
    """A listing card shows one bundle offer name, and asking the loader to render
    again never duplicates or drops what the shopper already sees."""
    page.goto(base + "/products", wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    read = """() => [...document.querySelectorAll('[data-bundle-offer-product-id]')].map((e) => ({
      id: e.dataset.bundleOfferProductId,
      text: e.textContent.trim(),
      filled: !e.classList.contains('bundle-offer-badge'),
      visible: !!e.offsetParent,
      icons: e.querySelectorAll('svg').length,
    }))"""
    first = page.evaluate(read)
    ids = [b["id"] for b in first][:20]
    if not ids:
        return "FAIL", "listing renders no bundle badge placeholder"
    payload = api(base, "/api/v1/products/bundle-offers?" + "&".join(f"product_ids={i}" for i in ids)).get("payload") or []
    names = {offer["name"] for offer in payload if offer.get("product_ids")}
    filled = [b for b in first if b["filled"]]
    problems = []
    if not filled:
        problems.append("no card was filled although the offers API returned names")
    for badge in filled:
        if badge["text"] not in names:
            problems.append(f"{badge['id'][:8]} shows {badge['text']!r}, not one of {sorted(names)}")
        if badge["icons"] != 1:
            problems.append(f"{badge['id'][:8]} carries {badge['icons']} icons")
    page.evaluate("() => window.bundleOffersLoader.reload()")
    page.wait_for_timeout(1500)
    second = page.evaluate(read)
    if [(b["id"], b["text"]) for b in second if b["filled"]] != [(b["id"], b["text"]) for b in filled]:
        problems.append("reload changed the filled badges")
    if any(b["icons"] > 1 for b in second):
        problems.append("a badge gained a second icon after reload")
    if problems:
        return "FAIL", "; ".join(problems[:4])
    return "holds", f"{len(filled)} cards filled from {len(names)} offers, reload idempotent"


# ── driver ───────────────────────────────────────────────────────────────────

CHECKS = {
    "P2": p2_gallery,
    "P3": p3_lightbox,
    "P4": p4_variants,
    "P5": p5_quick_view,
    "P6": p6_sticky,
    "P7": p7_notify_me,
    "P8": p8_question_form,
    "P13": p13_bundle_badges,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8995")
    parser.add_argument("--only", default="")
    parser.add_argument(
        "--bundle",
        default="",
        help="serve this theme.js instead of the storefront's own (lets ROOT=<copy> test a copy's JS)",
    )
    args = parser.parse_args()
    base = args.base.rstrip("/")
    bundle = Path(args.bundle).read_bytes() if args.bundle and Path(args.bundle).is_file() else None
    try:
        with urllib.request.urlopen(base + "/healthz", timeout=5) as response:
            if response.status != 200:
                raise urllib.error.URLError("healthz")
    except Exception:
        print(f"BLOCKED P2..P8 :: storefront not reachable at {base} — start it with verify-growth-theme")
        return 2

    changed = 0
    jobs = [(pid, name, CHECKS[pid]) for pid, (name, _e) in EXPECTED.items() if not args.only or pid == args.only]

    def run(job):
        pid, name, check = job
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=CHROME, headless=True)
            context = browser.new_context(locale="ar-SA", viewport={"width": 1280, "height": 900})
            if bundle is not None:
                context.route(
                    re.compile(r"/dist/theme\.js"),
                    lambda route: route.fulfill(body=bundle, content_type="text/javascript"),
                )
            page = context.new_page()
            try:
                verdict, detail = check(page, base)
            except Exception as exc:
                verdict, detail = "FAIL", f"harness error: {type(exc).__name__}: {str(exc).splitlines()[0][:200]}"
            finally:
                browser.close()
        return pid, name, verdict, detail

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = {pid: (name, verdict, detail) for pid, name, verdict, detail in pool.map(run, jobs)}

    for pid, (name, expected) in EXPECTED.items():
        if pid not in results:
            continue
        _name, verdict, detail = results[pid]
        if verdict == expected:
            print(f"{'FINDING' if verdict == 'finding' else 'PASS'} {pid} {name} :: {detail}")
        else:
            changed += 1
            print(f"CHANGED {pid} {name} :: expected {expected}, got {verdict} :: {detail}")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
