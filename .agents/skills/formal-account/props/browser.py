"""Browser-side properties of formal-account: the REAL assets/js/features/phone-input.js and
wishlist.js, loaded into headless Chrome (served by request interception, no server, no build step) with
the real phone-input.jinja output as DOM and a stubbed `window.zid.account` (the SDK) for the wishlist.

    ROOT=<repo> uv run --no-project --with jinja2 --with playwright python -I props/browser.py

Prints `PROPERTY <id> <ok|finding> <signature>`.
"""

import json
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import ROOT, make_env, report, report_finding  # noqa: E402

CHROME = os.environ.get(
    "CHROME",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" if sys.platform == "darwin" else "/usr/bin/google-chrome",
)
ORIGIN = "http://account.test"
ENV = make_env()


def phone_html(**ctx):
    ctx.setdefault("session", {"lang": "en"})
    return ENV.get_template("components/ui/phone-input.jinja").render(**ctx)


def serve(context, pages):
    """pages: path -> html. /assets/* is read from the checkout."""

    def handler(route):
        url = route.request.url
        if not url.startswith(ORIGIN):
            return route.abort()
        path = url[len(ORIGIN):].split("?")[0]
        if path in pages:
            return route.fulfill(status=200, content_type="text/html", body=pages[path])
        if path.startswith("/assets/"):
            target = ROOT / path[1:]
            if target.is_file():
                return route.fulfill(status=200, content_type="text/javascript", body=target.read_text())
        return route.fulfill(status=404, body="not found")

    context.route("**/*", handler)


def doc(body, module, lang="en", init_script=""):
    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><script>{init_script}</script></head>'
        f'<body>{body}<script type="module" src="/assets/js/features/{module}.js"></script></body></html>'
    )


def digits(s):
    return re.sub(r"\D", "", s)


# ─────────────────────────────────────────────────────────────────────────────
# phone-input.js
# ─────────────────────────────────────────────────────────────────────────────
PHONE_STATE = """
(() => {
  const w = document.querySelector('[data-phone-input]');
  return { shown: w.querySelector('[data-phone-number-input]').value,
           full: w.querySelector('[data-phone-full-value]').value,
           code: w.querySelector('[data-phone-country-code]').value,
           display: w.querySelector('[data-phone-country-display]').textContent.trim() };
})()
"""


def phone_page(browser, **ctx):
    context = browser.new_context(locale="en-US")
    page = context.new_page()
    serve(context, {"/": doc(phone_html(**ctx), "phone-input")})
    page.goto(ORIGIN + "/")
    page.wait_for_function("window.PhoneInput && document.querySelector('[data-phone-input]')._phoneInput")
    return page


