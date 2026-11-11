#!/usr/bin/env python3
"""Browser properties for assets/js/shipping-payment.js: load the REAL, unmodified file into
a page rendered from the real templates and check the cities dialog and copy buttons.

Usage: uv run --no-project --with playwright --with jinja2 python -I dom_props.py [--root DIR] [--out DIR]
  exit 0 = every property matched its recorded outcome; exit 1 = one changed (CHANGED <property>)
  exit 2 = the browser or fixture could not run

No server: the page is rendered by plain Jinja2 (render_props.make_env) to a file under --out
and opened as file://. `navigator.clipboard` is replaced by a recorder and the page clock is
faked so the 2 s copy-feedback timer is deterministic. Seed is fixed and printed.
"""

import argparse
import sys

sys.dont_write_bytecode = True  # python -I ignores PYTHONDONTWRITEBYTECODE; keep the skill dir clean
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_props as rp  # noqa: E402  (same harness dir)

from playwright.sync_api import sync_playwright  # noqa: E402

SEED = 20261111
CHROME = os.environ.get(
    "CHROME",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" if sys.platform == "darwin" else "/usr/bin/google-chrome",
)

EXPECTED = {
    "CitiesDialogRenders": "holds",
    "CitiesDialogLifecycle": "holds",
    "CityTextEscaping": "holds",
    "CopyButtonCopies": "holds",
    "CountryTextEscaping": "violation",
    "CopyFeedbackRestores": "violation",
}

RECORDER = """
  window.__copied = [];
  Object.defineProperty(navigator, 'clipboard', {value: {writeText: (v) => { window.__copied.push(v); return Promise.resolve(); }}, configurable: true});
"""

COUNTRIES = ["Saudi Arabia", "UAE", "Kuwait", None]


def build_page(env, root, out, methods, banks=(), name="page"):
    html = rp.render(env, "templates/shipping_payment.jinja", **rp.page_ctx(methods, [rp.pay_method(1)], list(banks)))
    # the stub asset_url yields /assets/js/x.js; point it at the real file on disk
    html = html.replace("/assets/js/shipping-payment.js?v=t", (Path(root) / "assets/js/shipping-payment.js").as_uri())
    path = Path(out) / f"{name}.html"
    path.write_text("<!doctype html><meta charset=utf-8>" + html, encoding="utf-8")
    return path.as_uri()


def cities(rnd, n, mode):
    names = [f"Cit{rnd.randrange(10**4)}{rnd.choice('abcXYZ(') }{k}" for k in range(n)]
    out = []
    for k, nm in enumerate(names):
        c = {"name": nm}
        country = COUNTRIES[k % 3] if mode != "none" else None
        if mode == "nested" and country:
            c["country"] = {"name": country}
        elif mode == "flat" and country:
            c["country_name"] = country
        elif mode == "mixed" and country and k % 2:
            c["country"] = {"name": country}
        out.append(c)
    return out


def expected_view(cs, term):
    """Independent oracle: group by country (first-seen order), keep cities matching name or country."""
    groups = {}
    for c in cs:
        country = (c.get("country") or {}).get("name") or c.get("country_name") or "Other"
        groups.setdefault(country, []).append(c["name"])
    t = term.lower()
    view = []
    for country, names in groups.items():
        keep = [n for n in names if t in n.lower() or t in country.lower()]
        if keep:
            view.append((country, keep))
    return view


def read_view(page):
    return page.evaluate(
        """() => [...document.querySelectorAll('#cities-dialog [data-country-section]')].map(s => ({
            country: (s.querySelector('.font-semibold') || {}).textContent,
            count: (s.querySelector('.text-xs') || {}).textContent,
            accordion: !!s.querySelector('[data-country-trigger]'),
            tags: [...s.querySelectorAll('.badge')].map(b => b.textContent)}))"""
    )


def open_method(page, mid):
    page.evaluate(f"() => document.querySelector(\"[data-cities-trigger][data-method-id='{mid}']\").click()")


def is_open(page):
    return page.evaluate("() => document.getElementById('cities-dialog').open")


