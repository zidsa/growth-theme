"""verify-layout journeys: the layout group's shell, header, footer, shared components and JS utils.

Loaded by ../../verify-growth-theme/scripts/drive.py; run from the repo root:

    uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py layout-shell
"""

import re
from pathlib import Path

# A theme-bundle console error is a layout defect; landbot/SDK noise is not ours.
def _theme_errors(page, sink):
    page.on(
        "console",
        lambda m: sink.append(f"{m.text} @ {m.location.get('url', '')}")
        if m.type == "error" and ("theme.js" in (m.location.get("url") or "") or "assets" in (m.location.get("url") or ""))
        else None,
    )


def _in_stock_product(page, base):
    api = page.request.get(base + "/api/v1/products?page_size=20&availability=in_stock")
    return next(p for p in api.json()["results"] if not p["has_options"] and not p["has_fields"])


def _out_of_stock_product(page, base):
    api = page.request.get(base + "/api/v1/products?page_size=20&availability=out_of_stock")
    return next(p for p in api.json()["results"] if not p["has_options"])


def _countries_in_source():
    """Rows of the real country table this checkout ships (None if not run from the repo)."""
    try:
        src = Path("assets/js/data/countries.js").read_text()
    except OSError:
        return None
    return len(re.findall(r'\{\s*code:\s*"', src))


# ── layout-shell ─────────────────────────────────────────────────────────────
def shell(page, base, out, checks):
    """The page shell layout.jinja promises: one document frame, header, footer, one theme bundle."""
    errors = []
    _theme_errors(page, errors)
    resp = page.goto(base + "/", wait_until="load")
    page.wait_for_selector("footer#footer")
    page.wait_for_timeout(600)
    checks["home_status"] = resp.status
    checks["dir"] = page.evaluate("document.documentElement.dir")
    checks["lang"] = page.evaluate("document.documentElement.lang")
    checks["template"] = page.evaluate("document.body.dataset.template")
    checks["main"] = page.locator("main#main").count()
    checks["header"] = page.locator("header").count()
    checks["footer"] = page.locator("footer#footer").count()
    checks["theme_scripts"] = page.evaluate(
        "Array.from(document.scripts).map(s => s.src).filter(s => s && s.includes('dist/theme.js'))"
    )
    checks["profile_url"] = page.evaluate("window.layoutConfig && window.layoutConfig.profileUrl")
    checks["cart_href"] = page.evaluate(
        "(() => { const a = document.querySelector('a[href$=\"/cart\"], a[href*=\"/cart?\"]'); return a && new URL(a.href).pathname; })()"
    )
    checks["cart_badge"] = page.locator("[data-cart-badge]").count()
    checks["logo"] = page.evaluate(
        "(() => { const h = document.querySelector('header'); return {img: h.querySelectorAll('img').length, text: (h.querySelector('h1,h2')||{}).textContent?.trim() || null}; })()"
    )
    checks["footer_groups"] = page.locator("footer#footer ul[role='list']").count()
    checks["footer_links"] = page.locator("footer#footer a[href]").count()
    checks["announcement_bar"] = page.locator("[data-announcement-bar]").count()
    checks["main_tags"] = page.locator("main").count()
    page.screenshot(path=out / "1-home.png")

    # The same frame must hold on a second template (footer/header are shared includes).
    resp2 = page.goto(base + "/products", wait_until="load")
    page.wait_for_selector("nav[aria-label]")
    page.wait_for_timeout(400)
    checks["products_status"] = resp2.status
    checks["products_template"] = page.evaluate("document.body.dataset.template")
    checks["products_main"] = page.locator("main#main").count()
    checks["products_theme_scripts"] = page.evaluate(
        "Array.from(document.scripts).map(s => s.src).filter(s => s && s.includes('dist/theme.js')).length"
    )
    checks["breadcrumb"] = page.locator("nav[aria-label='breadcrumb']").count()
    checks["breadcrumb_items"] = page.locator("nav[aria-label='breadcrumb'] li").count()
    checks["products_footer"] = page.locator("footer#footer").count()
    page.screenshot(path=out / "2-products.png", full_page=False)

    checks["theme_console_errors"] = errors
    ok = (
        checks["home_status"] == 200
        and checks["dir"] == "rtl"
        and checks["lang"] == "ar"
        and checks["template"] == "home"
        and checks["main"] == 1
        and checks["header"] == 1
        and checks["footer"] == 1
        and len(checks["theme_scripts"]) == 1
        and checks["profile_url"].endswith("/account")
        and (checks["cart_href"] or "").startswith("/cart")
        and checks["cart_badge"] == 1
        and (checks["logo"]["img"] > 0 or checks["logo"]["text"])
        and checks["footer_groups"] >= 1
        and checks["footer_links"] >= 1
        and checks["announcement_bar"] <= 1
        and checks["main_tags"] == 1
        and checks["products_status"] == 200
        and checks["products_main"] == 1
        and checks["products_theme_scripts"] == 1
        and checks["breadcrumb_items"] >= 1
        and checks["products_footer"] == 1
        and not errors
    )
    return ok