def prop_phone_input_format(browser):
    page = phone_page(browser)
    # Every length 0-14 x ten digit patterns (all start digits, so leading zeros occur), typed as one paste.
    rows = page.evaluate(
        """
(() => {
  const out = [];
  const w = document.querySelector('[data-phone-input]');
  const input = w.querySelector('[data-phone-number-input]');
  const full = w.querySelector('[data-phone-full-value]');
  for (let len = 0; len <= 14; len++) {
    for (let k = 0; k < 10; k++) {
      let d = '';
      for (let i = 0; i < len; i++) d += String((i * 7 + k) % 10);
      input.value = d;
      input.setSelectionRange(d.length, d.length);
      input.dispatchEvent(new Event('input', { bubbles: true }));
      out.push({ len, typed: d, shown: input.value, full: full.value });
    }
  }
  return out;
})()
"""
    )
    lost, spacing, full_mismatch = [], [], []
    for r in rows:
        if digits(r["shown"]) != r["typed"]:
            lost.append(f"{len(r['typed'])} digits typed {r['typed']!r} -> shown {r['shown']!r} (kept {len(digits(r['shown']))})")
        if r["shown"] != r["shown"].strip() or "  " in r["shown"]:
            spacing.append(f"{len(r['typed'])} digits typed {r['typed']!r} -> shown {r['shown']!r}")
        if r["full"] != (("+966" + digits(r["shown"])) if digits(r["shown"]) else ""):
            full_mismatch.append(f"{r['shown']!r} -> full {r['full']!r}")
    by_len_lost = sorted({len(r['typed']) for r in rows if digits(r['shown']) != r['typed']})
    by_len_space = sorted({len(r['typed']) for r in rows if r['shown'] != r['shown'].strip() or '  ' in r['shown']})
    # Idempotence: formatting an already-formatted value changes nothing.
    idem = page.evaluate(
        """
(() => {
  const input = document.querySelector('[data-phone-number-input]');
  const bad = [];
  for (let len = 1; len <= 14; len++) {
    let d = ''; for (let i = 0; i < len; i++) d += String((i * 3 + 1) % 10);
    input.value = d; input.dispatchEvent(new Event('input', { bubbles: true }));
    const once = input.value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    if (input.value !== once) bad.push(`${len}: ${once} -> ${input.value}`);
  }
  return bad;
})()
"""
    )
    # Caret: insert one digit at every position of every formatted value (lengths 1-13): the caret stays
    # right after the digit just typed.
    caret_bad = page.evaluate(
        """
(() => {
  const input = document.querySelector('[data-phone-number-input]');
  const bad = [];
  const dig = (s) => s.replace(/\\D/g, '').length;
  for (let len = 1; len <= 13; len++) {
    let d = ''; for (let i = 0; i < len; i++) d += String((i * 3 + 1) % 10);
    input.value = d; input.dispatchEvent(new Event('input', { bubbles: true }));
    const base = input.value;
    for (let p = 0; p <= base.length; p++) {
      input.value = base.slice(0, p) + '5' + base.slice(p);
      input.setSelectionRange(p + 1, p + 1);
      const expectBefore = dig(base.slice(0, p)) + 1;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      const got = dig(input.value.slice(0, input.selectionStart));
      if (got !== expectBefore) bad.push(`len ${len} caret ${p}: ${base} -> ${input.value} caret ${input.selectionStart} (digits before ${got}, want ${expectBefore})`);
    }
  }
  return bad;
})()
"""
    )
    page.context.close()
    report("phone-digits", lost, f"cases={len(rows)}")
    report_finding("phone-spacing", spacing, "no-stray-space" if not spacing else f"stray-space-at-length={','.join(map(str, by_len_space))}")
    report("phone-full-value", full_mismatch, f"cases={len(rows)}")
    report("phone-idempotent", idem, "lengths=1..14")
    report("phone-caret", caret_bad, f"cases={sum(l + 1 for l in range(1, 14))}")
    return lost, spacing


def prop_phone_numerals(browser):
    page = phone_page(browser)
    cases = {
        "arabic-indic": "٠١٢٣٤٥٦٧٨٩",
        "extended-arabic-indic": "۰۱۲۳۴۵۶۷۸۹",
        "fullwidth": "０１２３４５６７８９",
    }
    bad = []
    for name, text in cases.items():
        page.evaluate(
            "(t) => { const i = document.querySelector('[data-phone-number-input]'); i.value = t; i.dispatchEvent(new Event('input', { bubbles: true })); }",
            text,
        )
        s = page.evaluate(PHONE_STATE)
        if len(digits(s["shown"])) != 0 and False:
            pass
        kept = len(re.sub(r"\D", "", s["shown"]))
        if kept != 10:
            bad.append(f"{name}: typed 10 numerals {text!r} -> shown {s['shown']!r}, full value {s['full']!r}")
    page.context.close()
    return report_finding("phone-numerals", bad, "dropped=" + ",".join(b.split(":")[0] for b in bad) if bad else "all-scripts-kept")


