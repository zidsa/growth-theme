"""Journeys for verify-product: the PDP data contract, carousel/zoom, variants,
sticky bar, quick view, notify-me, reviews, questions and bundle badges.

Each journey is fn(page, base, out, checks) -> bool, loaded by
verify-growth-theme/scripts/drive.py from .agents/skills/verify-*/journeys.py.
Store 1 is shared: the only writes here are cart writes that this file undoes.
"""

import json
import re
import time

# ── helpers ──────────────────────────────────────────────────────────────────

# Messages from these files are this theme's responsibility; every other console
# line on the page comes from third-party widgets (landbot, raqeeb, store chat).
OWN_JS = ("dist/theme.js", "js/question-form.js", "js/time-ago.js")


def _own_errors(page, sink):
    """Record uncaught errors raised by this checkout's own scripts."""

    def on_page_error(err):
        text = f"{err.name}: {err.message}\n{getattr(err, 'stack', '')}"
        if any(name in text for name in OWN_JS):
            sink.append(text.splitlines()[0])

    page.on("pageerror", on_page_error)
    return sink


def api(page, base, path):
    r = page.request.get(base + path)
    return (r.json() if r.ok else None) or {}


def listing(page, base, query="page_size=60&availability=in_stock"):
    return api(page, base, f"/api/v1/products?{query}").get("results") or []


def open_pdp(page, base, slug, checks):
    resp = page.goto(base + "/products/" + slug, wait_until="load")
    if "/auth/login" in page.url:
        checks.setdefault("failure", "PDP redirected to /auth/login: upstream token missing")
    return resp


def counts(page):
    return {
        "slides": page.locator(".product-gallery__slide").count(),
        "thumbs": page.locator(".product-gallery-thumbs__slide").count(),
        "lightbox": page.locator("#product-gallery-lightbox a").count(),
        "options": page.locator(".product-options__group").count(),
        "option_items": page.locator(".product-options__item").count(),
    }


def find_pdp(page, base, checks, want, tries=6, availability="in_stock", prefilter=None):
    """Open candidate PDPs until `want(counts, page)` holds; record every attempt.

    The listing API already tells us has_options/has_fields/image count, so the
    prefilter keeps this to one or two page loads instead of six.
    """
    seen = []
    products = listing(page, base, f"page_size=100&availability={availability}")
    if prefilter:
        products = [p for p in products if prefilter(p)]
        checks["candidates"] = len(products)
    for product in products:
        open_pdp(page, base, product["slug"], checks)
        shape = counts(page)
        shape["slug"] = product["slug"]
        seen.append(shape)
        if want(shape, page):
            checks["picked"] = {"id": product["id"], "slug": product["slug"], "shape": shape}
            return product
        if len(seen) >= tries:
            break
    checks["attempts"] = [{k: v for k, v in s.items() if k != "slug"} for s in seen]
    checks["failure"] = f"no product in {tries} matched the shape this journey needs"
    return None


def _money(text):
    """The buy box and the API both print a price; compare the number, not its dressing."""
    if not text:
        return None
    match = re.search(r"[0-9]+(?:\.[0-9]+)?", str(text).replace(",", ""))
    return float(match.group(0)) if match else None


def thumb_state(page):
    return page.evaluate(
        """() => {
          const thumbs = [...document.querySelectorAll('.product-gallery-thumbs__slide')];
          return {
            active: thumbs.findIndex((t) => t.classList.contains('border-primary')),
            n: thumbs.length,
            prevDisabled: document.querySelector('.product-gallery__prev')?.disabled ?? null,
            nextDisabled: document.querySelector('.product-gallery__next')?.disabled ?? null,
          };
        }"""
    )


def page_prices(page):
    return page.evaluate(
        """() => ({
          box: document.querySelector('[data-product-price]')?.textContent.trim() ?? null,
          sticky: document.querySelector('[data-sticky-cta-price]')?.textContent.trim() ?? null,
          sku: document.querySelector('[data-product-sku]')?.textContent.trim() ?? null,
          productId: document.querySelector('#product-id')?.value ?? null,
        })"""
    )


def clear_cart(page, base, checks):
    checks["cart_cleared_status"] = page.request.delete(base + "/api/v1/cart/items").status


