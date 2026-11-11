"""Content-pages journeys for verify-growth-theme's drive.py.

Each journey: fn(page, base, out, checks) -> bool. Loaded by
.agents/skills/verify-growth-theme/scripts/drive.py, which imports JOURNEYS from every
.agents/skills/verify-*/journeys.py.

Covers templates/faqs, templates/page, templates/shipping_payment, components/shipping-payment/*
and assets/js/shipping-payment.js. All read-only against store 1: no cart writes, no forms.

vitrin's real routes (zidsa/vitrin storefront/routes.py):
  /faqs                       -> templates/faqs.jinja            (data: /api/v1/pages/faqs)
  /pages/{slug}               -> templates/page.jinja            (data: /api/v1/pages/{slug})
  /shipping-and-payment       -> templates/shipping_payment.jinja (data: /api/v1/shipping-and-payment)
`/shipping-payment` is NOT a route (404 on every store); the page lives at /shipping-and-payment.
"""

import html
import json
import re

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

POLICY_SLUGS = ["privacy-policy", "terms-and-conditions"]  # store 1 has no other page slugs
XSS_MARK = "__cities_xss__"


# ── helpers ────────────────────────────────────────────────────────────────


def _api(page, base, path):
    r = page.request.get(base + "/api/v1" + path)
    return r.status, (r.json() if r.ok else None)


def _theme_console_errors(page):
    """Collect console errors / page errors into a list for the rest of the journey."""
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    return errors


def _own_errors(errors):
    """Errors that come from the theme, not from the shared testing backend or the chat widget."""
    noise = ("Failed to load resource", "favicon", "landbot", "chatbot.com", "net::ERR")
    return [e for e in errors if not any(n in e for n in noise)]


def _amount(money):
    """'21.01 SAR' -> '21.01'. A site script swaps the currency code for a symbol glyph after load."""
    return money.split()[0]


def _open_sp(page, base):
    page.goto(base + "/shipping-and-payment", wait_until="load")
    page.wait_for_selector("#shipping-methods-data", state="attached", timeout=30000)
    page.wait_for_timeout(500)  # DOMContentLoaded handlers + el-disclosure upgrade


def _expanded(page, target):
    return page.evaluate(
        "t => document.querySelector(`[commandfor='${t}']`).getAttribute('aria-expanded')", target
    )


def _panel_visible(page, target):
    return page.evaluate(
        "t => { const e = document.getElementById(t); return !e.hidden && e.getBoundingClientRect().height > 0; }",
        target,
    )


# ── faqs ───────────────────────────────────────────────────────────────────


def faqs(page, base, out, checks):
    errors = _theme_console_errors(page)
    status, data = _api(page, base, "/pages/faqs")
    items = data["content"]
    checks["api_faqs"] = len(items)
    resp = page.goto(base + "/faqs", wait_until="load")
    checks["status"] = resp.status
    page.wait_for_selector("el-disclosure", state="attached", timeout=30000)
    page.wait_for_timeout(500)
    checks["h1"] = page.locator("h1").inner_text().strip()
    checks["breadcrumb_current"] = page.locator("nav[aria-label] [aria-current='page']").first.inner_text().strip()
    checks["rendered_items"] = page.locator("el-disclosure[id^='faq-']").count()
    checks["questions_match_api"] = [
        t.strip() for t in page.locator("button[commandfor^='faq-'] span.font-semibold").all_inner_texts()
    ] == [f["question"].strip() for f in items]
    checks["first_open_rest_closed"] = page.evaluate(
        "() => [...document.querySelectorAll(\"button[commandfor^='faq-']\")].map(b => b.getAttribute('aria-expanded'))"
    ) == ["true"] + ["false"] * (len(items) - 1)
    checks["first_visible"] = _panel_visible(page, "faq-1")
    checks["second_hidden"] = not _panel_visible(page, "faq-2")
    page.screenshot(path=out / "1-faqs.png", full_page=False)
    # Open the second, then close the first.
    page.locator("button[commandfor='faq-2']").click()
    page.wait_for_function("() => document.querySelector(\"[commandfor='faq-2']\").getAttribute('aria-expanded') === 'true'")
    page.wait_for_timeout(400)
    checks["second_opens"] = _expanded(page, "faq-2") == "true" and _panel_visible(page, "faq-2")
    page.locator("button[commandfor='faq-1']").click()
    page.wait_for_function("() => document.querySelector(\"[commandfor='faq-1']\").getAttribute('aria-expanded') === 'false'")
    page.wait_for_timeout(400)
    checks["first_closes"] = _expanded(page, "faq-1") == "false" and not _panel_visible(page, "faq-1")
    checks["second_stays_open"] = _expanded(page, "faq-2") == "true"
    page.screenshot(path=out / "2-faq2-open.png", full_page=False)
    # /pages/faqs must hand over to /faqs (vitrin redirect), keeping the FAQ template.
    page.goto(base + "/pages/faqs", wait_until="load")
    checks["pages_faqs_redirects_to"] = page.url
    checks["console_errors"] = _own_errors(errors)
    return (
        status == 200
        and resp.status == 200
        and checks["rendered_items"] == len(items) >= 2
        and checks["questions_match_api"]
        and checks["first_open_rest_closed"]
        and checks["first_visible"]
        and checks["second_hidden"]
        and checks["second_opens"]
        and checks["first_closes"]
        and checks["second_stays_open"]
        and page.url.rstrip("/").endswith("/faqs")
        and not checks["console_errors"]
    )