def prop_phone_filter_select(browser):
    page = phone_page(browser, all_countries=True)
    rows = page.evaluate(
        """
(() => {
  const w = document.querySelector('[data-phone-input]');
  const search = w.querySelector('[data-phone-country-search]');
  const none = w.querySelector('[data-phone-no-results]');
  const popover = document.getElementById(w.querySelector('[data-slot=country-trigger]').getAttribute('popovertarget'));
  const opts = () => Array.from(w.querySelectorAll('.phone-country-option'));
  popover.showPopover();
  const visible = () => opts().filter((o) => !o.hidden);
  const out = { total: opts().length, misses: [], noResultMismatch: [], spaced: [] };
  const ask = (q) => { search.value = q; search.dispatchEvent(new Event('input', { bubbles: true })); return visible(); };
  for (const o of opts()) {
    const d = o.dataset;
    const queries = [d.countryName, d.countryName.toUpperCase(), '  ' + d.countryName.slice(0, 4) + '  ', d.dialCode, d.countryCode, d.countryCode.toLowerCase()];
    if (d.countryNameAr) queries.push(d.countryNameAr, d.countryNameAr.slice(0, 3));
    for (const q of queries) {
      if (!q.trim()) continue;
      const v = ask(q);
      if (!v.includes(o)) out.misses.push(`${d.countryCode} not found by ${JSON.stringify(q)}`);
      if ((v.length === 0) !== !none.hidden) out.noResultMismatch.push(JSON.stringify(q));
    }
  }
  const v = ask('zzzzqqqq');
  if (v.length !== 0 || none.hidden) out.noResultMismatch.push('nonsense query');
  const all = ask('');
  if (all.length !== opts().length || !none.hidden) out.noResultMismatch.push('cleared query');
  return out;
})()
"""
    )
    filter_bad = rows["misses"] + [f"no-results message wrong for {q}" for q in rows["noResultMismatch"]]
    report("phone-filter", filter_bad, f"countries={rows['total']}")

    # Selection: choose every option by click; display, hidden code, full value, aria-selected and both events agree.
    sel = page.evaluate(
        """
(async () => {
  const w = document.querySelector('[data-phone-input]');
  const input = w.querySelector('[data-phone-number-input]');
  input.value = '512345678'; input.dispatchEvent(new Event('input', { bubbles: true }));
  const events = [];
  w.addEventListener('phone:country-change', (e) => events.push(e.detail));
  const popover = document.getElementById(w.querySelector('[data-slot=country-trigger]').getAttribute('popovertarget'));
  const bad = []; const collisions = {};
  const options = Array.from(w.querySelectorAll('.phone-country-option'));
  for (const o of options) {
    popover.showPopover();
    o.click();
    const d = o.dataset;
    const selected = options.filter((x) => x.getAttribute('aria-selected') === 'true');
    const dials = new Set(selected.map((x) => x.dataset.dialCode));
    const full = w.querySelector('[data-phone-full-value]').value;
    if (w.querySelector('[data-phone-country-code]').value !== d.dialCode) bad.push(d.countryCode + ': hidden code');
    if (w.querySelector('[data-phone-country-display]').textContent.trim() !== d.dialCode) bad.push(d.countryCode + ': display');
    if (full !== d.dialCode + '512345678') bad.push(d.countryCode + ': full value ' + full);
    if (dials.size !== 1 || !dials.has(d.dialCode)) bad.push(d.countryCode + ': aria-selected dials ' + Array.from(dials));
    if (selected.length !== 1) collisions[d.dialCode] = selected.map((x) => x.dataset.countryCode);
    if (popover.matches(':popover-open')) bad.push(d.countryCode + ': popover still open');
    if (document.activeElement !== input) bad.push(d.countryCode + ': focus not on the number input');
  }
  const last = events[events.length - 1];
  if (events.length !== options.length) bad.push('country-change events ' + events.length + ' for ' + options.length + ' clicks');
  const wrong = events.filter((e, i) => e.countryCode !== options[i].dataset.countryCode || e.dialCode !== options[i].dataset.dialCode);
  if (wrong.length) bad.push(wrong.length + ' events carry the wrong country');
  return { bad, collisions, n: options.length };
})()
"""
    )
    report("phone-select", sel["bad"], f"countries={sel['n']}")
    collisions = [f"+{k.lstrip('+')}: choosing one of {v} marks all of {v} as selected" for k, v in sel["collisions"].items()]
    report_finding("phone-dial-collision", collisions, "shared-dial-codes=" + ",".join(sorted(sel["collisions"])) if collisions else "none")

    # validate()/isValid() at wrapper level vs the table, every country x length 0-20.
    val = page.evaluate(
        """
(() => {
  const w = document.querySelector('[data-phone-input]');
  const h = w._phoneInput; const bad = []; let n = 0;
  const seen = new Set();
  for (const c of window.CountriesData) {
    if (seen.has(c.dialCode)) continue; seen.add(c.dialCode);
    h.setDialCode(c.dialCode);
    for (let len = 0; len <= 20; len++) {
      let d = ''; for (let i = 0; i < len; i++) d += String((i + 2) % 10);
      h.reset();
      w.querySelector('[data-phone-number-input]').value = d;      // bypass formatting
      const verdict = h.validate(); const ok = h.isValid(); n++;
      const expect = len === 0 ? 'EMPTY' : window.CountriesData.validatePhoneLength(d, c.dialCode);
      if (verdict !== expect) bad.push(`${c.dialCode} len ${len}: validate ${verdict} != ${expect}`);
      if (ok !== (verdict === undefined)) bad.push(`${c.dialCode} len ${len}: isValid ${ok} vs validate ${verdict}`);
    }
  }
  return { bad, n };
})()
"""
    )
    report("phone-validate", val["bad"], f"cases={val['n']}")
    page.context.close()