def prop_renders(browser, env, root, out, rnd):
    failures, cases = [], 0
    page = browser.new_page()
    for case in range(14):
        mode = ["none", "nested", "flat", "mixed"][case % 4]
        n = rnd.choice([4, 5, 9, 25])
        cs = cities(rnd, n, mode)
        url = build_page(env, root, out, [{**rp.method(1, 5), "delivery_option_cities": cs}], name=f"render-{case}")
        page.goto(url)
        open_method(page, 1)
        terms = ["", cs[0]["name"][2:6], cs[1]["name"].upper(), cs[2]["name"].lower(), "(", "[a-", "\\", "uae", "SAUDI", "zzz-no-match"]
        for term in terms:
            page.fill("[data-cities-search]", term)
            want = expected_view(cs, term)
            got = read_view(page)
            cases += 1
            label = f"[{mode} n={n} term={term!r}]"
            empty_shown = page.evaluate("() => !document.querySelector('[data-cities-empty]').classList.contains('hidden')")
            if empty_shown != (not want):
                failures.append(f"{label} empty state shown={empty_shown} but expected view has {len(want)} groups")
            if [(g["country"], g["tags"]) for g in got] != want:
                failures.append(f"{label} rendered {[(g['country'], len(g['tags'])) for g in got]} expected {[(c, len(t)) for c, t in want]}")
            if any(g["count"] != f"({len(g['tags'])} cities)" for g in got):
                failures.append(f"{label} header count text disagrees with tag count")
            if any(g["accordion"] != (len(want) > 1) for g in got):
                failures.append(f"{label} accordion layout iff more than one country")
    page.close()
    return failures, cases


def prop_lifecycle(browser, env, root, out, rnd):
    failures = []
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    m1 = {**rp.method(1, 6, name="First method"), "delivery_option_cities": cities(rnd, 6, "nested")}
    m2 = {**rp.method(2, 5, name="Second method"), "delivery_option_cities": cities(rnd, 5, "none")}
    page.goto(build_page(env, root, out, [m1, m2], name="lifecycle"))
    open_method(page, 1)
    if not is_open(page):
        failures.append("trigger did not open the dialog")
    if page.inner_text("[data-cities-dialog-title]").strip() != "First method":
        failures.append("title != method name")
    page.fill("[data-cities-search]", "zzz")
    page.evaluate("() => document.querySelector(\"#cities-dialog button[command='close']\").click()")
    if is_open(page):
        failures.append("close button left the dialog open")
    open_method(page, 2)
    if page.input_value("[data-cities-search]") != "":
        failures.append("search text survived reopening")
    if page.inner_text("[data-cities-dialog-title]").strip() != "Second method":
        failures.append("title stale after switching method")
    tags = [t for g in read_view(page) for t in g["tags"]]
    if sorted(tags) != sorted(c["name"] for c in m2["delivery_option_cities"]):
        failures.append("list kept cities of the previous method")
    page.evaluate("() => document.querySelector(\"#cities-dialog button[command='close']\").click()")
    # a trigger whose id is not in the data must be inert, not throw
    page.evaluate(
        """() => { const el = document.querySelector('[data-cities-trigger]'); el.dataset.methodId = '999'; el.click(); }"""
    )
    if is_open(page):
        failures.append("unknown method id opened the dialog")
    if errors:
        failures.append(f"page errors: {errors[:2]}")
    # accordion: collapse / expand a country (needs more than one)
    page.evaluate("() => { document.querySelector('[data-cities-trigger]').dataset.methodId = '1'; document.querySelector('[data-cities-trigger]').click(); }")
    if page.locator("[data-country-trigger]").count() >= 2:
        page.locator("[data-country-trigger]").first.click()
        c0 = page.evaluate("() => [document.querySelector('[data-country-content]').classList.contains('hidden'), document.querySelector('[data-country-icon]').classList.contains('rotate-180')]")
        if c0 != [True, False]:
            failures.append(f"collapse state wrong: {c0}")
        page.locator("[data-country-trigger]").first.click()
        c1 = page.evaluate("() => [document.querySelector('[data-country-content]').classList.contains('hidden'), document.querySelector('[data-country-icon]').classList.contains('rotate-180')]")
        if c1 != [False, True]:
            failures.append(f"expand state wrong: {c1}")
    else:
        failures.append("fixture did not produce a multi-country dialog")
    page.close()
    return failures


def poisoned_view(browser, env, root, out, field, name):
    page = browser.new_page()
    page.add_init_script("window.__sink = 0;")
    pay = f'<img id="SINK-{field}" src="x:" onerror="window.__sink=1">'
    if field == "country":
        c = [{"name": "A", "country": {"name": pay}}, {"name": "B", "country": {"name": "Other country"}}, {"name": "C"}, {"name": "D"}, {"name": "E"}]
    else:
        c = [{"name": pay, "country": {"name": "KSA"}}, {"name": "B"}, {"name": "C"}, {"name": "D"}, {"name": "E"}]
    page.goto(build_page(env, root, out, [{**rp.method(1, 5), "delivery_option_cities": c}], name=name))
    open_method(page, 1)
    page.wait_for_timeout(300)
    injected = page.locator(f"#cities-dialog #SINK-{field}").count()  # the dialog only: the page preview is the template's
    ran = page.evaluate("() => window.__sink")
    page.close()
    return injected, ran


def prop_country_escaping(browser, env, root, out, rnd):
    injected, ran = poisoned_view(browser, env, root, out, "country", "xss-country")
    return [f"country name became markup (element injected={injected}, onerror ran={ran})"] if injected else []