# ── journeys ─────────────────────────────────────────────────────────────────


def product_pdp(page, base, out, checks):
    """A PDP renders the buy box from the store's own data, with a gallery."""
    errors = _own_errors(page, [])
    product = find_pdp(
        page,
        base,
        checks,
        lambda shape, _page: shape["slides"] >= 1 and shape["options"] >= 1,
        prefilter=lambda p: p.get("has_options") and len(p.get("images") or []) >= 1,
    )
    if not product:
        return False

    prices = page_prices(page)
    checks.update(
        {
            "url": page.url,
            "counts": counts(page),
            "prices": prices,
            "main_section": page.locator("#product-main-section").count(),
            "sticky_bar": page.locator("[data-sticky-cta]").count(),
            "in_stock_visible": page.locator("[data-in-stock]:not(.hidden)").count() > 0,
            "hero_loaded": page.evaluate(
                "() => { const i = document.querySelector('.product-gallery__slide img');"
                " return !!i && i.complete && i.naturalWidth > 0; }"
            ),
            "title": page.title(),
        }
    )
    page.screenshot(path=out / "1-pdp.png", full_page=False)
    checks["own_js_errors"] = errors
    return (
        checks["main_section"] == 1
        and checks["counts"]["slides"] >= 1
        and bool(prices["box"])
        and checks["in_stock_visible"]
        and checks["hero_loaded"]
        and not errors
    )


def product_gallery(page, base, out, checks):
    """Carousel, thumbnails and zoom agree on which image is which."""
    product = find_pdp(
        page,
        base,
        checks,
        lambda shape, _p: shape["slides"] >= 3,
        prefilter=lambda p: len(p.get("images") or []) >= 3,
    )
    if not product:
        return False

    start = thumb_state(page)
    # next / prev walk the thumbnail highlight
    page.locator(".product-gallery__next").click()
    page.wait_for_timeout(700)
    after_next = thumb_state(page)
    page.screenshot(path=out / "1-after-next.png")
    page.locator(".product-gallery__prev").click()
    page.wait_for_timeout(700)
    after_prev = thumb_state(page)
    # clicking a thumbnail at k activates k
    page.locator(".product-gallery-thumbs__slide").nth(2).click()
    page.wait_for_timeout(700)
    after_thumb = thumb_state(page)

    contract = page.evaluate(
        """() => {
          const slides = [...document.querySelectorAll('.product-gallery__slide')];
          const links = [...document.querySelectorAll('#product-gallery-lightbox a')];
          const triggers = slides
            .map((s) => s.querySelector('[data-lightbox-trigger]'))
            .filter(Boolean)
            .map((t) => Number(t.getAttribute('data-lightbox-trigger')));
          return {
            triggers,
            links: links.length,
            hrefs: links.map((a) => a.getAttribute('href')),
            pswpSizes: links.filter((a) => a.dataset.pswpWidth && a.dataset.pswpHeight).length,
            mainSrc: slides[0]?.querySelector('img')?.getAttribute('src'),
          };
        }"""
    )
    checks.update(
        {
            "counts": counts(page),
            "thumb_start": start,
            "thumb_after_next": after_next,
            "thumb_after_prev": after_prev,
            "thumb_after_click_2": after_thumb,
            "lightbox": contract,
        }
    )
    sequential = contract["triggers"] == list(range(contract["links"]))
    moved = (
        after_next["active"] == start["active"] + 1
        and after_prev["active"] == start["active"]
        and after_thumb["active"] == 2
    )
    disabled_ok = start["prevDisabled"] is True and start["nextDisabled"] is False

    # Zoom: the picture the shopper clicked must be the picture that opens.
    zoom_ok = "not-opened"
    if contract["links"] >= 1:
        index = min(2, contract["links"] - 1)
        page.locator(".product-gallery-thumbs__slide").nth(index).click()
        page.wait_for_timeout(700)
        trigger = page.locator(f"[data-lightbox-trigger='{index}']").first
        trigger.click(force=True)
        opened = False
        for _ in range(10):
            page.wait_for_timeout(500)
            if page.locator(".pswp").count():
                opened = True
                break
        if opened:
            try:
                page.wait_for_function(
                    """() => {
                      const item = document.querySelector('.pswp__item[aria-hidden="false"]');
                      return !!item?.querySelector('.pswp__img')?.getAttribute('src');
                    }""",
                    timeout=12000,
                )
            except Exception as exc:  # pragma: no cover - only on a slow CDN
                checks["zoom_wait_error"] = type(exc).__name__
            shown = page.evaluate(
                """() => {
                  const item = document.querySelector('.pswp__item[aria-hidden="false"]');
                  return item?.querySelector('.pswp__img')?.getAttribute('src') ?? null;
                }"""
            )
            checks["zoom_shown_src"] = shown
            checks["zoom_expected_src"] = contract["hrefs"][index]
            zoom_ok = shown == contract["hrefs"][index]
            page.screenshot(path=out / "2-lightbox.png")
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
        else:
            # PhotoSwipe is imported from jsdelivr at click time; without the CDN
            # there is nothing to open, and the index contract above still holds.
            checks["zoom_skipped"] = "photoswipe did not open (jsdelivr unreachable?)"
    checks["zoom_ok"] = zoom_ok
    return (
        sequential
        and moved
        and disabled_ok
        and contract["links"] == len(contract["triggers"])
        and contract["pswpSizes"] == contract["links"]
        and zoom_ok in (True, "not-opened")
    )