def prop_phone_escape(browser):
    """Escape in the country search, inside a modal <dialog> (as notify-me-dialog renders it)."""
    body = f"<dialog id='dlg'>{phone_html()}</dialog><button id='opener'>open</button>"
    context = browser.new_context(locale="en-US")
    page = context.new_page()
    serve(context, {"/": doc(body, "phone-input")})
    page.goto(ORIGIN + "/")
    page.wait_for_function("document.querySelector('[data-phone-input]')._phoneInput")
    page.evaluate("document.getElementById('dlg').showModal()")
    page.click("[data-slot='country-trigger']")
    page.wait_for_function("document.querySelector('[data-phone-country-search]') === document.activeElement")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    after = page.evaluate(
        """({ dialogOpen: document.getElementById('dlg').open,
              popoverOpen: document.querySelector('[data-phone-input] [popover]').matches(':popover-open'),
              focus: document.activeElement.getAttribute('data-slot') || document.activeElement.tagName })"""
    )
    context.close()
    bad = []
    if after["popoverOpen"]:
        bad.append("popover still open after Escape")
    if not after["dialogOpen"]:
        bad.append("one Escape also closed the surrounding modal dialog (the shopper loses the form)")
    if after["focus"] != "country-trigger":
        bad.append(f"focus is on {after['focus']!r}, not the country trigger")
    return report_finding("phone-escape", bad, "escape-keeps-dialog-and-focuses-trigger" if not bad else f"dialog-open={after['dialogOpen']},focus={after['focus']}")


# ─────────────────────────────────────────────────────────────────────────────
# wishlist.js
# ─────────────────────────────────────────────────────────────────────────────
INIT_SCRIPT = """
window.__calls = [];
window.__pending = [];
window.__list = { results: [{ id: 'A' }] };
window.__wishlistsImpl = async () => window.__list;
window.zid = { account: {
  wishlists: () => window.__wishlistsImpl(),
  addToWishlists: (b) => { __calls.push(['add', b.product_ids[0]]); return new Promise((res, rej) => __pending.push({ res, rej, kind: 'add', id: b.product_ids[0] })); },
  removeFromWishlist: (id) => { __calls.push(['remove', id]); return new Promise((res, rej) => __pending.push({ res, rej, kind: 'remove', id })); },
} };
"""

