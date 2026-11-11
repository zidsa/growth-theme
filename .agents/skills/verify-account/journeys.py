"""verify-account journeys: the phone input (js/features/phone-input.js) and the wishlist toggle
(js/features/wishlist.js) of growth-theme, driven against the live storefront as a guest.

Loaded by ../../verify-growth-theme/scripts/drive.py; run from the repo root:

    uv run --no-project --with playwright python -I .agents/skills/verify-growth-theme/scripts/drive.py account-phone-format

Nothing here submits a form, sends an OTP, subscribes a stock alert or touches account data.
"""

import re
from urllib.parse import parse_qs, urlparse


# A theme-bundle console error is an account-module defect; landbot/SDK noise is not ours.
def _theme_errors(page, sink):
    page.on(
        "console",
        lambda m: sink.append(f"{m.text} @ {m.location.get('url', '')}")
        if m.type == "error"
        and ("theme.js" in (m.location.get("url") or "") or "dist/" in (m.location.get("url") or ""))
        else None,
    )


def _out_of_stock_product(page, base):
    api = page.request.get(base + "/api/v1/products?page_size=20&availability=out_of_stock")
    return next(p for p in api.json()["results"] if not p["has_options"])


def _open_phone(page, base):
    """PDP of an out-of-stock product -> notify-me dialog open (never submitted). Returns the product."""
    product = _out_of_stock_product(page, base)
    page.goto(base + "/products/" + product["slug"], wait_until="load")
    page.wait_for_selector("[data-notify-me-btn]")
    page.locator("[data-notify-me-btn]").first.click()
    page.wait_for_selector("[data-phone-input] [data-phone-number-input]", state="visible")
    page.wait_for_timeout(500)
    return product


# Collects phone:change / phone:country-change on the wrapper, with their detail.
_LISTEN = """
(() => {
  const w = document.querySelector('[data-phone-input]');
  window.__phoneEvents = [];
  for (const name of ['phone:change', 'phone:country-change'])
    w.addEventListener(name, (e) => window.__phoneEvents.push({ name, detail: e.detail }));
})()
"""

_STATE = """
(() => {
  const w = document.querySelector('[data-phone-input]');
  return {
    shown: w.querySelector('[data-phone-number-input]').value,
    full: w.querySelector('[data-phone-full-value]').value,
    code: w.querySelector('[data-phone-country-code]').value,
    display: w.querySelector('[data-phone-country-display]').textContent.trim(),
  };
})()
"""


def _digits(s):
    return re.sub(r"\D", "", s)