def product_variants(page, base, out, checks):
    """Picking an option swaps the whole buy box to the variant the API returned."""
    product = find_pdp(
        page,
        base,
        checks,
        lambda shape, p: shape["options"] >= 1
        and any(
            p.locator(".product-options__group").nth(i).locator(".product-options__item").count() >= 2
            for i in range(shape["options"])
        ),
        prefilter=lambda p: p.get("has_options") and len(p.get("images") or []) >= 1,
    )
    if not product:
        return False

    group = page.locator(".product-options__group").filter(
        has=page.locator(".product-options__item >> nth=1")
    ).first
    before = page_prices(page)
    page.evaluate(
        "() => { window.__variantEvents = [];"
        "window.addEventListener('product:variant-changed',"
        " (e) => window.__variantEvents.push(e.detail?.selectedProduct?.id ?? null)); }"
    )
    picked = group.locator(".product-options__item:not(.active)").first
    picked_label = picked.inner_text().strip()
    with page.expect_response(
        lambda r: re.search(r"/api/v1/products/[^/]+/options$", r.url) and r.request.method == "POST",
        timeout=20000,
    ) as pending:
        picked.click()
    response = pending.value
    payload = response.json() if response.ok else {}
    page.wait_for_timeout(1500)
    after = page_prices(page)
    checks.update(
        {
            "option_post_status": response.status,
            "payload": {
                "id": payload.get("id"),
                "price": payload.get("formatted_sale_price") or payload.get("formatted_price"),
                "sku": payload.get("sku"),
                "media": len(payload.get("media") or []),
            },
            "before": before,
            "after": after,
            "variant_events": page.evaluate("window.__variantEvents"),
            "picked_label": picked_label,
            "active_labels": [t.strip() for t in page.locator(".product-options__item.active").all_inner_texts()],
            "gallery_media_srcs": page.evaluate(
                "() => [...document.querySelectorAll('.product-gallery__slide img[data-media-src]')]"
                ".map((i) => i.dataset.mediaSrc)"
            ),
            "sticky_options": page.inner_text("[data-sticky-cta-options]").strip()
            if page.locator("[data-sticky-cta-options]").count()
            else None,
        }
    )
    page.screenshot(path=out / "1-variant.png")
    expected_media = [m["image"]["large"] for m in (payload.get("media") or []) if m.get("image")]
    checks["expected_media"] = expected_media
    changed = after["productId"] == payload.get("id") and payload.get("id") != before["productId"]
    priced = _money(after["box"]) == _money(payload.get("formatted_sale_price") or payload.get("formatted_price"))
    sku_ok = after["sku"] == payload.get("sku")
    mirrored = after["sticky"] == after["box"]
    media_ok = not expected_media or checks["gallery_media_srcs"] == expected_media
    return (
        response.ok
        and picked_label in checks["active_labels"]
        and changed
        and priced
        and sku_ok
        and mirrored
        and media_ok
        and payload.get("id") in checks["variant_events"]
    )


