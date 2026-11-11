"""Cart-group journeys for verify-growth-theme's drive.py.

Each journey: fn(page, base, out, checks) -> bool. Loaded by
.agents/skills/verify-growth-theme/scripts/drive.py, which imports JOURNEYS from every
.agents/skills/verify-*/journeys.py.

Store 1 is shared. Every journey empties the cart in a finally block; none checks out,
logs in, writes account data or sends OTPs.
"""

import json
import re

PATCH_TIMEOUT = 30000
SWAP_TIMEOUT = 40000  # the AJAX swap re-fetches /cart through vitrin: 4-6 s on this box


# ── helpers ────────────────────────────────────────────────────────────────


def _cart(page, base):
    r = page.request.get(base + "/api/v1/cart")
    return r.json() if r.ok else {}


def _clear(page, base):
    return page.request.delete(base + "/api/v1/cart/items").status


def _add(page, base, product_id, quantity=1):
    return page.request.post(
        base + "/api/v1/cart/items", data={"product_id": product_id, "quantity": quantity}
    )


def _simple_products(page, base, count):
    r = page.request.get(base + "/api/v1/products?page_size=50&availability=in_stock")
    items = [p for p in r.json()["results"] if not p["has_options"] and not p["has_fields"]]
    return items[:count]


def _lines(page):
    return page.locator("[data-cart-products-list] [data-qty-input]").count()


def _wait_lines(page, expected, timeout=SWAP_TIMEOUT):
    page.wait_for_function(
        "n => document.querySelectorAll('[data-cart-products-list] [data-qty-input]').length === n",
        arg=expected,
        timeout=timeout,
    )


def _qty(page):
    return page.evaluate(
        "() => { const i = document.querySelector('[data-cart-products-list] [data-qty-value]'); return i ? i.value : null; }"
    )


def _wait_qty(page, expected, timeout=SWAP_TIMEOUT):
    page.wait_for_function(
        "v => { const i = document.querySelector('[data-cart-products-list] [data-qty-value]'); return !!i && i.value === v; }",
        arg=str(expected),
        timeout=timeout,
    )


def _open_cart(page, base):
    page.goto(base + "/cart", wait_until="load")
    page.wait_for_selector("[data-cart-products-list] [data-qty-input]", timeout=30000)
    page.wait_for_timeout(400)  # header/badge/auth visibility settle


def _badge(page):
    return page.evaluate(
        "() => { const b = document.querySelector('[data-cart-badge]'); return b ? {text: b.textContent.trim(), hidden: b.hidden} : null; }"
    )


def _refresh_collector(page):
    """Collect POST/DELETE traffic the theme sends to the cart API."""
    seen = []
    page.on(
        "request",
        lambda r: seen.append((r.method, r.url))
        if "/api/v1/cart/" in r.url and r.method != "GET"
        else None,
    )
    return seen


def _amount(value_string):
    """The numeric part of a totals value_string.

    vitrin replaces the currency word ("SAR") with an inline riyal SVG, so the rendered
    text carries the number only; compare numbers, never the whole value_string.
    """
    m = re.search(r"-?[\d,]+(?:\.\d+)?", value_string or "")
    return m.group(0) if m else None


# ── journeys ───────────────────────────────────────────────────────────────