# ── layout-nav ───────────────────────────────────────────────────────────────
def nav(page, base, out, checks):
    """main-nav (6 items + More overflow) and mobile-drawer must agree on the store menu."""
    errors = []
    _theme_errors(page, errors)
    page.goto(base + "/", wait_until="load")
    page.wait_for_selector("header nav")
    page.wait_for_timeout(600)

    desktop = page.evaluate(
        "Array.from(document.querySelectorAll('header nav > div > ul > li')).map(li => li.innerText.trim())"
    )
    drawer = page.evaluate(
        "(() => { const c = document.querySelector('#mobile-drawer div.flex.w-full.flex-col');"
        " return c ? Array.from(c.children).map(x => x.innerText.trim().split('\\n')[0]) : null; })()"
    )
    checks["desktop_items"] = desktop
    checks["drawer_items"] = drawer
    checks["desktop_count"] = len(desktop)
    checks["drawer_count"] = len(drawer) if drawer is not None else None
    checks["more_label"] = desktop[-1] if desktop else None

    # Every desktop item except the "More" trigger is a real link with a path.
    checks["desktop_hrefs"] = page.evaluate(
        "Array.from(document.querySelectorAll('header nav > div > ul > li a')).map(a => a.getAttribute('href'))"
    )
    checks["empty_hrefs"] = [h for h in checks["desktop_hrefs"] if not h or h in ("#", "javascript:void(0)")]

    total = len(drawer) if drawer is not None else 0
    expected_desktop = min(total, 6) + (1 if total > 6 else 0)
    checks["expected_desktop_count"] = expected_desktop

    overflow = []
    if total > 6:
        page.locator("button[popovertarget='more-menu-popover']").click()
        page.wait_for_timeout(500)
        checks["more_popover"] = page.evaluate(
            "(() => { const e = document.getElementById('more-menu-popover'); if (!e) return null;"
            " const r = e.getBoundingClientRect(); return {open: e.matches(':popover-open'), height: r.height}; })()"
        )
        overflow = [
            line.strip()
            for line in page.locator("#more-menu-popover").inner_text().split("\n")
            if line.strip()
        ]
        checks["overflow_items"] = overflow
        page.screenshot(path=out / "1-more-popover.png")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    checks["overflow_count"] = len(overflow)
    checks["expected_overflow_count"] = max(total - 6, 0)

    # The drawer is the mobile twin of the same menu: no item may be dropped.
    missing_in_drawer = [label for label in desktop[:-1] if label and label not in (drawer or [])]
    checks["missing_in_drawer"] = missing_in_drawer

    # Search dialog (components/header/search.jinja) opens, queries and links to the listing.
    page.locator("[data-search-trigger]").first.click()
    page.wait_for_timeout(400)
    checks["search_open"] = page.evaluate(
        "(() => { const d = document.getElementById('search-dialog'); return d ? d.open : null; })()"
    )
    page.fill("[data-search-input]", "منتج")
    page.wait_for_timeout(2500)
    checks["search"] = page.evaluate(
        "(() => { const g = s => document.querySelector(s);"
        " const results = g('[data-search-results]'); const empty = g('[data-search-empty]');"
        " return {results_shown: results ? !results.classList.contains('hidden') : null,"
        "  product_cards: g('[data-search-products]') ? g('[data-search-products]').children.length : null,"
        "  empty_shown: empty ? !empty.classList.contains('hidden') : null,"
        "  all_href: g('[data-search-all-link]') && g('[data-search-all-link]').getAttribute('href'),"
        "  clear_shown: g('[data-search-clear]') ? !g('[data-search-clear]').classList.contains('hidden') : null}; })()"
    )
    page.screenshot(path=out / "2-search-dialog.png")
    checks["theme_console_errors"] = errors

    search = checks["search"]
    ok = (
        total >= 1
        and checks["desktop_count"] == expected_desktop
        and checks["more_label"] == ("More" if total > 6 else checks["more_label"])
        and not checks["empty_hrefs"]
        and not missing_in_drawer
        and (total <= 6 or (checks["more_popover"] or {}).get("open"))
        and checks["overflow_count"] == checks["expected_overflow_count"]
        and checks["search_open"] is True
        and (search["results_shown"] or search["empty_shown"])
        and "/products?q=" in (search["all_href"] or "")
        and search["clear_shown"] is True
        and not errors
    )
    return ok