# ── account-phone-format ─────────────────────────────────────────────────────
def phone_format(page, base, out, checks):
    """Typing into the national-number field: grouped as you type, digits kept, full value = dial + digits."""
    errors = []
    _theme_errors(page, errors)
    _open_phone(page, base)
    page.evaluate(_LISTEN)
    number = page.locator("[data-phone-input] [data-phone-number-input]").first
    number.click()

    initial = page.evaluate(_STATE)
    checks["initial"] = initial
    checks["initial_full_empty_when_no_digits"] = initial["full"] == ""

    # Type 1..14 digits one key at a time; after every key the invariants must hold.
    typed = "5123456789012"
    steps, bad, trailing = [], [], []
    for n in range(1, len(typed) + 1):
        if n == 1:
            number.press_sequentially(typed[0])
        else:
            number.press_sequentially(typed[n - 1])
        s = page.evaluate(_STATE)
        steps.append((typed[:n], s["shown"], s["full"]))
        if _digits(s["shown"]) != typed[:n]:
            bad.append(f"digits changed at {n}: {s['shown']!r}")
        if "  " in s["shown"] or s["shown"] != s["shown"].lstrip():
            bad.append(f"stray spaces at {n}: {s['shown']!r}")
        if s["shown"] != s["shown"].rstrip():
            trailing.append((n, s["shown"]))
        if s["full"] != "+966" + typed[:n]:
            bad.append(f"full value at {n}: {s['full']!r}")
    checks["typing_steps"] = steps
    checks["typing_violations"] = bad
    # FINDING (recorded, not a failure here; see formal-account `phone-spacing`): exactly 10 digits
    # leaves a trailing space, "512 345 6789 ".
    checks["finding_trailing_space_at_digits"] = trailing
    checks["shown_9_digits"] = next(s for t, s, f in steps if len(t) == 9)
    checks["shown_13_digits"] = steps[-1][1]
    page.screenshot(path=out / "1-typed.png")

    # Letters and punctuation never enter the value; the full value ignores them.
    number.fill("")
    number.press_sequentially("5a1-2 b3")
    s = page.evaluate(_STATE)
    checks["mixed_input"] = s
    mixed_ok = _digits(s["shown"]) == "5123" and s["full"] == "+9665123" and not re.search(r"[A-Za-z\-]", s["shown"])

    # Re-formatting an already formatted value is the identity (paste of "512 345 678").
    number.fill("512 345 678")
    s = page.evaluate(_STATE)
    checks["paste_formatted"] = s
    paste_ok = s["shown"] == "512 345 678" and s["full"] == "+966512345678"

    # Caret stays after the same digit when editing in the middle.
    number.fill("512345678")
    page.evaluate(
        "(() => { const i = document.querySelector('[data-phone-number-input]'); i.setSelectionRange(2, 2); })()"
    )
    page.keyboard.type("9")
    caret = page.evaluate(
        "(() => { const i = document.querySelector('[data-phone-number-input]');"
        " return { value: i.value, caret: i.selectionStart }; })()"
    )
    checks["mid_edit"] = caret
    digits_before_caret = len(_digits(caret["value"][: caret["caret"]]))
    caret_ok = _digits(caret["value"]) == "5192345678" and digits_before_caret == 3

    # Events: every keystroke announced phone:change with the same fullValue as the hidden input.
    events = page.evaluate("window.__phoneEvents")
    changes = [e for e in events if e["name"] == "phone:change"]
    checks["phone_change_events"] = len(changes)
    events_ok = bool(changes) and all(
        e["detail"]["dialCode"] == "+966" and re.fullmatch(r"\d*", e["detail"]["phoneNumber"]) for e in changes
    )
    last = changes[-1]["detail"] if changes else {}
    checks["last_event"] = last
    events_ok = events_ok and last.get("fullValue") == page.evaluate(_STATE)["full"]

    # Public API on the wrapper: validate / isValid / setPhoneNumber / reset.
    api = page.evaluate(
        """
(() => {
  const h = window.PhoneInput.get(document.querySelector('[data-phone-input]'));
  const r = {};
  h.setPhoneNumber('512345678'); r.valid9 = [h.validate(), h.isValid(), h.getValue(), h.getPhoneNumber()];
  h.setPhoneNumber('51234'); r.short = [h.validate(), h.isValid()];
  h.setPhoneNumber('51234567890123'); r.long = [h.validate(), h.isValid()];
  h.reset(); r.empty = [h.validate(), h.isValid(), h.getValue()];
  return r;
})()
"""
    )
    checks["api"] = api
    api_ok = (
        api["valid9"] == [None, True, "+966512345678", "512345678"]
        and api["short"][0] == "TOO_SHORT"
        and api["short"][1] is False
        and api["long"][0] == "TOO_LONG"
        and api["long"][1] is False
        and api["empty"] == ["EMPTY", False, ""]
    )

    # Observation, not a pass criterion: Arabic-Indic digits (the numerals an ar-SA keyboard can emit).
    number.fill("")
    number.fill("٥١٢٣٤٥٦٧٨")
    obs = page.evaluate(_STATE)
    checks["observation_arabic_indic_digits"] = {"typed": "٥١٢٣٤٥٦٧٨", **obs}
    page.screenshot(path=out / "2-after-api.png")

    checks["mixed_ok"], checks["paste_ok"], checks["caret_ok"] = mixed_ok, paste_ok, caret_ok
    checks["events_ok"], checks["api_ok"] = events_ok, api_ok
    checks["theme_console_errors"] = errors
    return (
        checks["initial"] == {"shown": "", "full": "", "code": "+966", "display": "+966"}
        and not bad
        and checks["shown_9_digits"] == "512 345 678"
        and mixed_ok
        and paste_ok
        and caret_ok
        and events_ok
        and api_ok
        and not errors
    )