def cart_page(page, base, out, checks):
    """Populated cart page: rows, totals, money signs, checkout, controller boot."""
    try:
        _clear(page, base)
        product = _simple_products(page, base, 1)[0]
        checks["add_status"] = _add(page, base, product["id"], 2).status
        cart = _cart(page, base)
        checks["api_products_count"] = cart.get("products_count")
        checks["api_totals"] = [t["code"] for t in cart.get("totals", [])]
        _open_cart(page, base)
        page.screenshot(path=out / "1-cart.png", full_page=True)

        checks["lines"] = _lines(page)
        checks["qty"] = _qty(page)
        checks["line_ids"] = page.evaluate(
            """() => Array.from(document.querySelectorAll('[data-cart-products-list] [data-qty-input]'))
                 .map(w => ({cart: w.dataset.cartProductId, product: w.dataset.productId}))"""
        )
        checks["product_in_page"] = product["id"].replace("-", "") in json.dumps(
            checks["line_ids"]
        )

        summary = page.evaluate(
            """() => {
              const root = document.querySelector('[data-cart-totals]');
              if (!root) return null;
              const rows = Array.from(root.children);
              return {
                rows: rows.length,
                last: rows.length ? rows[rows.length - 1].innerText.replace(/\\s+/g, ' ').trim() : '',
                bold: rows.length ? rows[rows.length - 1].querySelectorAll('.font-semibold').length : 0,
                text: root.innerText.replace(/\\s+/g, ' ').trim(),
                missing: [],
              };
            }"""
        )
        checks["summary"] = summary
        if summary:
            checks["summary"]["missing"] = [
                t["value_string"]
                for t in cart.get("totals", [])
                if _amount(t["value_string"]) not in summary["text"]
            ]
            checks["double_sign"] = "--" in summary["text"]
            total = next((t for t in cart.get("totals", []) if t["code"] == "total"), None)
            checks["total_last"] = bool(
                total
                and _amount(total["value_string"]) in summary["last"]
                and summary["bold"] == 2
            )
        checks["checkout_href"] = page.evaluate(
            "() => { const a = document.querySelector('[data-checkout-buttons] a'); return a ? a.getAttribute('href') : null; }"
        )
        checks["controller"] = page.evaluate(
            "() => ({ CartPage: typeof window.CartPage, init: !!(window.CartPage && window.CartPage.init) })"
        )
        # The controller script must come from this checkout's asset server.
        perf = page.evaluate(
            "() => performance.getEntriesByType('resource').filter(e => e.name.includes('cart-controller.js')).map(e => e.name)"
        )
        checks["controller_url"] = perf
        checks["controller_served"] = any("cart-controller.js" in u for u in perf)

        passed = (
            checks["lines"] == 1
            and checks["qty"] == "2"
            and checks["product_in_page"]
            and bool(summary)
            and summary["rows"] == len(cart.get("totals", []))
            and not checks["summary"]["missing"]
            and not checks.get("double_sign")
            and checks.get("total_last")
            and checks["checkout_href"] == "/checkout"
            and checks["controller"] == {"CartPage": "object", "init": True}
            and checks["controller_served"]
        )
        return passed
    finally:
        checks["cart_cleared_status"] = _clear(page, base)


def cart_empty(page, base, out, checks):
    """Empty cart: empty state only, no totals/coupon/checkout, badge hidden."""
    try:
        checks["cart_cleared_status"] = _clear(page, base)
        page.goto(base + "/cart", wait_until="load")
        page.wait_for_selector(".cart-empty", timeout=30000)
        page.screenshot(path=out / "1-empty.png", full_page=True)
        state = page.evaluate(
            """() => ({
              empty: !!document.querySelector('.cart-empty'),
              totals: document.querySelectorAll('[data-cart-totals]').length,
              coupon: document.querySelectorAll('[data-coupon-section]').length,
              checkout: document.querySelectorAll('[data-checkout-buttons]').length,
              list: document.querySelectorAll('[data-cart-products-list]').length,
              badge: (() => { const b = document.querySelector('[data-cart-badge]'); return b ? {text: b.textContent.trim(), hidden: b.hidden} : null; })(),
              controller: !!performance.getEntriesByType('resource').find(e => e.name.includes('cart-controller.js')),
              continue_shopping: !!document.querySelector('.cart-empty a[href$="/"]'),
            })"""
        )
        checks.update(state)
        return (
            state["empty"]
            and state["totals"] == 0
            and state["coupon"] == 0
            and state["checkout"] == 0
            and state["list"] == 0
            and bool(state["badge"])
            and state["badge"]["hidden"] is True
            and state["controller"]
        )
    finally:
        checks["cart_cleared_status"] = _clear(page, base)