BUTTON = (
    '<button type="button" data-wishlist-btn data-product-id="{pid}" aria-label="{label}">'
    '<svg><path d="x"/></svg></button>'
)


def wishlist_page(browser, buttons, lang="en", label="Add to wishlist", init=INIT_SCRIPT):
    context = browser.new_context(locale="en-US")
    page = context.new_page()
    body = "".join(BUTTON.format(pid=pid, label=label) for pid in buttons)
    serve(context, {"/products": doc(body, "wishlist", lang=lang, init_script=init)})
    page.goto(ORIGIN + "/products?x=1#h")
    page.wait_for_function("window.wishlistManager && window.wishlistManager.isInitialized")
    return page


def prop_wishlist_states(browser):
    page = wishlist_page(browser, ["A", "B"])
    result = page.evaluate(
        """
(async () => {
  const m = window.wishlistManager;
  const tick = () => new Promise((r) => setTimeout(r, 0));
  const kindOf = (b) => b.innerHTML.includes('C22B51') ? 'filled' : b.innerHTML.includes('animate-spin') ? 'loading' : 'empty';
  const OPS = ['clickA', 'clickB', 'ok', 'fail'];
  const bad = []; let runs = 0;
  const btn = (id) => document.querySelector(`[data-wishlist-btn][data-product-id="${id}"]`);

  function check(trail, label) {
    for (const id of ['A', 'B']) {
      const b = btn(id); const kind = kindOf(b);
      const pend = __pending.filter((p) => p.id === id).length;
      const want = { empty: ['Add to wishlist', false], filled: ['Remove from wishlist', false], loading: ['Loading', true] }[kind];
      if (b.getAttribute('aria-label') !== want[0] || b.disabled !== want[1]) bad.push(`${trail}: ${id} label/disabled ${b.getAttribute('aria-label')}/${b.disabled} for ${kind}`);
      if (kind === 'loading' && pend === 0) bad.push(`${trail}: ${id} spinner with no call in flight`);
      if (kind !== 'loading' && pend > 0) bad.push(`${trail}: ${id} ${kind} while a call is in flight`);
      if (pend > 1) bad.push(`${trail}: ${id} has ${pend} overlapping writes`);
      if (kind !== 'loading' && (kind === 'filled') !== m.wishlistProductIds.has(id)) bad.push(`${trail}: ${id} shows ${kind} but set says ${m.wishlistProductIds.has(id)}`);
    }
  }

  async function run(seq) {
    m.isLoggedIn = true; m.wishlistProductIds = new Set(['A']); __calls.length = 0; __pending.length = 0;
    m.updateAllButtons();
    const trail = seq.join('>');
    for (const op of seq) {
      if (op === 'clickA' || op === 'clickB') {
        const b = btn(op === 'clickA' ? 'A' : 'B');
        const before = __calls.length; const wasLoading = kindOf(b) === 'loading';
        b.click(); await tick();
        const expectCall = wasLoading ? 0 : 1;
        if (__calls.length - before !== expectCall) bad.push(`${trail}: ${op} made ${__calls.length - before} SDK writes (want ${expectCall})`);
      } else if (op === 'ok' || op === 'fail') {
        const p = __pending.shift();
        if (p) { op === 'ok' ? p.res({ ok: true }) : p.rej(new Error('x')); await tick(); await tick();
          const should = op === 'ok' ? p.kind === 'add' : p.kind === 'remove';
          if (m.wishlistProductIds.has(p.id) !== should) bad.push(`${trail}: ${op} of ${p.kind} ${p.id} left set membership ${m.wishlistProductIds.has(p.id)}`);
        }
      } else { window.dispatchEvent(new Event('products-updated')); await tick(); }
      check(trail, op);
    }
    // settle everything: no spinner may survive
    while (__pending.length) { const p = __pending.shift(); p.res({}); await tick(); await tick(); }
    for (const id of ['A', 'B']) if (kindOf(btn(id)) === 'loading') bad.push(`${trail}: ${id} still loading after all calls settled`);
    runs++;
  }

  function* seqs(n, prefix = []) { if (prefix.length === n) { yield prefix; return; } for (const o of OPS) yield* seqs(n, [...prefix, o]); }
  for (let n = 1; n <= 4; n++) for (const s of seqs(n)) { await run(s); if (bad.length > 30) return { bad, runs }; }
  return { bad, runs };
})()
"""
    )
    page.context.close()
    return report("wishlist-states", result["bad"], f"sequences={result['runs']}")