# ── layout-carousel ──────────────────────────────────────────────────────────
def carousel(page, base, out, checks):
    """js/lib/carousel via main.js: progress stays in 0..100 and the buttons track the ends."""
    errors = []
    _theme_errors(page, errors)
    product = _in_stock_product(page, base)
    page.goto(base + "/products/" + product["slug"], wait_until="load")
    page.wait_for_selector("[data-carousel] [data-carousel-next]", state="attached")
    page.wait_for_timeout(1500)

    state = page.evaluate(
        """Array.from(document.querySelectorAll('[data-carousel]')).map(c => {
             const next = c.querySelector('[data-carousel-next]');
             const prev = c.querySelector('[data-carousel-prev]');
             const slides = c.querySelectorAll('[data-carousel-slide], .embla__slide, .products-embla__slide').length;
             const bar = c.querySelector('[data-carousel-progress]');
             return {name: c.dataset.productsCarousel || c.dataset.carousel,
                     loop: c.dataset.carouselLoop,
                     slides, next_disabled: next && next.disabled, prev_disabled: prev && prev.disabled,
                     next_visible: next && !next.classList.contains('invisible'),
                     prev_visible: prev && !prev.classList.contains('invisible'),
                     progress: bar ? parseFloat(bar.style.width) : null};
           })"""
    )
    checks["carousels"] = state
    checks["slides"] = max((c["slides"] for c in state), default=0)

    steps, progress, next_disabled_at_end, prev_enabled_after_move = [], [], False, False
    for i in range(12):
        btn = page.locator("[data-carousel-next]:not([disabled])").first
        if not btn.count():
            next_disabled_at_end = True
            break
        btn.click()
        page.wait_for_timeout(450)
        snap = page.evaluate(
            """Array.from(document.querySelectorAll('[data-carousel]')).map(c => {
                 const bar = c.querySelector('[data-carousel-progress]');
                 const next = c.querySelector('[data-carousel-next]'); const prev = c.querySelector('[data-carousel-prev]');
                 return {progress: bar ? parseFloat(bar.style.width) : null,
                         next_disabled: next && next.disabled, prev_disabled: prev && prev.disabled};
               })"""
        )
        steps.append(snap)
        progress.append([s["progress"] for s in snap])
        if any((s["prev_disabled"] is False) for s in snap):
            prev_enabled_after_move = True

    checks["steps"] = steps
    checks["progress_series"] = progress
    checks["next_disabled_at_end"] = next_disabled_at_end
    checks["prev_enabled_after_move"] = prev_enabled_after_move

    flat = [p for row in progress for p in row if p is not None]
    in_bounds = all(0 <= p <= 100 for p in flat) and len(flat) == sum(len(r) for r in progress)
    monotonic = all(
        b >= a - 0.01 for row in progress for a, b in zip(row, row[1:]) if a is not None and b is not None
    )
    checks["progress_in_bounds"] = in_bounds
    checks["progress_monotonic"] = monotonic

    # A disabled arrow means "that direction is exhausted": at the furthest (or nearest) point this
    # carousel ever reached, never somewhere in the middle. Both arrows share one visibility toggle.
    start = [
        (c["progress"], c["next_disabled"], c["prev_disabled"]) for c in state
    ]
    per_carousel = [[pair] for pair in start]
    for snap in steps:
        for index, pair in enumerate(snap):
            if index < len(per_carousel):
                per_carousel[index].append((pair["progress"], pair["next_disabled"], pair["prev_disabled"]))
    checks["next_disabled_only_at_bound"] = all(
        p is None or p >= max((x[0] for x in series if x[0] is not None), default=-1) - 0.5
        for series in per_carousel
        for p, next_disabled, _ in series
        if next_disabled
    )
    checks["prev_disabled_only_at_bound"] = all(
        p is None or p <= min((x[0] for x in series if x[0] is not None), default=101) + 0.5
        for series in per_carousel
        for p, _, prev_disabled in series
        if prev_disabled
    )
    checks["arrows_share_visibility"] = all(c["next_visible"] == c["prev_visible"] for c in state)
    checks["hidden_arrows_are_disabled"] = all(
        not (c["next_visible"] or c["prev_visible"]) or not (c["next_disabled"] and c["prev_disabled"])
        for c in state
        if c["slides"] >= 2
    )
    checks["start_prev_disabled"] = all(c["prev_disabled"] for c in state if c["loop"] != "true")
    checks["reached_end"] = any(
        next_disabled and p is not None and p >= max((x[0] for x in series if x[0] is not None), default=-1) - 0.5
        for series in per_carousel
        for p, next_disabled, _ in series
    )

    # Re-init on content:loaded must not duplicate a carousel inside the same container.
    page.evaluate("window.dispatchEvent(new CustomEvent('content:loaded'))")
    page.wait_for_timeout(500)
    checks["after_reinit"] = page.evaluate(
        "document.querySelectorAll('[data-carousel] [data-carousel-viewport]').length"
    )
    checks["viewport_per_carousel"] = page.evaluate(
        "document.querySelectorAll('[data-carousel]').length ? document.querySelectorAll('[data-carousel-viewport]').length : 0"
    )
    page.screenshot(path=out / "1-carousel-end.png")
    checks["theme_console_errors"] = errors

    return (
        checks["slides"] >= 2
        and in_bounds
        and monotonic
        and next_disabled_at_end
        and prev_enabled_after_move
        and checks["next_disabled_only_at_bound"]
        and checks["prev_disabled_only_at_bound"]
        and checks["arrows_share_visibility"]
        and checks["hidden_arrows_are_disabled"]
        and checks["start_prev_disabled"]
        and checks["reached_end"]
        and checks["after_reinit"] == checks["viewport_per_carousel"]
        and not errors
    )