# ── custom / policy pages ──────────────────────────────────────────────────


def page_content(page, base, out, checks):
    errors = _theme_console_errors(page)
    ok = True
    for slug in POLICY_SLUGS:
        status, data = _api(page, base, f"/pages/{slug}")
        resp = page.goto(base + f"/pages/{slug}", wait_until="load")
        page.wait_for_selector("h1", timeout=30000)
        h1 = page.locator("h1").inner_text().strip()
        crumb = page.locator("nav[aria-label] [aria-current='page']").first.inner_text().strip()
        home_link = page.locator("nav[aria-label] a").first.get_attribute("href")
        body_text = page.locator("div.prose-theme").inner_text()
        body_html = page.locator("div.prose-theme").inner_html()
        # The API content is HTML: compare its visible text prefix with the rendered text.
        squash = lambda t: re.sub(r"\s+", "", html.unescape(t))  # &nbsp; and layout whitespace differ
        api_text = squash(re.sub(r"<[^>]+>", "", data["content"]))[:60]
        rendered_text = squash(body_text)
        row = {
            "http": resp.status,
            "api_title": data["title"],
            "h1": h1,
            "breadcrumb_current": crumb,
            "home_link": home_link,
            "content_prefix_in_dom": api_text in rendered_text,
            "content_is_html": "<" in body_html,
            "title_tag": page.title(),
        }
        checks[slug] = row
        page.screenshot(path=out / f"{slug}.png", full_page=False)
        ok &= (
            resp.status == 200
            and h1 == data["title"].strip()
            and crumb == h1
            and home_link in ("/", base + "/")
            and row["content_prefix_in_dom"]
            and data["title"].strip() in row["title_tag"]
        )
    # Unknown slug: vitrin 404s (the theme page is not rendered with an empty page).
    r = page.goto(base + "/pages/does-not-exist-xyz", wait_until="load")
    checks["unknown_slug_status"] = r.status
    ok &= r.status == 404
    checks["console_errors"] = _own_errors(errors)
    return ok and not checks["console_errors"]


# ── shipping & payment ─────────────────────────────────────────────────────