def cart_quantity(page, base, out, checks):
    """+ / − / trash on the cart page: one API call each, DOM follows the API."""
    try:
        _clear(page, base)
        product = _simple_products(page, base, 1)[0]
        _add(page, base, product["id"], 1)
        line = _cart(page, base)["products"][0]["id"]
        checks["line_id"] = line
        _open_cart(page, base)
        page.screenshot(path=out / "1-qty-1.png", full_page=True)

        calls = _refresh_collector(page)
        with page.expect_response(
            lambda r: r.url.endswith(f"/api/v1/cart/items/{line}") and r.request.method == "PATCH",
            timeout=PATCH_TIMEOUT,
        ) as up:
            page.locator("[data-cart-products-list] [data-qty-input] [data-qty-action='increase']").first.click()
        checks["increase_status"] = up.value.status
        _wait_qty(page, 2)
        checks["qty_after_increase_dom"] = _qty(page)
        checks["qty_after_increase_api"] = _cart(page, base)["products"][0]["quantity"]

        page.wait_for_timeout(300)
        with page.expect_response(
            lambda r: r.url.endswith(f"/api/v1/cart/items/{line}") and r.request.method == "PATCH",
            timeout=PATCH_TIMEOUT,
        ) as down:
            page.locator("[data-cart-products-list] [data-qty-input] [data-qty-action='decrease']").first.click()
        checks["decrease_status"] = down.value.status
        _wait_qty(page, 1)
        checks["qty_after_decrease_dom"] = _qty(page)
        checks["qty_after_decrease_api"] = _cart(page, base)["products"][0]["quantity"]

        page.wait_for_timeout(300)
        with page.expect_response(
            lambda r: r.url.endswith(f"/api/v1/cart/items/{line}") and r.request.method == "DELETE",
            timeout=PATCH_TIMEOUT,
        ) as rm:
            page.locator("[data-cart-products-list] [data-action='product-remove']").locator(
                "visible=true"
            ).first.click()
        checks["remove_status"] = rm.value.status
        page.wait_for_selector(".cart-empty", timeout=SWAP_TIMEOUT)
        page.screenshot(path=out / "2-empty.png", full_page=True)
        checks["empty_after_remove"] = page.evaluate("() => !!document.querySelector('.cart-empty')")
        checks["api_after_remove"] = _cart(page, base).get("products_count")
        checks["cart_calls"] = [c for c in calls if "/cart/items" in c[1]]

        patched = [c for c in calls if c[0] == "PATCH" and c[1].endswith(f"/cart/items/{line}")]
        deleted = [c for c in calls if c[0] == "DELETE" and c[1].endswith(f"/cart/items/{line}")]
        return (
            checks["increase_status"] == 200
            and checks["decrease_status"] == 200
            and checks["remove_status"] in (200, 204)
            and checks["qty_after_increase_dom"] == "2"
            and checks["qty_after_increase_api"] == 2
            and checks["qty_after_decrease_dom"] == "1"
            and checks["qty_after_decrease_api"] == 1
            and checks["empty_after_remove"]
            and checks["api_after_remove"] == 0
            and len(patched) == 2
            and len(deleted) == 1
        )
    finally:
        checks["cart_cleared_status"] = _clear(page, base)


def cart_badge(page, base, out, checks):
    """Header badge after removing one of two lines.

    Expected to FAIL today: js/cart/refresh.js only refreshes the badge through
    `window.cartManager.refreshBadge`, which this storefront does not define.
    """
    try:
        _clear(page, base)
        products = _simple_products(page, base, 2)
        checks["products"] = [p["id"] for p in products]
        for p in products:
            _add(page, base, p["id"], 1)
        _open_cart(page, base)
        page.screenshot(path=out / "1-two-lines.png", full_page=True)
        checks["lines_before"] = _lines(page)
        checks["badge_before"] = _badge(page)
        checks["api_before"] = _cart(page, base).get("products_count")

        page.locator("[data-cart-products-list] [data-action='product-remove']").locator(
            "visible=true"
        ).first.click()
        _wait_lines(page, 1)
        page.wait_for_timeout(500)
        page.screenshot(path=out / "2-one-line.png", full_page=True)
        checks["lines_after"] = _lines(page)
        checks["badge_after"] = _badge(page)
        checks["api_after"] = _cart(page, base).get("products_count")
        checks["badge_expected"] = str(checks["api_after"])
        checks["cart_manager"] = page.evaluate("() => typeof window.cartManager")

        conds = {
            "one_line_left": checks["lines_after"] == 1,
            "api_count_one": checks["api_after"] == 1,
            "badge_rendered": bool(checks["badge_after"]),
            "badge_matches_api": bool(checks["badge_after"]) and checks["badge_after"]["text"] == checks["badge_expected"],
        }
        checks["failed_checks"] = [k for k, ok in conds.items() if not ok]
        return not checks["failed_checks"]
    finally:
        checks["cart_cleared_status"] = _clear(page, base)