# ── layout-phone ─────────────────────────────────────────────────────────────
def phone(page, base, out, checks):
    """components/ui/phone-input.jinja in the notify-me dialog: table-driven country selector."""
    errors = []
    _theme_errors(page, errors)
    product = _out_of_stock_product(page, base)
    page.goto(base + "/products/" + product["slug"], wait_until="load")
    page.wait_for_selector("[data-notify-me-btn]")
    page.locator("[data-notify-me-btn]").first.click()
    page.wait_for_timeout(700)

    checks["dialog_open"] = page.evaluate(
        "(() => { const d = document.getElementById('notify-me-dialog'); return d ? d.open : null; })()"
    )
    checks["all_countries"] = page.get_attribute("[data-phone-input]", "data-all-countries")
    checks["options"] = page.locator("[data-phone-input] [data-phone-country-list] [data-dial-code]").count()
    checks["expected_options"] = _countries_in_source() if checks["all_countries"] == "true" else 18
    checks["initial_display"] = page.locator("[data-phone-country-display]").first.inner_text().strip()
    checks["initial_hidden"] = page.locator("[data-phone-country-code]").first.input_value()
    checks["saudi_option"] = page.locator("[data-phone-input] [data-phone-country-list] [data-dial-code='+966']").count()
    checks["egypt_option"] = page.locator("[data-phone-input] [data-phone-country-list] [data-dial-code='+20']").count()

    triggers = page.locator("[data-phone-input] [data-slot='country-trigger']")
    checks["trigger_count"] = triggers.count()
    triggers.first.click()
    page.wait_for_timeout(700)
    checks["popover_open"] = page.locator("[data-phone-input] [data-phone-country-search]").is_visible()
    page.fill("[data-phone-input] [data-phone-country-search]", "Egypt")
    page.wait_for_timeout(400)
    visible = page.locator("[data-phone-input] [data-phone-country-list] [data-dial-code]:visible")
    checks["filtered_options"] = visible.count()
    checks["filtered_first"] = visible.first.get_attribute("data-dial-code") if visible.count() else None
    page.screenshot(path=out / "1-country-search.png")
    if visible.count():
        visible.first.click()
        page.wait_for_timeout(400)
    checks["after_display"] = page.locator("[data-phone-country-display]").first.inner_text().strip()
    checks["after_hidden"] = page.locator("[data-phone-country-code]").first.input_value()

    page.fill("[data-phone-input] [data-phone-number-input]", "1001234567")
    page.wait_for_timeout(300)
    checks["full_value"] = page.evaluate(
        "(() => { const e = document.querySelector('[data-phone-input] [data-phone-full-value]') ||"
        " document.querySelector('[data-phone-input] input[type=hidden][name=phone]'); return e ? e.value : null; })()"
    )
    checks["submit_still_enabled"] = page.locator("[data-notify-submit-btn]").is_enabled()
    page.screenshot(path=out / "2-egypt-selected.png")
    checks["theme_console_errors"] = errors

    return (
        checks["dialog_open"] is True
        and checks["options"] >= 18
        and (checks["expected_options"] is None or checks["options"] == checks["expected_options"])
        and checks["initial_display"] == "+966"
        and checks["initial_hidden"] == "+966"
        and checks["saudi_option"] >= 1
        and checks["egypt_option"] >= 1
        and checks["popover_open"] is True
        and 1 <= checks["filtered_options"] < checks["options"]
        and checks["filtered_first"] == "+20"
        and checks["after_display"] == "+20"
        and checks["after_hidden"] == "+20"
        and (checks["full_value"] or "").startswith("+20")
        and not errors
    )