def product_sticky_bar(page, base, out, checks):
    """The sticky bar follows the buy box and buys the same thing."""
    product = find_pdp(
        page,
        base,
        checks,
        lambda shape, _p: shape["slides"] >= 1 and shape["options"] == 0,
        prefilter=lambda p: not p.get("has_options") and not p.get("has_fields"),
    )
    if not product:
        return False

    at_top = page.evaluate(
        """() => { const b = document.querySelector('[data-sticky-cta]');
          return {hidden: b.classList.contains('hidden'), aria: b.getAttribute('aria-hidden')}; }"""
    )
    page.screenshot(path=out / "1-top.png")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(900)
    at_bottom = page.evaluate(
        """() => { const b = document.querySelector('[data-sticky-cta]');
          return {hidden: b.classList.contains('hidden'), aria: b.getAttribute('aria-hidden'),
                  height: b.getBoundingClientRect().height}; }"""
    )
    page.screenshot(path=out / "2-bottom.png")
    prices = page_prices(page)

    with page.expect_response(
        lambda r: r.url.endswith("/api/v1/cart/items") and r.request.method == "POST", timeout=20000
    ) as pending:
        page.locator("[data-sticky-cta-add-to-cart]").click()
    added = pending.value
    page.wait_for_timeout(400)
    button_states = page.evaluate(
        """() => ({
          success: !document.querySelector('[data-sticky-cta-btn-success]').classList.contains('hidden'),
          loading: !document.querySelector('[data-sticky-cta-btn-loading]').classList.contains('hidden'),
        })"""
    )
    page.screenshot(path=out / "3-added.png")
    page.wait_for_timeout(1800)
    settled = page.evaluate(
        """() => ({
          default: !document.querySelector('[data-sticky-cta-btn-default]').classList.contains('hidden'),
          disabled: document.querySelector('[data-sticky-cta-add-to-cart]').disabled,
        })"""
    )
    cart = page.request.get(base + "/api/v1/cart")
    body = cart.json() if cart.ok else {}
    want = product["id"].replace("-", "")
    in_cart = any(
        str(p.get("product_id", "")).replace("-", "") == want for p in body.get("products", [])
    )
    checks.update(
        {
            "at_top": at_top,
            "at_bottom": at_bottom,
            "prices": prices,
            "add_status": added.status,
            "button_after_add": button_states,
            "button_settled": settled,
            "in_cart": in_cart,
            "cart_status": cart.status,
        }
    )
    clear_cart(page, base, checks)
    same_price = prices["sticky"] == prices["box"]
    return (
        at_top["hidden"]
        and at_top["aria"] == "true"
        and not at_bottom["hidden"]
        and at_bottom["aria"] == "false"
        and at_bottom["height"] > 0
        and same_price
        and added.ok
        and in_cart
        and button_states["success"]
        and settled["default"]
        and not settled["disabled"]
    )