def shipping_payment_page(page, base, out, checks):
    errors = _theme_console_errors(page)
    r404 = page.request.get(base + "/shipping-payment")
    checks["legacy_path_/shipping-payment_status"] = r404.status  # not a vitrin route
    status, api = _api(page, base, "/shipping-and-payment")
    methods, pays, banks = api["shipping_methods"], api["payment_methods"], api["banks"]
    checks["api_counts"] = {"shipping": len(methods), "payment": len(pays), "banks": len(banks)}
    _open_sp(page, base)
    checks["h1"] = page.locator("h1").inner_text().strip()
    checks["breadcrumb_current"] = page.locator("nav[aria-label] [aria-current='page']").first.inner_text().strip()
    # Desktop table: one row per method (1280 px viewport shows the md:block copy).
    rows = page.locator("#shipping-options .hidden.md\\:block .flex.items-center.gap-6")
    checks["table_rows"] = rows.count()
    row_names = [
        rows.nth(i).locator("span.text-foreground.text-xs.uppercase").first.text_content().strip()  # text_content: CSS uppercases inner_text
        for i in range(rows.count())
    ]
    checks["table_names_match_api"] = row_names == [m["name"].strip() for m in methods]
    # Shipping cost / COD text per row, against the API strings.
    cost_ok, cod_ok = True, True
    for i, m in enumerate(methods):
        cells = rows.nth(i).locator(":scope > div")
        cost_txt = cells.nth(2).text_content()
        cod_txt = cells.nth(3).text_content()
        if m["cost"]:
            cost_ok &= all(_amount(c["cost_string"]) in cost_txt for c in m["cost"])
        else:
            cost_ok &= bool(cost_txt.strip())  # "Free"
        if m["cod_enabled"]:
            if m["cod_fee"]:
                cod_ok &= all(_amount(c["cod_fee_string"]) in cod_txt for c in m["cod_fee"])
        else:
            cod_ok &= bool(cod_txt.strip())
    checks["cost_text_matches_api"] = cost_ok
    checks["cod_text_matches_api"] = cod_ok
    # "+N more" triggers appear exactly for methods with more than 3 areas.
    want_triggers = [m["id"] for m in methods if len(m["delivery_option_cities"] or []) > 3]
    got_triggers = page.locator("#shipping-options [data-cities-trigger]").evaluate_all(
        "els => els.map(e => Number(e.dataset.methodId))"
    )
    checks["more_triggers_match_api"] = got_triggers == want_triggers
    # Accordion defaults: shipping open, payment closed, banks present and closed.
    checks["defaults"] = {
        "shipping": _expanded(page, "shipping-options"),
        "payment": _expanded(page, "payment-options"),
        "banks": _expanded(page, "bank-accounts"),
    }
    checks["shipping_visible"] = _panel_visible(page, "shipping-options")
    checks["payment_hidden"] = not _panel_visible(page, "payment-options")
    page.screenshot(path=out / "1-shipping-open.png", full_page=False)
    # Open payment and banks.
    page.locator("button[commandfor='payment-options']").click()
    page.wait_for_function("() => document.querySelector(\"[commandfor='payment-options']\").getAttribute('aria-expanded') === 'true'")
    page.wait_for_timeout(400)
    checks["payment_opens"] = _panel_visible(page, "payment-options")
    pay_imgs = page.locator("#payment-options img").count()
    checks["payment_icons"] = pay_imgs
    checks["payment_icons_match_api"] = pay_imgs == sum(len(p.get("icons") or []) for p in pays)
    page.screenshot(path=out / "2-payment-open.png", full_page=False)
    page.locator("button[commandfor='bank-accounts']").click()
    page.wait_for_function("() => document.querySelector(\"[commandfor='bank-accounts']\").getAttribute('aria-expanded') === 'true'")
    page.wait_for_timeout(400)
    checks["banks_open"] = _panel_visible(page, "bank-accounts")
    bank_cards = page.locator("#bank-accounts .rounded.border.px-4.py-3")
    checks["bank_cards"] = bank_cards.count()
    bank_text = page.locator("#bank-accounts").inner_text()
    checks["bank_ibans_match_api"] = all(b["iban"] in bank_text for b in banks if b.get("iban"))
    checks["bank_names_match_api"] = all(b["bank"]["name"] in bank_text for b in banks)
    checks["copy_buttons"] = page.locator("[data-copy-btn]").count()
    checks["copy_buttons_match_api"] = checks["copy_buttons"] == sum(
        bool(b.get("account_number")) + bool(b.get("iban")) for b in banks
    )
    page.screenshot(path=out / "3-banks-open.png", full_page=False)
    # Close shipping.
    page.locator("button[commandfor='shipping-options']").click()
    page.wait_for_function("() => document.querySelector(\"[commandfor='shipping-options']\").getAttribute('aria-expanded') === 'false'")
    page.wait_for_timeout(400)
    checks["shipping_closes"] = not _panel_visible(page, "shipping-options")
    checks["console_errors"] = _own_errors(errors)
    return (
        r404.status == 404
        and checks["h1"] != ""
        and checks["table_rows"] == len(methods)
        and checks["table_names_match_api"]
        and cost_ok
        and cod_ok
        and checks["more_triggers_match_api"]
        and checks["defaults"] == {"shipping": "true", "payment": "false", "banks": "false"}
        and checks["shipping_visible"]
        and checks["payment_hidden"]
        and checks["payment_opens"]
        and checks["payment_icons_match_api"]
        and checks["banks_open"]
        and checks["bank_cards"] == len(banks)
        and checks["bank_ibans_match_api"]
        and checks["bank_names_match_api"]
        and checks["copy_buttons_match_api"]
        and checks["shipping_closes"]
        and not checks["console_errors"]
    )