# ── layout-loyalty ───────────────────────────────────────────────────────────
def loyalty(page, base, out, checks):
    """js/layout-loyalty: the floating rewards button exists only where layout.jinja emits it."""
    errors = []
    _theme_errors(page, errors)
    page.goto(base + "/", wait_until="load")
    page.wait_for_timeout(1200)
    checks["home_template"] = page.evaluate("document.body.dataset.template")
    checks["home_script"] = page.locator("script[src*='layout-loyalty']").count()
    checks["home_button"] = page.locator("#loyalty-floating-btn").count()
    checks["button_visible"] = page.locator("#loyalty-floating-btn").is_visible() if checks["home_button"] else False
    checks["button_box"] = page.evaluate(
        "(() => { const b = document.getElementById('loyalty-floating-btn'); if (!b) return null;"
        " const r = b.getBoundingClientRect(); return {left: Math.round(r.left), right: Math.round(r.right), width: Math.round(r.width)}; })()"
    )
    checks["in_rtl_side"] = bool(checks["button_box"] and checks["button_box"]["left"] < 200)
    checks["label"] = page.evaluate(
        "(() => { const b = document.querySelector('#loyalty-floating-btn .loyalty_footer_btn span'); return b && b.innerText.trim(); })()"
    )

    instrumented = page.evaluate(
        """(() => { const d = window.loyalty_rewards_dialog; if (!d) return 'missing';
             window.__loyaltyOpens = 0; const open = d.open;
             try { d.open = function () { window.__loyaltyOpens += 1; return open.apply(this, arguments); }; return 'wrapped'; }
             catch (e) { return 'sealed'; } })()"""
    )
    checks["dialog_instrumented"] = instrumented
    if checks["home_button"]:
        page.locator("#loyalty-floating-btn .loyalty_footer_btn").click()
        page.wait_for_timeout(800)
    checks["opens"] = page.evaluate("window.__loyaltyOpens || 0")
    checks["dialog_present"] = page.evaluate(
        "document.querySelectorAll('.MuiDialog-container, [role=dialog]').length"
    )
    page.screenshot(path=out / "1-loyalty-home.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)

    # layout.jinja skips the button on product/cart/page templates: /cart must have neither.
    page.goto(base + "/cart", wait_until="load")
    page.wait_for_timeout(800)
    checks["cart_template"] = page.evaluate("document.body.dataset.template")
    checks["cart_script"] = page.locator("script[src*='layout-loyalty']").count()
    checks["cart_button"] = page.locator("#loyalty-floating-btn").count()
    checks["theme_console_errors"] = errors

    return (
        checks["home_script"] == 1
        and checks["home_button"] == 1
        and checks["button_visible"]
        and checks["in_rtl_side"]
        and bool(checks["label"])
        and checks["opens"] == 1
        and checks["cart_button"] == 0
        and checks["cart_script"] == 0
        and not errors
    )


# ── layout-404 ───────────────────────────────────────────────────────────────
def not_found(page, base, out, checks):
    """templates/404_not_found.jinja: the countdown counts 3-2-1-0 and then goes home."""
    errors = []
    _theme_errors(page, errors)
    resp = page.goto(base + "/layout-journey-missing-page", wait_until="commit")
    checks["status"] = resp.status if resp else None
    page.wait_for_selector("#redirectCountdown", timeout=8000)
    checks["template"] = page.evaluate("document.body.dataset.template")
    checks["home_cta"] = page.evaluate(
        "Array.from(document.querySelectorAll('main a[href]')).filter(a => new URL(a.href).pathname === '/').length"
    )

    seen, redirected = [], False
    for step in range(28):
        try:
            text = page.evaluate(
                "(() => { const e = document.getElementById('redirectCountdown');"
                " return e && e.textContent.trim(); })()"
            )
        except Exception:
            text = None
        if step == 0:
            page.screenshot(path=out / "1-404.png")
        try:
            if page.evaluate("location.pathname") == "/":
                redirected = True
                break
        except Exception:
            redirected = True  # context destroyed mid-navigation
            break
        if text and (not seen or seen[-1] != text):
            seen.append(text)
        page.wait_for_timeout(250)
    checks["countdown_seen"] = seen
    checks["redirected_home"] = redirected or page.evaluate("location.pathname") == "/"
    checks["final_url"] = page.url
    numbers = [int(s) for s in seen if s.isdigit()]
    checks["countdown_numbers"] = numbers
    checks["theme_console_errors"] = errors

    # "0" is written and the redirect fires in the same tick, so it often is not painted:
    # the invariant is first tick 3, a non-increasing 3..0 run, then home, never a negative.
    checks["zero_painted"] = 0 in numbers
    return (
        checks["status"] == 404
        and "404" in (checks["template"] or "")
        and checks["home_cta"] >= 1
        and bool(numbers)
        and numbers[0] == 3
        and max(numbers) <= 3
        and min(numbers) >= 0
        and all(b <= a for a, b in zip(numbers, numbers[1:]))
        and min(numbers) <= 1
        and checks["redirected_home"]
        and not errors
    )


# ── layout-auth ──────────────────────────────────────────────────────────────
def auth(page, base, out, checks):
    """Header auth controls + the drawer twin + no cross-origin redirect from handleLoginAction."""
    errors = []
    _theme_errors(page, errors)
    page.goto(base + "/", wait_until="load")
    page.wait_for_selector("#header-login-btn")
    page.wait_for_timeout(600)
    checks["login_visible"] = page.locator("#header-login-btn").is_visible()
    checks["profile_visible"] = page.locator("#header-profile-btn").is_visible()
    checks["handle_login_type"] = page.evaluate("typeof window.handleLoginAction")
    checks["profile_url"] = page.evaluate("window.layoutConfig.profileUrl")
    checks["state"] = page.evaluate("window.customerAuthState || null")

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base + "/", wait_until="load")
    page.wait_for_timeout(800)
    page.locator("#mobile-drawer-dialog > button").click()
    page.wait_for_timeout(500)
    checks["drawer_open"] = page.evaluate("document.getElementById('mobile-drawer').open")
    checks["drawer_login_visible"] = page.locator("#mobile-login-btn").is_visible()
    checks["drawer_items"] = page.evaluate(
        "(() => { const c = document.querySelector('#mobile-drawer div.flex.w-full.flex-col');"
        " return c ? c.children.length : null; })()"
    )
    page.screenshot(path=out / "1-drawer.png")
    page.keyboard.press("Escape")

    # Guest click: either the SDK dialog opens or the page falls back to /auth/login.
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base + "/", wait_until="load")
    page.wait_for_timeout(800)
    instrumented = page.evaluate(
        """(() => { const d = window.auth_dialog; if (!d) return 'missing';
             window.__authOpens = 0; const open = d.open;
             try { d.open = function () { window.__authOpens += 1; return open.apply(this, arguments); }; return 'wrapped'; }
             catch (e) { return 'sealed'; } })()"""
    )
    checks["auth_instrumented"] = instrumented
    page.locator("#header-login-btn").click()
    page.wait_for_timeout(1500)
    checks["auth_opens"] = page.evaluate("window.__authOpens || 0")
    checks["after_login_click"] = page.evaluate("location.pathname")
    page.screenshot(path=out / "2-login.png")

    # Logged-in branch (stubbed: store 1 cannot log in): a hostile target must not be followed.
    page.goto(base + "/", wait_until="load")
    page.wait_for_timeout(600)
    page.evaluate(
        "() => { window.customerAuthState = {isAuthenticated: true, isGuest: false};"
        " setTimeout(() => window.handleLoginAction('https://attacker.test/collect', false), 0); }"
    )
    page.wait_for_timeout(2000)
    checks["hostile_redirect_url"] = page.url
    checks["hostile_redirect_origin"] = page.evaluate("location.origin")
    checks["stayed_home_origin"] = page.evaluate("location.origin") == base
    checks["landed_path"] = page.evaluate("location.pathname")
    page.screenshot(path=out / "3-hostile-redirect.png")
    checks["theme_console_errors"] = errors

    return (
        checks["login_visible"]
        and not checks["profile_visible"]
        and checks["handle_login_type"] == "function"
        and checks["profile_url"].endswith("/account")
        and checks["drawer_open"] is True
        and checks["drawer_login_visible"]
        and (checks["auth_opens"] == 1 or "/auth/login" in (checks["after_login_click"] or ""))
        and checks["stayed_home_origin"]
        and checks["landed_path"] != "/collect"
        and not errors
    )


JOURNEYS = {
    "layout-shell": shell,
    "layout-nav": nav,
    "layout-carousel": carousel,
    "layout-phone": phone,
    "layout-loyalty": loyalty,
    "layout-404": not_found,
    "layout-auth": auth,
}