def prop_wishlist_refresh_midflight(browser):
    """`products-updated` / `content:loaded` fire on every filter, pagination and quick-view render; the buttons
    of requests still in flight must keep their spinner."""
    page = wishlist_page(browser, ["B"])
    out = page.evaluate(
        """
(async () => {
  const m = window.wishlistManager; const tick = () => new Promise((r) => setTimeout(r, 0));
  const b = document.querySelector('[data-wishlist-btn]');
  m.isLoggedIn = true; m.wishlistProductIds = new Set(); m.updateAllButtons();
  b.click(); await tick();
  const loading = b.disabled;
  window.dispatchEvent(new Event('products-updated')); await tick();
  const afterUpdate = { disabled: b.disabled, label: b.getAttribute('aria-label') };
  b.click(); await tick();
  return { loading, afterUpdate, writes: __calls.length };
})()
"""
    )
    page.context.close()
    bad = []
    if out["afterUpdate"]["disabled"] is not True:
        bad.append(f"products-updated replaced the in-flight spinner with {out['afterUpdate']}")
    if out["writes"] != 1:
        bad.append(f"{out['writes']} SDK writes for one product after a re-render and a second click")
    return report_finding("wishlist-refresh-midflight", bad, "spinner-survives-rerender" if not bad else "rerender-reenables-button")


def prop_wishlist_duplicates(browser):
    """The same product can have two buttons (a card and the PDP, or quick view): both must show the same state."""
    page = wishlist_page(browser, ["B", "B"])
    out = page.evaluate(
        """
(async () => {
  const m = window.wishlistManager;
  const tick = () => new Promise((r) => setTimeout(r, 0));
  const kind = (b) => b.innerHTML.includes('C22B51') ? 'filled' : b.innerHTML.includes('animate-spin') ? 'loading' : 'empty';
  m.isLoggedIn = true; m.wishlistProductIds = new Set(); m.updateAllButtons();
  const [first, second] = document.querySelectorAll('[data-wishlist-btn]');
  second.click(); await tick();
  const during = [kind(first), kind(second), first.disabled, second.disabled];
  second.click(); await tick();                       // impatient second click on the button the shopper pressed
  const writesWhileLoading = __calls.length;
  __pending.shift().res({ ok: true }); await tick(); await tick();
  const after = [kind(first), kind(second)];
  return { during, after, writesWhileLoading };
})()
"""
    )
    page.context.close()
    bad = []
    if out["during"][1] != "loading":
        bad.append(f"clicked button shows {out['during'][1]} while its request is in flight (the spinner went to the other button: {out['during']})")
    if out["writesWhileLoading"] != 1:
        bad.append(f"{out['writesWhileLoading']} SDK writes after two clicks on the same product (second click not blocked)")
    if out["after"][0] != out["after"][1]:
        bad.append(f"after success the two buttons for one product disagree: {out['after']}")
    return report_finding("wishlist-duplicates", bad, "buttons-agree" if not bad else "duplicate-buttons-diverge")