def prop_city_escaping(browser, env, root, out, rnd):
    injected, ran = poisoned_view(browser, env, root, out, "city", "xss-city")
    # `ran` is not used here: the page's own preview text (template, autoescape off) also fires the handler
    return [f"city name became markup in the dialog (element injected={injected})"] if injected else []


def copy_page(browser, env, root, out, name):
    page = browser.new_page()
    page.clock.install(time=0)
    page.add_init_script(RECORDER)
    page.goto(build_page(env, root, out, [rp.method(1, 2)], banks=[rp.bank(1), rp.bank(2)], name=name))
    page.wait_for_timeout(100)
    return page


def prop_copy(browser, env, root, out, rnd):
    failures = []
    page = copy_page(browser, env, root, out, "copy")
    btns = page.locator("[data-copy-btn]")
    n = btns.count()
    if n != 4:
        failures.append(f"fixture has {n} copy buttons, wanted 4")
    for i in range(n):
        value = btns.nth(i).get_attribute("data-copy-value")
        before = btns.nth(i).inner_html()
        btns.nth(i).evaluate("e => e.click()")
        page.clock.run_for(50)
        copied = page.evaluate("() => window.__copied.slice()")
        if copied[-1:] != [value]:
            failures.append(f"button {i}: copied {copied[-1:]} != {value!r}")
        if "text-success" not in btns.nth(i).inner_html():
            failures.append(f"button {i}: no success icon after copy")
        page.clock.run_for(2100)
        if btns.nth(i).inner_html() != before:
            failures.append(f"button {i}: icon not restored after 2 s")
    if page.evaluate("() => window.__copied.length") != n:
        failures.append("copy count != click count")
    page.close()
    return failures


def prop_copy_restores(browser, env, root, out, rnd):
    """Click twice inside the 2 s window, let every timer run: the icon must be the original."""
    page = copy_page(browser, env, root, out, "copy-twice")
    btn = page.locator("[data-copy-btn]").first
    before = btn.inner_html()
    btn.evaluate("e => e.click()")
    page.clock.run_for(500)
    btn.evaluate("e => e.click()")
    page.clock.run_for(5000)
    after = btn.inner_html()
    page.close()
    if after != before:
        return ["after two clicks within 2 s and all timers elapsed the button still shows "
                + ("the success check" if "text-success" in after else "a changed icon")]
    return []


PROPS = [
    ("CitiesDialogRenders", prop_renders, "assets/js/shipping-payment.js:renderCities (grouping, search filter, counts, empty state, layout)"),
    ("CitiesDialogLifecycle", prop_lifecycle, "assets/js/shipping-payment.js:openCitiesDialog, initCitiesDialog, country accordion"),
    ("CityTextEscaping", prop_city_escaping, "assets/js/shipping-payment.js:renderCities (city tags use textContent)"),
    ("CopyButtonCopies", prop_copy, "assets/js/shipping-payment.js:initCopyButtons"),
    ("CountryTextEscaping", prop_country_escaping, "assets/js/shipping-payment.js:renderCities (country name in innerHTML)"),
    ("CopyFeedbackRestores", prop_copy_restores, "assets/js/shipping-payment.js:initCopyButtons (originalSvg captured per click)"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(rp.DEFAULT_ROOT))
    ap.add_argument("--out", default=str(Path.home() / ".cache" / "formal-content-pages" / "dom"))
    args = ap.parse_args()
    root, out = Path(args.root), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not (root / "assets/js/shipping-payment.js").exists():
        print(f"no assets/js/shipping-payment.js under {root}", file=sys.stderr)
        return 2
    env = rp.make_env(root)
    print(f"seed {SEED}")
    bad = 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME, headless=True)
            for name, fn, where in PROPS:
                rnd = random.Random(f"{SEED}-{name}")
                try:
                    res = fn(browser, env, root, out, rnd)
                except Exception as exc:  # noqa: BLE001  a property that cannot run its steps has failed
                    res = [f"property could not complete its steps: {str(exc).splitlines()[0][:160]}"]
                failures, extra = (res if isinstance(res, tuple) else (res, None))
                got = "violation" if failures else "holds"
                note = f", {extra} cases" if extra else ""
                if got != EXPECTED[name]:
                    bad += 1
                    print(f"CHANGED  {name}: recorded {EXPECTED[name]}, now {got} ({where})")
                    for f in failures[:5]:
                        print(f"           {f}")
                    if got == "holds":
                        print("           if the code was fixed, update EXPECTED here and in SKILL.md and the finding.")
                else:
                    print(f"ok       {name}: {got} as recorded{note} ({where})")
                    if got == "violation":
                        print(f"FINDING: {name}: {failures[0]}")
            browser.close()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR    browser harness could not run: {exc!r}", file=sys.stderr)
        return 2
    print(f"javascript: {'every property matches its recorded outcome' if not bad else str(bad) + ' changed'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