def shipping_payment_mobile(page, base, out, checks):
    errors = _theme_console_errors(page)
    page.set_viewport_size({"width": 390, "height": 844})
    _, api = _api(page, base, "/shipping-and-payment")
    methods = api["shipping_methods"]
    _open_sp(page, base)
    cards = page.locator("#shipping-options .md\\:hidden > div > div")
    checks["cards"] = cards.count()
    checks["cards_visible"] = cards.first.is_visible()
    checks["table_hidden"] = not page.locator("#shipping-options .hidden.md\\:block").first.is_visible()
    names = [
        cards.nth(i).locator("span.text-sm").first.inner_text().strip() for i in range(cards.count())
    ]
    checks["names_match_api"] = names == [m["name"].strip() for m in methods]
    want = [m["id"] for m in methods if len(m["delivery_option_cities"] or []) > 3]
    got = page.locator("[data-cities-trigger-mobile]").evaluate_all("els => els.map(e => Number(e.dataset.methodId))")
    checks["mobile_triggers_match_api"] = got == want
    page.screenshot(path=out / "1-mobile-cards.png", full_page=False)
    # Mobile trigger opens the same dialog.
    trig = page.locator("[data-cities-trigger-mobile]").first
    mid = int(trig.get_attribute("data-method-id"))
    trig.click()
    page.wait_for_function("() => document.getElementById('cities-dialog').open", timeout=5000)
    page.wait_for_timeout(400)
    checks["dialog_open"] = page.evaluate("() => document.getElementById('cities-dialog').open")
    expect_n = len(next(m for m in methods if m["id"] == mid)["delivery_option_cities"])
    checks["dialog_tags"] = page.locator("#cities-dialog .badge").count()
    checks["dialog_title"] = page.locator("[data-cities-dialog-title]").inner_text().strip()
    page.screenshot(path=out / "2-mobile-dialog.png", full_page=False)
    # Mobile footer "Close" button closes it.
    page.locator("#cities-dialog button[command='close']").locator("visible=true").first.click()
    page.wait_for_function("() => !document.getElementById('cities-dialog').open", timeout=5000)
    checks["dialog_closed"] = not page.evaluate("() => document.getElementById('cities-dialog').open")
    checks["console_errors"] = _own_errors(errors)
    return (
        checks["cards"] == len(methods)
        and checks["cards_visible"]
        and checks["table_hidden"]
        and checks["names_match_api"]
        and checks["mobile_triggers_match_api"]
        and checks["dialog_open"]
        and checks["dialog_tags"] == expect_n
        and checks["dialog_closed"]
        and not checks["console_errors"]
    )


# ── cities dialog ──────────────────────────────────────────────────────────