def cart_coupon(page, base, out, checks):
    """Coupon form: enable-on-input, one request per submit, recovery on rejection."""
    try:
        _clear(page, base)
        product = _simple_products(page, base, 1)[0]
        _add(page, base, product["id"], 1)
        _open_cart(page, base)
        page.screenshot(path=out / "1-form.png")

        # A second bootstrap must be a no-op, otherwise one submit would apply twice.
        checks["second_init"] = page.evaluate(
            "() => { try { window.CartPage.init({ cart: {}, loyaltyEnabled: false, translations: {} }); return 'returned'; } catch (e) { return String(e); } }"
        )
        input_ = page.locator("[data-coupon-input]")
        btn = page.locator("[data-coupon-submit-btn]")
        checks["disabled_empty"] = btn.is_disabled()
        input_.fill("ZZ-NO-SUCH-COUPON")
        checks["enabled_typed"] = not btn.is_disabled()
        input_.fill("   ")
        checks["disabled_spaces"] = btn.is_disabled()
        input_.fill("ZZ-NO-SUCH-COUPON")
        checks["enabled_retyped"] = not btn.is_disabled()

        calls = _refresh_collector(page)
        nav_before = page.evaluate("() => performance.getEntriesByType('navigation').length")
        with page.expect_response(
            lambda r: "/api/v1/cart/coupons" in r.url and r.request.method == "POST",
            timeout=PATCH_TIMEOUT,
        ) as resp:
            btn.click()
        checks["coupon_status"] = resp.value.status
        page.wait_for_timeout(800)
        page.screenshot(path=out / "2-rejected.png", full_page=True)

        state = page.evaluate(
            """() => {
              const btn = document.querySelector('[data-coupon-submit-btn]');
              const spin = document.querySelector('[data-coupon-submit-spinner]');
              const text = document.querySelector('[data-coupon-submit-text]');
              const input = document.querySelector('[data-coupon-input]');
              return {
                disabled: btn ? btn.disabled : null,
                spinner_hidden: spin ? spin.classList.contains('hidden') : null,
                text_hidden: text ? text.classList.contains('hidden') : null,
                focused: document.activeElement === input,
                applied_chip: !!document.querySelector('[data-applied-coupon]'),
                nav: performance.getEntriesByType('navigation').length,
                value: input ? input.value : null,
              };
            }"""
        )
        checks["after_reject"] = state
        checks["coupon_requests"] = [c for c in calls if "/api/v1/cart/coupons" in c[1]]
        checks["nav_before"] = nav_before

        return (
            checks["second_init"] == "returned"
            and checks["disabled_empty"]
            and checks["enabled_typed"]
            and checks["disabled_spaces"]
            and checks["enabled_retyped"]
            and checks["coupon_status"] >= 400
            and len(checks["coupon_requests"]) == 1
            and state["disabled"] is False
            and state["spinner_hidden"] is True
            and state["text_hidden"] is False
            and state["focused"] is True
            and state["applied_chip"] is False
            and state["nav"] == nav_before
        )
    finally:
        checks["cart_cleared_status"] = _clear(page, base)


def cart_loyalty_guest(page, base, out, checks):
    """Guest loyalty card: earn copy, login link with redirect, redemption hidden."""
    try:
        _clear(page, base)
        product = _simple_products(page, base, 1)[0]
        _add(page, base, product["id"], 1)
        _open_cart(page, base)
        page.screenshot(path=out / "1-loyalty.png", full_page=True)
        state = page.evaluate(
            """() => {
              const visible = (el) => !!el && el.offsetParent !== null;
              const section = document.querySelector('[data-loyalty-section]');
              const login = section && section.querySelector('a[data-action="login"]');
              const redemption = document.querySelector('[data-loyalty-redemption-section]');
              return {
                section: visible(section),
                earn_card: visible(document.querySelector('[data-loyalty-earn-card]')),
                points: (document.querySelector('[data-loyalty-calculated-points]') || {}).textContent,
                login_href: login ? login.getAttribute('href') : null,
                redemption_visible: visible(redemption),
                copy: section ? section.innerText.replace(/\\s+/g, ' ').trim().slice(0, 200) : '',
              };
            }"""
        )
        checks.update(state)
        return (
            state["section"]
            and state["earn_card"]
            and bool(state["login_href"])
            and "redirect_to=/cart" in state["login_href"]
            and state["redemption_visible"] is False
        )
    finally:
        checks["cart_cleared_status"] = _clear(page, base)