def prop_wishlist_guest(browser):
    """Guest click: SDK untouched, redirect to /auth/login with the current pathname, never off-origin."""
    paths = ["/products", "/products/%D9%85%D9%86%D8%AA%D8%AC-1", "/a%20b", "/x?y=1", "/blogs/a&b=c", "/p/%22%3E", "/", "/%2F%2Fevil.test"]
    bad = []
    for path in paths:
        context = browser.new_context(locale="en-US")
        page = context.new_page()
        navs = []
        page.on("request", lambda r, navs=navs: navs.append(r.url) if r.is_navigation_request() and "/auth/login" in r.url else None)
        init = INIT_SCRIPT + "window.__wishlistsImpl = async () => { const e = new Error('401'); e.status = 401; throw e; };"
        pathonly = path.split("?")[0]
        serve(context, {pathonly: doc(BUTTON.format(pid="A", label="Add to wishlist"), "wishlist", init_script=init)})
        page.route(ORIGIN + "/auth/login*", lambda route: route.fulfill(status=200, content_type="text/html", body="login"))
        page.goto(ORIGIN + path)
        page.wait_for_function("window.wishlistManager && window.wishlistManager.isInitialized")
        state = page.evaluate("({ loggedIn: wishlistManager.isLoggedIn, calls: __calls.length })")
        page.click("[data-wishlist-btn] svg")
        page.wait_for_timeout(400)
        if len(navs) != 1:
            bad.append(f"{path}: {len(navs)} login navigations")
            context.close()
            continue
        from urllib.parse import parse_qs, urlparse

        u = urlparse(navs[0])
        expected_pathname = urlparse(ORIGIN + path).path
        if f"{u.scheme}://{u.netloc}" != ORIGIN or u.path != "/auth/login":
            bad.append(f"{path}: left the origin or the login path: {navs[0]}")
        if parse_qs(u.query).get("redirect_to") != [expected_pathname]:
            bad.append(f"{path}: redirect_to={parse_qs(u.query).get('redirect_to')} (pathname is {expected_pathname!r})")
        if state["loggedIn"] is not False or state["calls"] != 0:
            bad.append(f"{path}: guest state {state}")
        context.close()
    return report("wishlist-guest-redirect", bad, f"paths={len(paths)}")


def prop_wishlist_sync(browser):
    shapes = {
        "results-objects": ({"results": [{"id": "A"}, {"id": "C"}]}, True, {"A", "C"}),
        "array-of-ids": (["A", "C"], True, {"A", "C"}),
        "empty-results": ({"results": []}, True, set()),
        "null-response": (None, True, set()),
        "unknown-shape": ({"count": 2}, True, set()),
    }
    bad = []
    for name, (payload, logged, expect) in shapes.items():
        init = INIT_SCRIPT + f"window.__wishlistsImpl = async () => ({json.dumps(payload)});"
        page = wishlist_page(browser, ["A", "B", "C"], init=init)
        got = page.evaluate(
            "({ logged: wishlistManager.isLoggedIn, ids: Array.from(wishlistManager.wishlistProductIds).sort(),"
            " kinds: Array.from(document.querySelectorAll('[data-wishlist-btn]')).map((b) => b.innerHTML.includes('C22B51') ? 'filled' : 'empty') })"
        )
        want_kinds = ["filled" if i in expect else "empty" for i in ("A", "B", "C")]
        if got["logged"] is not logged or set(got["ids"]) != expect or got["kinds"] != want_kinds:
            bad.append(f"{name}: {got} (want ids {sorted(expect)}, kinds {want_kinds})")
        page.context.close()
    # errors: 401 and 403 -> guest; a 500 must not turn the shopper into a logged-in one
    for status, logged in ((401, False), (403, False), (500, False), (None, False)):
        err = "{status: %s}" % status if status else "{}"
        init = INIT_SCRIPT + f"window.__wishlistsImpl = async () => {{ throw Object.assign(new Error('x'), {err}); }};"
        page = wishlist_page(browser, ["A"], init=init)
        got = page.evaluate("({ logged: wishlistManager.isLoggedIn, label: document.querySelector('[data-wishlist-btn]').getAttribute('aria-label'), disabled: document.querySelector('[data-wishlist-btn]').disabled })")
        if got["logged"] is not logged or got["disabled"]:
            bad.append(f"error status {status}: {got}")
        page.context.close()
    return report("wishlist-sync", bad, f"shapes={len(shapes)},errors=4")