def product_quick_view(page, base, out, checks):
    """Quick view borrows the PDP for a modal and gives the page its data back."""
    candidates = ["/products?q=" + "منتج-جديد-بخيارات", "/products", "/products?page=2"]
    found = None
    for path in candidates:
        page.goto(base + path, wait_until="load")
        page.wait_for_timeout(1200)
        if page.locator("[data-open-quick-view]").count():
            found = path
            break
        page.screenshot(path=out / f"scan-{len(checks)}.png")
    checks["listing"] = found
    checks["cards"] = page.locator("[data-product-card]").count()
    if not found:
        checks["failure"] = "no listing showed a card with data-open-quick-view"
        return False

    button = page.locator("[data-open-quick-view]").first
    card = button.locator("xpath=ancestor::*[@data-product-card]")
    href = card.locator("a[href]").first.get_attribute("href")
    before = page.evaluate("() => window.productObj === undefined ? null : window.productObj")
    checks["card_href"] = href

    button.click()
    modal = page.locator("#product-quick-view-modal")
    content = page.locator("#quick-view-content")
    page.wait_for_selector("#quick-view-content #product-main-section", timeout=20000)
    page.wait_for_timeout(600)
    opened = page.evaluate(
        """() => ({
          open: document.getElementById('product-quick-view-modal')?.open ?? false,
          sections: document.querySelectorAll('#quick-view-content #product-main-section').length,
          productId: document.querySelector('#quick-view-content #product-id')?.value ?? null,
          price: document.querySelector('#quick-view-content [data-product-price]')?.textContent.trim() ?? null,
          link: document.getElementById('quick-view-product-link')?.getAttribute('href'),
          footerHidden: document.getElementById('quick-view-footer')?.classList.contains('hidden'),
        })"""
    )
    page.screenshot(path=out / "1-quick-view.png", full_page=False)
    page.locator("[command='close'][commandfor='product-quick-view-modal']").first.click()
    page.wait_for_timeout(700)
    closed = page.evaluate(
        """() => ({
          open: document.getElementById('product-quick-view-modal')?.open ?? false,
          contentLength: document.getElementById('quick-view-content')?.innerHTML.length ?? -1,
          productObj: window.productObj === undefined ? null : window.productObj,
        })"""
    )
    checks.update({"opened": opened, "closed": closed})
    return (
        opened["open"]
        and opened["sections"] == 1
        and bool(opened["productId"])
        and not opened["footerHidden"]
        and opened["link"] == href
        and not closed["open"]
        and closed["contentLength"] == 0
        and closed["productObj"] == before
    )