def cart_gift_guest(page, base, out, checks):
    """Gift order button as a guest: opens a dialog, no navigation."""
    try:
        _clear(page, base)
        product = _simple_products(page, base, 1)[0]
        _add(page, base, product["id"], 1)
        _open_cart(page, base)
        checks["gift_section"] = page.locator("[data-gift-order-section]").count()
        page.screenshot(path=out / "1-before-click.png")
        page.locator("[data-gift-order-btn]").first.click()
        page.wait_for_selector(".MuiDialog-paper, dialog[open]", state="visible", timeout=15000)
        page.wait_for_timeout(500)
        page.screenshot(path=out / "2-dialog.png", full_page=True)
        state = page.evaluate(
            """() => {
              const d = document.querySelector('.MuiDialog-paper, dialog[open]');
              return {
                dialogs: document.querySelectorAll('.MuiDialog-paper, dialog[open]').length,
                text: d ? d.innerText.replace(/\\s+/g, ' ').trim().slice(0, 200) : null,
                url: location.pathname,
                gift_dialog: typeof window.gift_dialog,
                auth_dialog: typeof window.auth_dialog,
              };
            }"""
        )
        checks.update(state)
        return (
            checks["gift_section"] == 1
            and state["dialogs"] >= 1
            and bool(state["text"])
            and state["url"] == "/cart"
        )
    finally:
        checks["cart_cleared_status"] = _clear(page, base)


def cart_gift_popup(page, base, out, checks):
    """Adding from the PDP shows the header gift hint, which hides itself."""
    try:
        _clear(page, base)
        product = _simple_products(page, base, 1)[0]
        checks["product"] = {"id": product["id"], "slug": product["slug"]}
        page.goto(base + "/products/" + product["slug"], wait_until="load")
        page.wait_for_selector("[data-in-stock] button[data-add-to-cart-form]", timeout=30000)
        page.screenshot(path=out / "1-pdp.png")
        with page.expect_response(
            lambda r: r.url.endswith("/api/v1/cart/items") and r.request.method == "POST",
            timeout=PATCH_TIMEOUT,
        ) as added:
            page.locator("[data-in-stock] button[data-add-to-cart-form]").first.click()
        checks["add_status"] = added.value.status
        page.wait_for_selector("[data-gift-cart-popup]", state="visible", timeout=10000)
        page.wait_for_timeout(300)
        page.screenshot(path=out / "2-popup.png")
        checks["popup_visible_after_add"] = page.locator("[data-gift-cart-popup]").is_visible()
        page.wait_for_timeout(5000)
        checks["popup_hidden_after_hide_delay"] = not page.locator("[data-gift-cart-popup]").is_visible()
        page.screenshot(path=out / "3-after-delay.png")
        return checks["popup_visible_after_add"] and checks["popup_hidden_after_hide_delay"]
    finally:
        checks["cart_cleared_status"] = _clear(page, base)