# ── account-phone-country ────────────────────────────────────────────────────
def phone_country(page, base, out, checks):
    """The searchable country popover: open, filter, keyboard, select, close, state sync."""
    errors = []
    _theme_errors(page, errors)
    _open_phone(page, base)
    page.evaluate(_LISTEN)
    wrapper = "[data-phone-input]"
    number = page.locator(f"{wrapper} [data-phone-number-input]").first
    number.click()
    number.press_sequentially("512345678")

    trigger = page.locator(f"{wrapper} [data-slot='country-trigger']").first
    search = page.locator(f"{wrapper} [data-phone-country-search]").first
    options = f"{wrapper} [data-phone-country-list] .phone-country-option"

    def visible_dials():
        return page.evaluate(
            f"Array.from(document.querySelectorAll({options!r})).filter(o => !o.hidden).map(o => o.dataset.dialCode)"
        )

    def highlighted():
        return page.evaluate(
            f"Array.from(document.querySelectorAll({options!r})).filter(o => !o.hidden)"
            ".findIndex(o => o.hasAttribute('data-highlighted'))"
        )

    trigger.click()
    page.wait_for_timeout(500)
    checks["popover_open"] = page.evaluate(
        f"document.getElementById(document.querySelector('{wrapper} [data-slot=country-trigger]').getAttribute('popovertarget')).matches(':popover-open')"
    )
    checks["search_focused"] = page.evaluate(
        "document.activeElement && document.activeElement.hasAttribute('data-phone-country-search')"
    )
    total = len(visible_dials())
    checks["options_total"] = total
    hi = highlighted()
    selected_idx = page.evaluate(
        f"Array.from(document.querySelectorAll({options!r})).filter(o => !o.hidden).findIndex(o => o.dataset.dialCode === '+966')"
    )
    checks["open_highlight_is_selected"] = hi == selected_idx and hi >= 0
    page.screenshot(path=out / "1-popover-open.png")

    # Filter: Arabic name, English name, dial code, ISO code, whitespace, nonsense.
    def filt(q):
        search.fill(q)
        page.wait_for_timeout(150)
        no_results_visible = page.evaluate(
            "(() => { const n = document.querySelector('[data-phone-no-results]'); return n ? !n.hidden : null; })()"
        )
        return visible_dials(), no_results_visible

    ar_dials, _ = filt("مصر")
    en_dials, _ = filt("  EGYPT ")
    code_dials, _ = filt("eg")
    dial_dials, _ = filt("+20")
    none_dials, none_msg = filt("zzzzqq")
    all_dials, all_msg = filt("")
    checks["filter"] = {
        "ar": ar_dials,
        "en_padded_upper": en_dials,
        "iso": code_dials[:5],
        "dial": dial_dials[:5],
        "nonsense": none_dials,
        "nonsense_message": none_msg,
        "cleared": len(all_dials),
        "cleared_message": all_msg,
    }
    filter_ok = (
        ar_dials == ["+20"]
        and en_dials == ["+20"]
        and "+20" in code_dials
        and "+20" in dial_dials
        and none_dials == []
        and none_msg is True
        and len(all_dials) == total
        and all_msg is False
    )
    page.screenshot(path=out / "2-filter-egypt-ar.png")

    # Keyboard: Down / Up wrap inside the visible list; Enter selects the highlighted option.
    search.fill("")
    search.fill("a")  # many matches, first highlighted
    page.wait_for_timeout(150)
    n = len(visible_dials())
    start = highlighted()
    page.keyboard.press("ArrowUp")
    up_wrap = highlighted()
    page.keyboard.press("ArrowDown")
    down_back = highlighted()
    page.keyboard.press("ArrowDown")
    down_one = highlighted()
    checks["keyboard"] = {"visible": n, "start": start, "up_from_first": up_wrap, "down": down_back, "down2": down_one}
    keyboard_ok = start == 0 and up_wrap == n - 1 and down_back == 0 and down_one == 1

    # Enter on a chosen filter result: Egypt.
    search.fill("egypt")
    page.wait_for_timeout(150)
    page.keyboard.press("Enter")
    page.wait_for_timeout(300)
    s = page.evaluate(_STATE)
    checks["after_enter"] = s
    popover_closed = not page.evaluate(
        "document.getElementById(document.querySelector('[data-phone-input] [data-slot=country-trigger]').getAttribute('popovertarget')).matches(':popover-open')"
    )
    focus_back = page.evaluate("document.activeElement && document.activeElement.hasAttribute('data-phone-number-input')")
    selected = page.evaluate(
        f"Array.from(document.querySelectorAll({options!r})).filter(o => o.getAttribute('aria-selected') === 'true').map(o => o.dataset.dialCode)"
    )
    checks["aria_selected_dials"] = sorted(set(selected))
    select_ok = (
        s["code"] == "+20"
        and s["display"] == "+20"
        and s["full"] == "+20512345678"
        and s["shown"] == "512 345 678"
        and popover_closed
        and focus_back
        and set(selected) == {"+20"}
    )
    ev = page.evaluate("window.__phoneEvents")
    country_events = [e for e in ev if e["name"] == "phone:country-change"]
    checks["country_change_events"] = country_events
    event_ok = len(country_events) == 1 and country_events[0]["detail"]["dialCode"] == "+20" and (
        country_events[0]["detail"]["countryCode"] == "EG"
    )
    last_change = [e for e in ev if e["name"] == "phone:change"][-1]["detail"]
    event_ok = event_ok and last_change["fullValue"] == "+20512345678"
    page.screenshot(path=out / "3-egypt-selected.png")

    # Reopen: the highlighted row is the selected country; Escape closes and returns focus to the trigger.
    trigger.click()
    page.wait_for_timeout(400)
    reopen_hi = page.evaluate(
        f"(() => {{ const v = Array.from(document.querySelectorAll({options!r})).filter(o => !o.hidden);"
        " const i = v.findIndex(o => o.hasAttribute('data-highlighted')); return v[i] && v[i].dataset.dialCode; })()"
    )
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    esc_closed = not page.evaluate(
        "document.getElementById(document.querySelector('[data-phone-input] [data-slot=country-trigger]').getAttribute('popovertarget')).matches(':popover-open')"
    )
    esc_focus = page.evaluate("document.activeElement && document.activeElement.getAttribute('data-slot') === 'country-trigger'")
    checks["reopen_highlight"] = reopen_hi
    # FINDING (recorded, not a failure here; see formal-account `phone-escape`): the handler hides the
    # popover and focuses the trigger, but it never calls preventDefault, so the same Escape also cancels
    # the surrounding modal <dialog> and focus lands on the dialog's opener instead of the trigger.
    checks["escape"] = {
        "popover_closed": esc_closed,
        "focus_on_trigger": esc_focus,
        "finding_dialog_also_closed": page.evaluate("!document.getElementById('notify-me-dialog').open"),
    }

    # setDialCode through the public API picks the same state as a click.
    after_api = page.evaluate(
        "(() => { const h = window.PhoneInput.get(document.querySelector('[data-phone-input]'));"
        " h.setDialCode('+971'); return { dial: h.getDialCode(), value: h.getValue() }; })()"
    )
    checks["setDialCode"] = after_api
    api_ok = after_api == {"dial": "+971", "value": "+971512345678"}
    checks["theme_console_errors"] = errors

    checks.update(filter_ok=filter_ok, keyboard_ok=keyboard_ok, select_ok=select_ok, event_ok=event_ok)
    return (
        checks["popover_open"] is True
        and checks["search_focused"] is True
        and checks["open_highlight_is_selected"]
        and filter_ok
        and keyboard_ok
        and select_ok
        and event_ok
        and reopen_hi == "+20"
        and esc_closed
        and api_ok
        and not errors
    )