def cities_dialog(page, base, out, checks):
    errors = _theme_console_errors(page)
    _, api = _api(page, base, "/shipping-and-payment")
    methods = api["shipping_methods"]
    big = max(methods, key=lambda m: len(m["delivery_option_cities"] or []))
    cities = [c["name"] for c in big["delivery_option_cities"]]
    _open_sp(page, base)
    trig = page.locator(f"#shipping-options [data-cities-trigger][data-method-id='{big['id']}']")
    checks["method"] = {"id": big["id"], "name": big["name"], "cities": len(cities)}
    checks["trigger_text"] = trig.inner_text().strip()
    trig.click()
    page.wait_for_function("() => document.getElementById('cities-dialog').open", timeout=5000)
    page.wait_for_timeout(500)
    checks["title"] = page.locator("[data-cities-dialog-title]").inner_text().strip()
    tags = page.locator("#cities-dialog .badge")
    checks["tags_total"] = tags.count()
    checks["header_count"] = page.locator("[data-country-section] .text-xs").first.inner_text().strip()
    checks["tags_match_api"] = sorted(t.strip() for t in tags.all_inner_texts()) == sorted(c.strip() for c in cities)
    checks["empty_hidden"] = page.locator("[data-cities-empty]").evaluate("e => e.classList.contains('hidden')")
    page.screenshot(path=out / "1-dialog-open.png", full_page=False)
    # Search narrows the list; case-insensitive; matches substring.
    term = cities[len(cities) // 2][:3]
    want = [c for c in cities if term.lower() in c.lower() or term.lower() in "other"]
    page.locator("[data-cities-search]").fill(term)
    page.wait_for_timeout(300)
    got = sorted(t.strip() for t in page.locator("#cities-dialog .badge").all_inner_texts())
    checks["search_term"] = term
    checks["search_matches"] = len(got)
    checks["search_matches_expected"] = got == sorted(want)
    page.screenshot(path=out / "2-dialog-search.png", full_page=False)
    # Nonsense term: empty state shows, no tags.
    page.locator("[data-cities-search]").fill("zzzzqqqq")
    page.wait_for_timeout(300)
    checks["empty_shown"] = page.locator("[data-cities-empty]").evaluate("e => !e.classList.contains('hidden')")
    checks["tags_after_nonsense"] = page.locator("#cities-dialog .badge").count()
    page.screenshot(path=out / "3-dialog-empty.png", full_page=False)
    # Clearing restores everything.
    page.locator("[data-cities-search]").fill("")
    page.wait_for_timeout(300)
    checks["restored"] = page.locator("#cities-dialog .badge").count() == len(cities)
    # Close button closes the dialog.
    page.locator("#cities-dialog button[command='close']").first.click()
    page.wait_for_function("() => !document.getElementById('cities-dialog').open", timeout=5000)
    checks["closed"] = not page.evaluate("() => document.getElementById('cities-dialog').open")
    # Reopening a different (smaller) method resets search + list (no stale tags).
    small = next(m for m in methods if 3 < len(m["delivery_option_cities"] or []) < len(cities))
    page.locator(f"#shipping-options [data-cities-trigger][data-method-id='{small['id']}']").click()
    page.wait_for_function("() => document.getElementById('cities-dialog').open", timeout=5000)
    page.wait_for_timeout(300)
    checks["second_method_tags"] = page.locator("#cities-dialog .badge").count()
    checks["second_method_title"] = page.locator("[data-cities-dialog-title]").inner_text().strip()
    checks["search_reset"] = page.locator("[data-cities-search]").input_value() == ""
    checks["console_errors"] = _own_errors(errors)
    return (
        checks["title"] == big["name"].strip()
        and checks["tags_total"] == len(cities)
        and checks["tags_match_api"]
        and checks["empty_hidden"]
        and checks["search_matches_expected"]
        and checks["empty_shown"]
        and checks["tags_after_nonsense"] == 0
        and checks["restored"]
        and checks["closed"]
        and checks["second_method_tags"] == len(small["delivery_option_cities"])
        and checks["second_method_title"] == small["name"].strip()
        and checks["search_reset"]
        and not checks["console_errors"]
    )


def _page_with_countries(page, base, country_name):
    """Open /shipping-and-payment with store 1's methods, every other city given a country.

    Store 1's cities carry no country (the dialog groups them under "Other"), so the
    multi-country branch of shipping-payment.js is unreachable with live data. An init
    script rewrites the embedded #shipping-methods-data JSON on DOMContentLoaded, before
    the theme's own listener runs; template, CSS and the real assets/js/shipping-payment.js
    are untouched. (page.route() is not used: interception makes the cross-origin
    theme-asset request fail CORS.)
    """
    page.add_init_script(
        "(() => { const name = " + json.dumps(country_name) + ";"
        """
          document.addEventListener('DOMContentLoaded', () => {
            const el = document.getElementById('shipping-methods-data');
            if (!el) return;
            const data = JSON.parse(el.textContent);
            data.forEach(m => (m.delivery_option_cities || []).forEach((c, i) => {
              c.country = {name: i % 2 ? name : 'Saudi Arabia'};
            }));
            el.textContent = JSON.stringify(data);
          });
        })();"""
    )
    _open_sp(page, base)


def cities_dialog_countries(page, base, out, checks):
    errors = _theme_console_errors(page)
    _, api = _api(page, base, "/shipping-and-payment")
    big = max(api["shipping_methods"], key=lambda m: len(m["delivery_option_cities"] or []))
    n = len(big["delivery_option_cities"])
    _page_with_countries(page, base, "United Arab Emirates")
    page.locator(f"#shipping-options [data-cities-trigger][data-method-id='{big['id']}']").click()
    page.wait_for_function("() => document.getElementById('cities-dialog').open", timeout=5000)
    page.wait_for_timeout(400)
    sections = page.locator("[data-country-section]")
    checks["sections"] = sections.count()
    checks["triggers"] = page.locator("[data-country-trigger]").count()
    checks["tags_total"] = page.locator("#cities-dialog .badge").count()
    checks["all_open_initially"] = page.evaluate(
        "() => [...document.querySelectorAll('[data-country-content]')].every(e => !e.classList.contains('hidden') && e.getBoundingClientRect().height > 0)"
    )
    page.screenshot(path=out / "1-two-countries-open.png", full_page=False)
    # Collapse the first country: content hides, icon loses rotate-180; the second stays open.
    page.locator("[data-country-trigger]").first.click()
    page.wait_for_timeout(200)
    checks["first_collapsed"] = page.locator("[data-country-content]").first.evaluate(
        "e => e.classList.contains('hidden')"
    )
    checks["first_icon_unrotated"] = page.locator("[data-country-icon]").first.evaluate(
        "e => !e.classList.contains('rotate-180')"
    )
    checks["second_still_open"] = page.locator("[data-country-content]").nth(1).evaluate(
        "e => !e.classList.contains('hidden')"
    )
    page.screenshot(path=out / "2-first-collapsed.png", full_page=False)
    page.locator("[data-country-trigger]").first.click()
    page.wait_for_timeout(200)
    checks["first_reopened"] = page.locator("[data-country-content]").first.evaluate(
        "e => !e.classList.contains('hidden')"
    )
    # Searching by country name keeps that country's cities only.
    page.locator("[data-cities-search]").fill("emirates")
    page.wait_for_timeout(300)
    checks["search_by_country_sections"] = page.locator("[data-country-section]").count()
    checks["search_by_country_tags"] = page.locator("#cities-dialog .badge").count()
    page.screenshot(path=out / "3-search-country.png", full_page=False)
    checks["console_errors"] = _own_errors(errors)
    return (
        checks["sections"] == 2
        and checks["triggers"] == 2
        and checks["tags_total"] == n
        and checks["all_open_initially"]
        and checks["first_collapsed"]
        and checks["first_icon_unrotated"]
        and checks["second_still_open"]
        and checks["first_reopened"]
        and checks["search_by_country_sections"] == 1
        and 0 < checks["search_by_country_tags"] < n
        and not checks["console_errors"]
    )


def cities_dialog_country_markup_escaped(page, base, out, checks):
    """A country name containing markup must be shown as text, never become DOM.

    EXPECTED TO FAIL against growth-theme 2b1c67d: renderCities() puts the country name
    into innerHTML (assets/js/shipping-payment.js, headerEl / triggerEl templates).
    Recorded as a finding; the assertion is not loosened.
    """
    errors = _theme_console_errors(page)
    _, api = _api(page, base, "/shipping-and-payment")
    big = max(api["shipping_methods"], key=lambda m: len(m["delivery_option_cities"] or []))
    payload = f'<img src=x id="{XSS_MARK}" onerror="window.{XSS_MARK}=1">Evil'
    _page_with_countries(page, base, payload)
    page.locator(f"#shipping-options [data-cities-trigger][data-method-id='{big['id']}']").click()
    page.wait_for_function("() => document.getElementById('cities-dialog').open", timeout=5000)
    page.wait_for_timeout(800)
    checks["injected_element_in_dom"] = page.locator(f"#{XSS_MARK}").count() > 0
    if checks["injected_element_in_dom"]:
        try:
            page.wait_for_function(f"() => window.{XSS_MARK} === 1", timeout=5000)
        except PlaywrightTimeoutError:
            pass
    checks["handler_ran"] = bool(page.evaluate(f"() => window.{XSS_MARK} === 1"))
    checks["header_text"] = page.locator("[data-country-trigger]").first.inner_text().strip()[:80]
    page.screenshot(path=out / "1-country-markup.png", full_page=False)
    checks["console_errors"] = _own_errors(errors)
    conds = {"no_injected_element": not checks["injected_element_in_dom"], "no_handler_ran": not checks["handler_ran"]}
    checks["failed_checks"] = [k for k, ok in conds.items() if not ok]
    return not checks["failed_checks"]


# ── copy to clipboard ──────────────────────────────────────────────────────


def copy_bank_details(page, base, out, checks):
    errors = _theme_console_errors(page)
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=base)
    _, api = _api(page, base, "/shipping-and-payment")
    bank = next(b for b in api["banks"] if b.get("iban"))
    _open_sp(page, base)
    page.locator("button[commandfor='bank-accounts']").click()
    page.wait_for_function("() => document.querySelector(\"[commandfor='bank-accounts']\").getAttribute('aria-expanded') === 'true'")
    page.wait_for_timeout(400)
    btn = page.locator(f"[data-copy-btn][data-copy-value='{bank['iban']}']").first
    checks["iban"] = bank["iban"]
    before = btn.inner_html()
    page.screenshot(path=out / "1-before-copy.png", full_page=False)
    btn.click()
    page.wait_for_function(
        "v => document.querySelector(`[data-copy-btn][data-copy-value='${v}'] svg.text-success`)", arg=bank["iban"], timeout=5000
    )
    checks["clipboard"] = page.evaluate("() => navigator.clipboard.readText()")
    checks["success_icon"] = True
    page.screenshot(path=out / "2-copied.png", full_page=False)
    page.wait_for_timeout(2300)
    checks["icon_reverted"] = btn.inner_html() == before
    # Account number button copies the account number, not the IBAN.
    if bank.get("account_number"):
        page.locator(f"[data-copy-btn][data-copy-value='{bank['account_number']}']").first.click()
        page.wait_for_timeout(500)
        checks["clipboard_account"] = page.evaluate("() => navigator.clipboard.readText()")
    checks["console_errors"] = _own_errors(errors)
    return (
        checks["clipboard"] == bank["iban"]
        and checks["icon_reverted"]
        and checks.get("clipboard_account", bank.get("account_number")) == bank.get("account_number")
        and not checks["console_errors"]
    )


JOURNEYS = {
    "content-pages-faqs": faqs,
    "content-pages-page-content": page_content,
    "content-pages-shipping-payment": shipping_payment_page,
    "content-pages-shipping-mobile": shipping_payment_mobile,
    "content-pages-cities-dialog": cities_dialog,
    "content-pages-cities-countries": cities_dialog_countries,
    "content-pages-cities-country-escaped": cities_dialog_country_markup_escaped,
    "content-pages-copy-bank": copy_bank_details,
}

# Recorded product bugs (drive.py exits 0 with FINDING while exactly these checks fail).
KNOWN = {
    "content-pages-cities-country-escaped": (
        {"no_injected_element", "no_handler_ran"},
        "the cities dialog writes the country name into the DOM as HTML (innerHTML); markup in it runs",
    ),
}