def prop_wishlist_sdk_wait(browser):
    """waitForZidSDK: finds the SDK whenever it shows up within 20 attempts, gives up (guest) after that, and
    refresh() recovers."""
    bad = []
    results = {}
    for appears_at in (0, 1, 5, 19, 20, 25):
        # Collapse the backoff timers (count attempts instead of waiting ~30 s) and publish the SDK stub
        # only once the n-th wait has been requested.
        init = INIT_SCRIPT.replace("window.zid = {", "window.__realZid = {") + f"""
        window.__attempts = 0; window.__delays = [];
        const nativeTimeout = window.setTimeout;
        window.setTimeout = (fn, ms, ...a) => {{ window.__delays.push(ms); window.__attempts++;
          if (window.__attempts === {appears_at}) window.zid = window.__realZid; return nativeTimeout(fn, 0, ...a); }};
        if ({appears_at} === 0) window.zid = window.__realZid;
        """
        context = browser.new_context(locale="en-US")
        page = context.new_page()
        serve(context, {"/products": doc(BUTTON.format(pid="A", label="Add to wishlist"), "wishlist", init_script=init)})
        page.goto(ORIGIN + "/products")
        page.wait_for_function("window.wishlistManager && window.wishlistManager.isInitialized", timeout=20000)
        got = page.evaluate("({ ready: wishlistManager.isZidReady, logged: wishlistManager.isLoggedIn, attempts: window.__attempts, maxDelay: Math.max(0, ...window.__delays) })")
        results[appears_at] = got
        expect_ready = appears_at < 20
        if got["ready"] is not expect_ready:
            bad.append(f"SDK appears after {appears_at} waits: ready={got['ready']} (want {expect_ready})")
        if expect_ready and got["logged"] is not True:
            bad.append(f"SDK appears after {appears_at} waits but the shopper is not synced")
        if got["maxDelay"] > 2000:
            bad.append(f"backoff exceeded the 2000 ms cap: {got['maxDelay']}")
        if not expect_ready:
            page.evaluate("window.zid = window.__realZid")
            page.evaluate("wishlistManager.refresh()")
            page.wait_for_function("wishlistManager.isLoggedIn === true", timeout=5000)
        context.close()
    return report("wishlist-sdk-wait", bad, "appear-at=0,1,5,19,20,25")


def prop_wishlist_label_language(browser):
    """The server renders a translated aria-label; after the module runs it must not flip to English."""
    page = wishlist_page(browser, ["A", "B"], lang="ar", label="أضف إلى المفضلة")
    labels = page.evaluate("Array.from(document.querySelectorAll('[data-wishlist-btn]')).map((b) => b.getAttribute('aria-label'))")
    page.context.close()
    bad = []
    if any(l != "أضف إلى المفضلة" for l in labels):
        bad.append(f"server-rendered Arabic aria-label became {labels} once wishlist.js ran (window.wishlistConfig is never defined by any template)")
    return report_finding("wishlist-label-language", bad, "label-kept" if not bad else "labels-overwritten-with-english")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        try:
            prop_phone_input_format(browser)
            prop_phone_numerals(browser)
            prop_phone_filter_select(browser)
            prop_phone_escape(browser)
            prop_wishlist_states(browser)
            prop_wishlist_refresh_midflight(browser)
            prop_wishlist_duplicates(browser)
            prop_wishlist_guest(browser)
            prop_wishlist_sync(browser)
            prop_wishlist_sdk_wait(browser)
            prop_wishlist_label_language(browser)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