def product_notify_me(page, base, out, checks):
    """Every notify-me trigger seeds the dialog with its own product."""
    product = find_pdp(
        page,
        base,
        checks,
        lambda shape, p: p.locator("[command='show-modal'][commandfor='notify-me-dialog']").count() >= 1,
        availability="out_of_stock",
    )
    if not product:
        return False

    posts = []
    page.on(
        "request",
        lambda r: posts.append(r.url) if "stock-alerts" in r.url and r.method == "POST" else None,
    )
    page_id = page.evaluate("document.querySelector('#product-id')?.value ?? null")
    triggers = page.locator("[command='show-modal'][commandfor='notify-me-dialog']")
    checks["triggers"] = triggers.count()
    checks["page_product_id"] = page_id

    triggers.first.click()
    page.wait_for_timeout(700)
    buy_box = page.evaluate(
        """() => ({open: document.getElementById('notify-me-dialog')?.open ?? false,
                  productId: document.querySelector('[data-notify-product-id]')?.value ?? null})"""
    )
    page.screenshot(path=out / "1-dialog.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(900)
    sticky = page.locator("[data-sticky-cta] [command='show-modal'][commandfor='notify-me-dialog']")
    sticky_target = None
    if sticky.count():
        sticky.first.click()
        page.wait_for_timeout(700)
        sticky_target = page.evaluate(
            "document.querySelector('[data-notify-product-id]')?.value ?? null"
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

    # A product card on a listing page carries its own id.
    listing_resp = api(page, base, "/api/v1/products?page_size=60&availability=out_of_stock")
    card_target = None
    if listing_resp.get("results"):
        page.goto(base + "/products", wait_until="load")
        page.wait_for_timeout(1500)
        card_trigger = page.locator("[data-notify-me-trigger]").first
        if card_trigger.count():
            want = card_trigger.get_attribute("data-notify-me-trigger")
            card_trigger.scroll_into_view_if_needed()
            card_trigger.click()
            page.wait_for_timeout(700)
            card_target = page.evaluate(
                "document.querySelector('[data-notify-product-id]')?.value ?? null"
            )
            checks["card_want"] = want
            page.screenshot(path=out / "2-card-dialog.png")
            page.keyboard.press("Escape")

    checks.update({"buy_box": buy_box, "sticky": sticky_target, "card": card_target, "posts": posts})
    return (
        buy_box["open"]
        and buy_box["productId"] == page_id
        and (sticky_target in (None, page_id))
        and (card_target in (None, checks.get("card_want")))
        and not posts
    )


def product_reviews(page, base, out, checks):
    """The reviews page lists the reviews the API returns, in relative time."""
    picked = None
    for product in listing(page, base, "page_size=60")[:30]:
        data = api(page, base, f"/api/v1/products/{product['id']}/reviews?page_size=5")
        if data.get("count"):
            picked = (product, data)
            break
    if not picked:
        checks["failure"] = "no product with reviews in the first 30 (store data changed)"
        return False

    product, data = picked
    resp = page.goto(base + f"/products/{product['slug']}/reviews", wait_until="load")
    page.wait_for_timeout(1500)
    rendered = page.evaluate(
        """() => {
          const stamps = [...document.querySelectorAll('[data-time-ago-date]')];
          return {
            stamps: stamps.length,
            first: stamps[0] ? {raw: stamps[0].dataset.timeAgoDate, text: stamps[0].textContent.trim()} : null,
            rawLeft: stamps.some((s) => s.textContent.trim() === s.dataset.timeAgoDate),
            widths: [...document.querySelectorAll('[style*="width"]')]
              .map((e) => parseFloat((e.getAttribute('style').match(/width:\\s*([\\d.]+)%/) || [])[1]))
              .filter((n) => !Number.isNaN(n)),
            empty: document.body.innerText.includes('no reviews yet'),
            allLink: [...document.querySelectorAll('a[href$="/reviews"]')].length,
          };
        }"""
    )
    page.screenshot(path=out / "1-reviews.png", full_page=True)

    # The PDP block for the same product does convert: that isolates the page's
    # missing script from a broken time-ago module.
    open_pdp(page, base, product["slug"], checks)
    page.wait_for_timeout(1200)
    pdp_stamps = page.evaluate(
        """() => [...document.querySelectorAll('[data-time-ago-date]')].map((e) => ({
          raw: e.dataset.timeAgoDate,
          text: e.textContent.trim(),
        }))"""
    )
    checks["pdp_stamps"] = pdp_stamps[:3]
    checks["pdp_converts"] = bool(pdp_stamps) and all(
        s["text"] and s["text"] != s["raw"] for s in pdp_stamps
    )
    page.screenshot(path=out / "2-pdp-reviews.png", full_page=True)
    if rendered["rawLeft"]:
        checks["finding"] = (
            "templates/reviews.jinja renders review-card's data-time-ago-date but loads no "
            "js/time-ago.js and no label block, so the reviews page shows raw timestamps "
            "('2026-01-27 21:19:21') while the PDP block converts the same data to '9 months ago'."
        )
    checks.update(
        {
            "product": {"id": product["id"], "slug": product["slug"]},
            "api_count": data.get("count"),
            "api_page_results": len(data.get("results") or []),
            "status": resp.status,
            "rendered": rendered,
        }
    )
    conds = {
        "status_200": resp.status == 200,
        "one_stamp_per_review": rendered["stamps"] == len(data.get("results") or []),
        "pdp_converts": checks["pdp_converts"],
        "page_converts_stamps": not rendered["rawLeft"],
        "bar_widths_0_100": all(0 <= w <= 100 for w in rendered["widths"]),
        "first_stamp_text": bool(rendered["first"] and rendered["first"]["text"]),
        "not_empty_state": not rendered["empty"],
    }
    checks["failed_checks"] = [k for k, ok in conds.items() if not ok]
    return not checks["failed_checks"]


def product_questions(page, base, out, checks):
    """The questions page renders its list, keeps askers anonymous, and never
    posts a question this journey did not fill in."""
    picked = None
    for product in listing(page, base, "page_size=60")[:40]:
        data = api(page, base, f"/api/v1/products/{product['id']}/questions")
        if data.get("count"):
            picked = (product, data)
            break
    if not picked:
        checks["failure"] = "no product with questions (store data changed)"
        return False

    product, data = picked
    first = data["results"][0]
    posts = []
    page.on(
        "request",
        lambda r: posts.append(r.url) if "/questions" in r.url and r.method == "POST" else None,
    )
    resp = page.goto(base + f"/products/{product['slug']}/questions", wait_until="load")
    page.wait_for_timeout(1200)
    rendered = page.evaluate(
        """() => {
          const form = document.getElementById('question-form');
          return {
            form: !!form,
            productId: form?.dataset.productId ?? null,
            text: document.body.innerText,
            lines: document.querySelectorAll('.divide-y > div').length,
            submit: !!document.getElementById('submit-question-btn'),
          };
        }"""
    )
    page.screenshot(path=out / "1-questions.png", full_page=True)

    # Empty submit: the browser's required checks stop it, and the form still
    # sends nothing. Then a filled form passes the same check without posting.
    page.click("#submit-question-btn")
    page.wait_for_timeout(600)
    validation = page.evaluate(
        """() => {
          const email = document.getElementById('question_email');
          const name = document.getElementById('question_name');
          const text = document.getElementById('question_text');
          const form = document.getElementById('question-form');
          return {
            emptyInvalid: !form.checkValidity(),
            emailInvalid: !email.validity.valid,
            nameInvalid: !name.validity.valid,
            textInvalid: !text.validity.valid,
            emailMarked: email.className.includes('border-destructive'),
          };
        }"""
    )
    page.screenshot(path=out / "2-validation.png")
    can_submit = page.evaluate(
        """() => {
          document.getElementById('question_name').value = 'Journey Value';
          document.getElementById('question_email').value = 'buyer@example.com';
          document.getElementById('question_text').value = 'Does this ship to Riyadh?';
          return document.getElementById('question-form').checkValidity();
        }"""
    )
    anonymous_leak = bool(first.get("is_anonymous") and first.get("name") and first["name"] in rendered["text"])
    checks.update(
        {
            "product": {"id": product["id"], "slug": product["slug"]},
            "api_count": data.get("count"),
            "status": resp.status,
            "rendered": {"form": rendered["form"], "submit": rendered["submit"], "lines": rendered["lines"]},
            "form_product_id": rendered["productId"],
            "validation": validation,
            "accepts_filled_form": can_submit,
            "anonymous_name_in_page": anonymous_leak,
            "posts": posts,
        }
    )
    return (
        resp.status == 200
        and rendered["form"]
        and rendered["submit"]
        and validation["emptyInvalid"]
        and validation["emailInvalid"]
        and validation["nameInvalid"]
        and validation["textInvalid"]
        and can_submit
        and not anonymous_leak
        and not posts
    )


def product_bundle_offers(page, base, out, checks):
    """A bundle badge appears only for products the bundle API puts in an offer."""
    page.goto(base + "/products", wait_until="load")
    page.wait_for_timeout(2500)
    rendered = page.evaluate(
        """() => [...document.querySelectorAll('[data-bundle-offer-product-id]')].map((e) => ({
          id: e.dataset.bundleOfferProductId,
          text: e.textContent.trim(),
          visible: !!e.offsetParent,
          icons: e.querySelectorAll('svg').length,
        }))"""
    )
    visible = [b for b in rendered if b["visible"]]
    ids = [b["id"] for b in rendered]
    payload = []
    if ids:
        data = api(page, base, "/api/v1/products/bundle-offers?" + "&".join(f"product_ids={i}" for i in ids[:20]))
        payload = data.get("payload") or []
    named = {o["name"] for o in payload if o.get("product_ids")}
    checks.update(
        {
            "badges": len(rendered),
            "visible": visible[:8],
            "visible_count": len(visible),
            "offer_names": sorted(named),
        }
    )
    page.screenshot(path=out / "1-badges.png", full_page=False)
    honest_text = all(b["text"] in named for b in visible) if named else not visible
    return bool(rendered) and honest_text and all(b["icons"] <= 1 for b in visible)


JOURNEYS = {
    "product-pdp": product_pdp,
    "product-gallery": product_gallery,
    "product-variants": product_variants,
    "product-sticky-bar": product_sticky_bar,
    "product-quick-view": product_quick_view,
    "product-notify-me": product_notify_me,
    "product-reviews": product_reviews,
    "product-questions": product_questions,
    "product-bundle-offers": product_bundle_offers,
}

# Recorded product bugs (drive.py exits 0 with FINDING while exactly these checks fail).
KNOWN = {
    "product-reviews": (
        {"page_converts_stamps"},
        "templates/reviews.jinja loads no js/time-ago.js, so the reviews page shows raw timestamps the PDP converts",
    ),
}