# ── account-wishlist-guest ───────────────────────────────────────────────────
# components/products/wishlist-button.jinja renders nothing unless store.settings.products.wishlist_enabled
# is true; store 1's settings do not enable it, so this journey injects the button exactly as the template
# emits it (data-wishlist-btn + data-product-id + aria-label) into the live page and lets the REAL theme.js
# wishlist module act on it. tests: formal-account `wishlist-template` renders the real template.
_BUTTON_HTML = (
    '<button type="button" class="btn btn-icon btn-icon-md" data-wishlist-btn data-product-id="{pid}" '
    'aria-label="Add to wishlist"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="size-6">'
    '<path d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5"/></svg></button>'
)


def _inject_buttons(page, ids):
    page.evaluate(
        """(html) => {
          document.querySelectorAll('[data-test-wishlist]').forEach((n) => n.remove());
          const host = document.createElement('div');
          host.setAttribute('data-test-wishlist', '');
          host.style.cssText = 'position:fixed;top:120px;left:20px;z-index:99999;background:#fff;padding:8px;display:flex;gap:8px';
          host.innerHTML = html;
          document.body.appendChild(host);
        }""",
        "".join(ids),
    )


def wishlist_guest(page, base, out, checks):
    """Guest: wishlist buttons render the empty heart; a click sends the shopper to /auth/login?redirect_to=<path>."""
    errors = []
    _theme_errors(page, errors)
    api = page.request.get(base + "/api/v1/products?page_size=2")
    pid = api.json()["results"][0]["id"]
    page.goto(base + "/products", wait_until="load")
    page.wait_for_selector("[data-product-card]")
    page.wait_for_function("window.wishlistManager && window.wishlistManager.isInitialized")

    mgr = page.evaluate(
        "({ zid: typeof window.zid, ready: wishlistManager.isZidReady, loggedIn: wishlistManager.isLoggedIn,"
        " init: wishlistManager.isInitialized, size: wishlistManager.wishlistProductIds.size })"
    )
    checks["manager"] = mgr
    checks["live_buttons_rendered"] = page.locator("[data-wishlist-btn]").count()
    checks["live_buttons_note"] = (
        "store 1 settings do not set products.wishlist_enabled, so the template renders no button"
    )
    # The SDK's own answer for a guest (a read): rejected, status 401.
    sdk = page.evaluate(
        "(async () => { try { await window.zid.account.wishlists(); return { ok: true }; }"
        " catch (e) { return { ok: false, status: e && e.status }; } })()"
    )
    checks["sdk_wishlists_as_guest"] = sdk

    _inject_buttons(page, [_BUTTON_HTML.format(pid=pid), _BUTTON_HTML.format(pid="")])
    page.evaluate("window.dispatchEvent(new Event('products-updated'))")
    state = page.evaluate(
        """Array.from(document.querySelectorAll('[data-wishlist-btn]')).map((b) => ({
          pid: b.dataset.productId, label: b.getAttribute('aria-label'), disabled: b.disabled,
          heart: b.innerHTML.includes('text-primary') && b.innerHTML.includes('M12.001 4.52853C') }))"""
    )
    checks["guest_buttons"] = state
    page.screenshot(path=out / "1-guest-buttons.png")

    # A button without product id is inert.
    before = page.url
    page.locator("[data-wishlist-btn]").nth(1).click()
    page.wait_for_timeout(400)
    checks["no_id_click_stays"] = page.url == before

    # Click the SVG inside the real button: closest() resolves the button, preventDefault, redirect to login.
    with page.expect_navigation(url=re.compile(r"/auth/login"), wait_until="commit", timeout=15000):
        page.locator("[data-wishlist-btn] svg").first.click()
    checks["redirected_to"] = page.url
    q = parse_qs(urlparse(page.url).query)
    checks["redirect_to_param"] = q.get("redirect_to")
    page.wait_for_timeout(800)
    page.screenshot(path=out / "2-login-page.png")
    checks["theme_console_errors"] = errors

    return (
        mgr["zid"] == "object"
        and mgr["ready"] is True
        and mgr["loggedIn"] is False
        and mgr["init"] is True
        and sdk == {"ok": False, "status": 401}
        and len(state) == 2
        and state[0]["label"] == "Add to wishlist"
        and state[0]["heart"] is True
        and state[0]["disabled"] is False
        and checks["no_id_click_stays"]
        and urlparse(page.url).path.endswith("/auth/login")
        and q.get("redirect_to") == ["/products"]
        and not errors
    )