def cart_refresh_race(page, base, out, checks):
    """A `zidcart:updated` that lands during a refresh must not be dropped.

    Expected to FAIL today: js/cart/refresh.js returns early while `isRefreshing` and
    forgets that another refresh is needed, so the page keeps the earlier response's
    cart until a further event arrives.
    """
    try:
        _clear(page, base)
        product = _simple_products(page, base, 1)[0]
        _add(page, base, product["id"], 1)
        line = _cart(page, base)["products"][0]["id"]
        checks["line_id"] = line
        _open_cart(page, base)

        # Hold the theme's own refresh response after its body has been read, so the
        # second cart change certainly lands between "response composed" and "DOM
        # swapped" — the window in which refresh.js drops the second event.
        page.evaluate(
            """() => {
              const orig = window.fetch.bind(window);
              window.__origFetch = orig;
              window.__refreshes = 0;
              window.__captured = 0;
              window.__swaps = 0;
              window.addEventListener('cart-updated', () => { window.__swaps += 1; });
              window.fetch = function (url, opts) {
                const isRefresh = opts && opts.headers && opts.headers['X-Requested-With'] === 'XMLHttpRequest';
                if (!isRefresh) return orig(url, opts);
                window.__refreshes += 1;
                return orig(url, opts).then(r => r.text()).then(t => {
                  window.__captured += 1;          // the body now reflects the cart as of us
                  return new Promise(resolve => {
                    setTimeout(() => resolve(new Response(t, { status: 200, headers: { 'Content-Type': 'text/html' } })), 2000);
                  });
                });
              };
            }"""
        )
        page.evaluate("() => window.dispatchEvent(new CustomEvent('zidcart:updated'))")
        page.wait_for_function("() => window.__captured === 1", timeout=SWAP_TIMEOUT)

        # The shopper's next change, while refresh #1 is in flight.
        changed = page.request.fetch(
            f"{base}/api/v1/cart/items/{line}", method="PATCH", form={"quantity": 3}
        )
        checks["change_status"] = changed.status
        checks["api_qty_after_change"] = _cart(page, base)["products"][0]["quantity"]
        page.evaluate("() => window.dispatchEvent(new CustomEvent('zidcart:updated'))")

        page.wait_for_function("() => window.__swaps >= 1", timeout=SWAP_TIMEOUT)
        page.screenshot(path=out / "1-after-first-refresh.png", full_page=True)
        first = page.evaluate(
            """() => ({
              qty: (document.querySelector('[data-cart-products-list] [data-qty-value]') || {}).value,
              refreshes: window.__refreshes,
              swaps: window.__swaps,
            })"""
        )
        checks["qty_after_first_refresh"] = first["qty"]
        checks["refreshes_at_first_swap"] = first["refreshes"]
        checks["swaps_at_first_swap"] = first["swaps"]

        # How long the page keeps the pre-change quantity before it matches the API.
        # A queued (not dropped) refresh would land with the body composed after the
        # change; here nothing guarantees it.
        stale_ms = page.evaluate(
            """async (want) => {
              const api = await window.__origFetch('/api/v1/cart', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(r => r.json()).catch(() => null);
              const qty = api && api.products && api.products[0] ? String(api.products[0].quantity) : null;
              const started = performance.now();
              const target = qty || want;
              while (performance.now() - started < 12000) {
                const i = document.querySelector('[data-cart-products-list] [data-qty-value]');
                if (i && i.value === target) return { ms: Math.round(performance.now() - started), qty: i.value, target };
                await new Promise(r => setTimeout(r, 250));
              }
              const i = document.querySelector('[data-cart-products-list] [data-qty-value]');
              return { ms: 12000, qty: i ? i.value : null, target, timed_out: true };
            }""",
            arg="3",
        )
        checks["stale_window"] = stale_ms
        checks["refreshes_total"] = page.evaluate("() => window.__refreshes")

        # A further event converges the page on the server's cart (proves the refresh
        # was dropped, not broken).
        if stale_ms["qty"] != stale_ms["target"]:
            page.evaluate("() => window.dispatchEvent(new CustomEvent('zidcart:updated'))")
            page.wait_for_function(
                "t => { const i = document.querySelector('[data-cart-products-list] [data-qty-value]'); return !!i && i.value === t; }",
                arg=stale_ms["target"],
                timeout=SWAP_TIMEOUT,
            )
            checks["converged_after_user_event"] = _qty(page)
        else:
            checks["converged_after_user_event"] = None
        checks["api_qty_final"] = _cart(page, base)["products"][0]["quantity"]
        page.screenshot(path=out / "2-converged.png", full_page=True)

        conds = {
            "change_ok": checks["change_status"] == 200,
            "api_qty_three": checks["api_qty_after_change"] == 3,
            "dom_qty_converges": stale_ms["qty"] == stale_ms["target"],
            "converges_within_1s": stale_ms["ms"] <= 1000,
        }
        checks["failed_checks"] = [k for k, ok in conds.items() if not ok]
        return not checks["failed_checks"]
    finally:
        checks["cart_cleared_status"] = _clear(page, base)


JOURNEYS = {
    "cart-page": cart_page,
    "cart-empty": cart_empty,
    "cart-quantity": cart_quantity,
    "cart-badge": cart_badge,
    "cart-coupon": cart_coupon,
    "cart-loyalty-guest": cart_loyalty_guest,
    "cart-gift-guest": cart_gift_guest,
    "cart-gift-popup": cart_gift_popup,
    "cart-refresh-race": cart_refresh_race,
}

# Recorded product bugs (drive.py exits 0 with FINDING while exactly these checks fail).
KNOWN = {
    "cart-badge": ({"badge_matches_api"}, "the header badge keeps the old count after a cart line is removed"),
    "cart-refresh-race": (
        {"dom_qty_converges", "converges_within_1s"},
        "js/cart/refresh.js drops a zidcart:updated that lands while a refresh is in flight; the page keeps the stale quantity",
    ),
}