# ── account-wishlist-toggle ──────────────────────────────────────────────────
def wishlist_toggle(page, base, out, checks):
    """Signed-in toggle with the SDK's account calls stubbed (store 1 cannot log in): loading, filled, empty, failure."""
    errors = []
    _theme_errors(page, errors)
    page.goto(base + "/products", wait_until="load")
    page.wait_for_function("window.wishlistManager && window.wishlistManager.isInitialized")
    writes = []
    page.on(
        "request",
        lambda r: writes.append(f"{r.method} {r.url}")
        if r.method != "GET" and "wishlist" in r.url.lower()
        else None,
    )

    # Stub only the three account calls; the module under test is the real one. The SDK's `account`
    # object is frozen, so swap `window.zid` for a copy whose `account` carries the stubs.
    page.evaluate(
        """() => {
          window.__calls = [];
          window.__gate = { add: null, remove: null };
          const hold = (key, result) => new Promise((resolve, reject) => {
            window.__gate[key] = { ok: () => resolve(result), fail: () => reject(new Error('stub')) };
          });
          window.zid = { ...window.zid, account: { ...window.zid.account,
            wishlists: async () => ({ results: [{ id: 'P-IN' }] }),
            addToWishlists: (body, opts) => { __calls.push(['add', body, opts]); return hold('add', { ok: true }); },
            removeFromWishlist: (id, opts) => { __calls.push(['remove', id, opts]); return hold('remove', {}); } } };
        }"""
    )
    _inject_buttons(page, [_BUTTON_HTML.format(pid="P-IN"), _BUTTON_HTML.format(pid="P-OUT")])
    page.evaluate("wishlistManager.refresh()")
    page.wait_for_function("wishlistManager.isLoggedIn === true")

    def snap(pid):
        return page.evaluate(
            """(pid) => { const b = document.querySelector(`[data-wishlist-btn][data-product-id="${pid}"]`);
            return { label: b.getAttribute('aria-label'), disabled: b.disabled,
              kind: b.innerHTML.includes('C22B51') ? 'filled' : b.innerHTML.includes('animate-spin') ? 'loading' : 'empty' }; }""",
            pid,
        )

    synced = {"in": snap("P-IN"), "out": snap("P-OUT")}
    checks["after_sync"] = synced
    page.screenshot(path=out / "1-synced.png")

    # add: P-OUT -> loading (disabled, "Loading") -> filled
    page.locator('[data-wishlist-btn][data-product-id="P-OUT"]').click()
    page.wait_for_function("window.__calls.length === 1")
    loading = snap("P-OUT")
    page.evaluate("__gate.add.ok()")
    page.wait_for_function("wishlistManager.isInWishlist('P-OUT')")
    added = snap("P-OUT")
    checks["add"] = {"loading": loading, "after": added}

    # remove: P-OUT -> loading -> empty
    page.locator('[data-wishlist-btn][data-product-id="P-OUT"]').click()
    page.wait_for_function("window.__calls.length === 2")
    page.evaluate("__gate.remove.ok()")
    page.wait_for_function("!wishlistManager.isInWishlist('P-OUT')")
    removed = snap("P-OUT")
    checks["remove"] = removed

    # add fails: back to empty, not in the set
    page.locator('[data-wishlist-btn][data-product-id="P-OUT"]').click()
    page.wait_for_function("window.__calls.length === 3")
    page.evaluate("__gate.add.fail()")
    page.wait_for_timeout(300)
    add_failed = {"state": snap("P-OUT"), "in_set": page.evaluate("wishlistManager.isInWishlist('P-OUT')")}
    checks["add_failed"] = add_failed

    # remove fails on P-IN: stays filled
    page.locator('[data-wishlist-btn][data-product-id="P-IN"]').click()
    page.wait_for_function("window.__calls.length === 4")
    page.evaluate("__gate.remove.fail()")
    page.wait_for_timeout(300)
    remove_failed = {"state": snap("P-IN"), "in_set": page.evaluate("wishlistManager.isInWishlist('P-IN')")}
    checks["remove_failed"] = remove_failed

    calls = page.evaluate("__calls")
    checks["sdk_calls"] = calls
    checks["unstubbed_wishlist_writes"] = writes
    page.screenshot(path=out / "2-final.png")
    checks["theme_console_errors"] = errors

    return (
        synced["in"] == {"label": "Remove from wishlist", "disabled": False, "kind": "filled"}
        and synced["out"] == {"label": "Add to wishlist", "disabled": False, "kind": "empty"}
        and loading == {"label": "Loading", "disabled": True, "kind": "loading"}
        and added == {"label": "Remove from wishlist", "disabled": False, "kind": "filled"}
        and removed == {"label": "Add to wishlist", "disabled": False, "kind": "empty"}
        and add_failed["state"]["kind"] == "empty"
        and add_failed["in_set"] is False
        and remove_failed["state"]["kind"] == "filled"
        and remove_failed["in_set"] is True
        and [c[0] for c in calls] == ["add", "remove", "add", "remove"]
        and calls[0][1] == {"product_ids": ["P-OUT"]}
        and calls[0][2] == {"showErrorNotification": True}
        and calls[1][1] == "P-OUT"
        and not writes
        and not errors
    )


JOURNEYS = {
    "account-phone-format": phone_format,
    "account-phone-country": phone_country,
    "account-wishlist-guest": wishlist_guest,
    "account-wishlist-toggle": wishlist_toggle,
}
