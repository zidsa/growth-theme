"""Formal properties for the layout group's DOM-bound JS: loading utils, the carousel and
main.js's carousel wiring, and the loyalty button.

    ROOT=<repo> uv run --no-project --with playwright python -I props/browser.py

Serves the real modules to a headless Chrome page through request interception (no server,
no build step) and prints `PROPERTY <id> <ok|finding> <signature>`.
"""

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(os.environ.get("ROOT", ".")).resolve()
CHROME = os.environ.get(
    "CHROME",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" if sys.platform == "darwin" else "/usr/bin/google-chrome",
)
ORIGIN = "http://layout.test"

PROPERTIES = []


def report(prop_id, violations, signature):
    status = "ok" if not violations else "finding"
    PROPERTIES.append((prop_id, status, signature))
    print(f"PROPERTY {prop_id} {status} {signature}", flush=True)
    for line in violations[:8]:
        print(f"    {line}", flush=True)


def serve(context, files):
    """files: path -> (content_type, body). Everything else under /assets or /nm comes from disk."""

    def handler(route):
        url = route.request.url
        if not url.startswith(ORIGIN):
            return route.abort()
        path = url[len(ORIGIN):].split("?")[0]
        if path in files:
            content_type, body = files[path]
            return route.fulfill(status=200, content_type=content_type, body=body)
        if path.startswith("/assets/"):
            target = ROOT / path[1:]
        elif path.startswith("/nm/"):
            target = ROOT / "node_modules" / path[4:]
        else:
            return route.fulfill(status=404, body="not found")
        if not target.is_file():
            return route.fulfill(status=404, body=f"missing {target}")
        return route.fulfill(status=200, content_type="text/javascript", body=target.read_text())

    context.route("**/*", handler)


IMPORT_MAP = {
    "imports": {
        "embla-carousel": "/nm/embla-carousel/esm/embla-carousel.esm.js",
        "embla-carousel-autoplay": "/nm/embla-carousel-autoplay/esm/embla-carousel-autoplay.esm.js",
        "embla-carousel-fade": "/nm/embla-carousel-fade/esm/embla-carousel-fade.esm.js",
        "embla-carousel-auto-scroll": "/nm/embla-carousel-auto-scroll/esm/embla-carousel-auto-scroll.esm.js",
    }
}

CAROUSEL_CSS = """
  .vp { width: 400px; overflow: hidden; }
  .track { display: flex; }
  .slide { flex: 0 0 300px; height: 60px; }
  .vp.wide { width: 2000px; }
"""


def carousel_markup(slides, extra=""):
    cells = "".join(f'<div class="embla__slide slide">{i}</div>' for i in range(slides))
    return f"""
      <div id="c" data-carousel {extra}>
        <div class="vp" data-carousel-viewport>
          <div class="track embla__container" data-carousel-container>{cells}</div>
        </div>
        <button type="button" data-carousel-prev>prev</button>
        <button type="button" data-carousel-next>next</button>
        <div data-carousel-dots></div>
        <div><div data-carousel-progress style="width:0%"></div></div>
      </div>"""


# ── escape.js: untrusted text in a double-quoted attribute cannot break out ──
def prop_escape(browser):
    page = browser.new_page()
    page.set_content("<div id='host'></div>")
    source = (ROOT / "assets/js/utils/escape.js").read_text().replace("export function", "function")
    page.add_script_tag(content=source)
    violations = page.evaluate(
        """() => {
            const out = [];
            const host = document.getElementById("host");
            const alphabet = ['"', "'", "<", ">", "&", "/", "=", "`", " ", "\\t", "\\n", "a", "Z", "0", "%", "#", "\\\\", "(", ")", "س", "é", "\\u2028"];
            const inputs = [""];
            for (const a of alphabet) {
              inputs.push(a);
              for (const b of alphabet) {
                inputs.push(a + b);
                for (const c of alphabet) inputs.push(a + b + c);
              }
            }
            const curated = [
              '"><img src=x onerror=alert(1)>',
              "'><script>alert(1)</script>",
              '&quot; onmouseover="alert(1)',
              "javascript:alert(1)",
              "\\"><svg/onload=alert(1)>",
              "data:text/html,<script>alert(1)</script>",
              "&#34;&#62;<b>x</b>",
              "\\u0000\\"><b>",
            ];
            inputs.push(...curated);
            // Seeded random strings (seed 20261111), same alphabet.
            let seed = 20261111;
            const rand = () => {
              seed = (seed * 1103515245 + 12345) & 0x7fffffff;
              return seed / 0x7fffffff;
            };
            for (let i = 0; i < 2000; i += 1) {
              const length = 1 + Math.floor(rand() * 8);
              let value = "";
              for (let j = 0; j < length; j += 1) value += alphabet[Math.floor(rand() * alphabet.length)];
              inputs.push(value);
            }

            for (const value of inputs) {
              host.innerHTML = `<span data-x="${escapeAttr(value)}">t</span>`;
              const spans = host.querySelectorAll("span");
              if (spans.length !== 1) {
                out.push(`${JSON.stringify(value)}: parsed ${spans.length} spans`);
                continue;
              }
              const span = spans[0];
              if (span.attributes.length !== 1) {
                out.push(`${JSON.stringify(value)}: ${span.attributes.length} attributes (${Array.from(span.attributes).map((a) => a.name)})`);
              }
              if (span.children.length !== 0) out.push(`${JSON.stringify(value)}: injected child elements`);
              // NUL and CR are normalised by the HTML parser before the attribute is set, so
              // fidelity is not assertable for them; structure (above) still is.
              const lossy = value.includes("\\u0000") || value.includes("\\r");
              if (!lossy && span.getAttribute("data-x") !== value) {
                out.push(`${JSON.stringify(value)}: round trip -> ${JSON.stringify(span.getAttribute("data-x"))}`);
              }
            }
            if (escapeAttr(null) !== "" || escapeAttr(undefined) !== "") out.push("null/undefined are not empty");
            if (escapeAttr(42) !== "42") out.push("numbers are not stringified");
            return out;
        }"""
    )
    page.close()
    cases = 1 + 22 + 22 * 22 + 22 * 22 * 22 + 8 + 2000
    report("escape-attr", violations, f"cases={cases}" if not violations else f"violations={len(violations)}")


# ── loading.js: show/hide must restore the label and never strand a disabled button ──
def prop_loading(browser):
    page = browser.new_page()
    page.set_content("<button id='b'>Save</button>")
    source = (ROOT / "assets/js/utils/loading.js").read_text().replace("export function", "function")
    page.add_script_tag(content=source)
    violations = page.evaluate(
        """() => {
            const out = [];
            const ops = (n) => Array.from({ length: n }, (_, i) => (i ? [] : [])).reduce((acc) => acc, []);
            // All sequences of show/hide up to length 5.
            const sequences = [];
            for (let length = 0; length <= 5; length += 1) {
              for (let mask = 0; mask < 1 << length; mask += 1) {
                sequences.push(Array.from({ length }, (_, i) => ((mask >> i) & 1 ? "show" : "hide")));
              }
            }
            for (const sequence of sequences) {
              const button = document.createElement("button");
              button.innerHTML = "Save changes";
              document.body.appendChild(button);
              for (const op of sequence) {
                if (op === "show") showSpinner(button);
                else hideSpinner(button);
              }
              const last = sequence[sequence.length - 1];
              const wantDisabled = last === "show";
              if (button.disabled !== wantDisabled) {
                out.push(`${sequence.join(">") || "none"}: disabled=${button.disabled}`);
              }
              if (wantDisabled) {
                if (!button.innerHTML.includes("animate-spin")) {
                  out.push(`${sequence.join(">")}: no spinner after show`);
                }
              } else if (button.innerHTML !== "Save changes") {
                out.push(`${sequence.join(">") || "none"}: label lost -> ${button.innerHTML.slice(0, 40)}`);
              }
              button.remove();
            }
            // Spinner text variant restores too.
            const button = document.createElement("button");
            button.innerHTML = "Pay";
            document.body.appendChild(button);
            showSpinner(button, { text: "Paying" });
            if (!button.innerHTML.includes("Paying")) out.push("showSpinner text option not rendered");
            hideSpinner(button);
            if (button.innerHTML !== "Pay") out.push(`text variant restored ${button.innerHTML}`);
            // Loading class toggle is symmetric.
            showLoading(button);
            if (!button.classList.contains("opacity-50")) out.push("showLoading missing class");
            hideLoading(button);
            if (button.classList.contains("opacity-50")) out.push("hideLoading kept class");
            // Null-safe.
            showSpinner(null);
            hideSpinner(undefined);
            showLoading(null);
            return out;
        }"""
    )
    page.close()
    report("loading", violations, "sequences=63" if not violations else f"violations={len(violations)}")


# ── carousel.js: index in range, dots in step, arrows at the bounds, progress in 0..1 ──
def prop_carousel(browser):
    context = browser.new_context()
    files = {
        "/harness.html": (
            "text/html",
            f"""<!doctype html><html dir="ltr"><head><style>{CAROUSEL_CSS}</style>
            <script type="importmap">{json.dumps(IMPORT_MAP)}</script></head>
            <body><div id="stage"></div>
            <script type="module">
              import {{ createCarousel, createConditionalCarousel }} from "/assets/js/lib/carousel.js";
              window.createCarousel = createCarousel;
              window.createConditionalCarousel = createConditionalCarousel;
              window.ready = true;
            </script></body></html>""",
        )
    }
    serve(context, files)
    page = context.new_page()
    page.goto(ORIGIN + "/harness.html")
    page.wait_for_function("() => window.ready === true", timeout=20000)

    violations = page.evaluate(
        """async () => {
            const tick = () => new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 30)));
            const out = [];
            const stage = document.getElementById("stage");
            const build = (slides, extra = "") => {
              stage.innerHTML = `
                <div id="c" data-carousel ${extra}>
                  <div class="vp" data-carousel-viewport><div class="track embla__container">` +
                    Array.from({ length: slides }, (_, i) => `<div class="embla__slide slide">${i}</div>`).join("") +
                  `</div></div>
                  <button type="button" data-carousel-prev>prev</button>
                  <button type="button" data-carousel-next>next</button>
                  <div data-carousel-dots></div>
                  <div><div data-carousel-progress style="width:0%"></div></div>
                </div>`;
              return document.getElementById("c");
            };
            const dots = () => Array.from(document.querySelectorAll("[data-carousel-dots] button"));
            const activeDot = () => dots().findIndex((d) => d.dataset.active === "true");
            const arrows = () => ({
              prev: document.querySelector("[data-carousel-prev]").disabled,
              next: document.querySelector("[data-carousel-next]").disabled,
            });
            const progress = () => parseFloat(document.querySelector("[data-carousel-progress]").style.width);

            // Fewer than two slides: no carousel (the caller may force one).
            for (const slides of [0, 1]) {
              const el = build(slides);
              const made = window.createCarousel(el, {});
              if (made !== null) out.push(`${slides} slides: createCarousel returned an instance`);
              const forced = window.createCarousel(build(slides), { forceInit: true });
              if (!forced) out.push(`${slides} slides forceInit: no instance`);
              await tick();
              if (made) made.destroy();
            }

            // Two slides in a 400px viewport give embla a single snap: assertions are bounds-only.
            {
              const api = window.createCarousel(build(2), {});
              await tick();
              for (let step = 0; step < 4; step += 1) {
                document.querySelector("[data-carousel-next]").click();
                await tick();
                const index = api.selectedIndex();
                if (index < 0 || index > 1) out.push(`2 slides: index ${index}`);
                const p = progress();
                if (!(p >= 0 && p <= 100)) out.push(`2 slides: progress ${p}`);
              }
              api.destroy();
            }

            for (const slides of [3, 5]) {
              for (const loop of [false, true]) {
                const el = build(slides);
                const api = window.createCarousel(el, { loop });
                if (!api) { out.push(`${slides} slides loop=${loop}: no instance`); continue; }
                await tick();
                if (dots().length !== slides) out.push(`${slides}/loop=${loop}: ${dots().length} dots`);
                const seen = [api.selectedIndex()];
                if (seen[0] !== 0) out.push(`${slides}/loop=${loop}: starts at ${seen[0]}`);
                for (let step = 0; step < slides * 3; step += 1) {
                  const before = api.selectedIndex();
                  document.querySelector("[data-carousel-next]").click();
                  await tick();
                  const after = api.selectedIndex();
                  if (after < 0 || after > slides - 1) out.push(`${slides}/loop=${loop}: index ${after}`);
                  if (loop) {
                    const wrapped = (before + 1) % slides;
                    if (after !== wrapped) out.push(`${slides}/loop=${loop}: ${before}->${after}, want ${wrapped}`);
                    if (arrows().next) out.push(`${slides}/loop=${loop}: next disabled while looping`);
                  } else {
                    const want = Math.min(before + 1, slides - 1);
                    if (after !== want) out.push(`${slides}/loop=${loop}: ${before}->${after}, want ${want}`);
                  }
                  if (activeDot() !== api.selectedIndex()) {
                    out.push(`${slides}/loop=${loop}: dot ${activeDot()} != index ${api.selectedIndex()}`);
                  }
                  if (dots().filter((d) => d.dataset.active === "true").length !== 1) {
                    out.push(`${slides}/loop=${loop}: ${dots().filter((d) => d.dataset.active === "true").length} active dots`);
                  }
                  const p = progress();
                  if (!(p >= 0 && p <= 100)) out.push(`${slides}/loop=${loop}: progress ${p}`);
                  seen.push(after);
                }
                if (!loop) {
                  if (api.selectedIndex() !== slides - 1) out.push(`${slides}: ended at ${api.selectedIndex()}`);
                  if (!arrows().next) out.push(`${slides}: next still enabled at the last slide`);
                  if (arrows().prev) out.push(`${slides}: prev disabled after moving`);
                  // embla animates the scroll; let it settle (up to 3 s) before reading the end value.
                  for (let i = 0; i < 100 && progress() < 99.5; i += 1) await tick();
                  if (progress() < 99.5) out.push(`${slides}: progress ${progress()} at the end`);
                  if (!seen.every((v, i) => i === 0 || v >= seen[i - 1])) out.push(`${slides}: index went backwards`);
                }
                api.destroy();
              }
            }

            // Scroll backwards never goes below zero and stops at the first slide.
            const el = build(4);
            const api = window.createCarousel(el, {});
            await tick();
            for (let i = 0; i < 6; i += 1) {
              document.querySelector("[data-carousel-prev]").click();
              await tick();
              if (api.selectedIndex() !== 0) out.push(`prev from start: index ${api.selectedIndex()}`);
              if (progress() !== 0) out.push(`prev from start: progress ${progress()}`);
            }

            // A carousel that fits: conditional init stays off; overflowing: it starts and shows controls.
            stage.innerHTML = `
              <div data-carousel data-carousel-conditional="true">
                <div class="vp wide" data-carousel-viewport><div class="track embla__container">
                  <div class="embla__slide slide">a</div><div class="embla__slide slide">b</div>
                </div></div>
              </div>
              <div id="controls" class="hidden">controls</div>`;
            const controls = document.getElementById("controls");
            const fits = document.querySelector("[data-carousel]");
            const fitCtl = window.createConditionalCarousel(fits, {}, controls);
            if (fitCtl.instance) out.push("conditional: initialized although the content fits");
            if (!controls.classList.contains("hidden")) out.push("conditional: controls shown while content fits");
            stage.querySelector(".vp").className = "vp";
            fitCtl.check();
            await tick();
            if (!fitCtl.instance) out.push("conditional: did not initialize once the content overflowed");
            if (controls.classList.contains("hidden")) out.push("conditional: controls stayed hidden while overflowing");
            return out;
        }"""
    )
    page.close()
    context.close()
    report("carousel-bounds", violations, "cases=14" if not violations else f"violations={len(violations)}")


# ── main.js: one carousel per [data-carousel], once, with the dataset mapped 1:1 ──
def prop_main_init(browser):
    context = browser.new_context()
    proxy = """
      import * as real from "/real/carousel.js";
      window.__calls = [];
      window.__conditional = [];
      export function createCarousel(container, options) {
        window.__calls.push({ id: container.id, options: JSON.parse(JSON.stringify(options || {})) });
        return real.createCarousel(container, options);
      }
      export function createConditionalCarousel(container, options, controls) {
        window.__conditional.push({ id: container.id, options: JSON.parse(JSON.stringify(options || {})) });
        return { instance: null, check() {}, destroy() {}, init() {} };
      }
    """
    stubs = {
        "/assets/js/product/gallery.js": "export function initAllProductGalleries() {}",
        "/assets/js/cart/add-to-cart.js": "export function initCart() {}\nexport function initButtons() {}",
    }
    empty = "export default {};"
    slides = (
        '<div class="vp" data-carousel-viewport><div class="track embla__container">'
        + "".join(f'<div class="embla__slide slide">{i}</div>' for i in range(3))
        + "</div></div>"
        '<button type="button" data-carousel-prev>prev</button>'
        '<button type="button" data-carousel-next>next</button>'
        '<div data-carousel-dots></div>'
        '<div><div data-carousel-progress style="width:0%"></div></div>'
    )
    files = {
        "/harness.html": (
            "text/html",
            f"""<!doctype html><html dir="rtl"><head><style>{CAROUSEL_CSS}</style>
            <script type="importmap">{json.dumps(IMPORT_MAP)}</script></head><body>
              <div id="a" data-carousel>{slides}</div>
              <div id="b" data-carousel data-carousel-loop="true" data-carousel-fade="true"
                   data-carousel-autoplay="3000" data-carousel-autoscroll="0.5"
                   data-carousel-align="center" data-carousel-dragfree="true">{slides}</div>
              <div id="c" data-carousel data-carousel-conditional="true">{slides}</div>
            </body></html>""",
        ),
        "/assets/js/main.js": ("text/javascript", (ROOT / "assets/js/main.js").read_text()),
        "/assets/js/lib/carousel.js": ("text/javascript", proxy),
        "/real/carousel.js": ("text/javascript", (ROOT / "assets/js/lib/carousel.js").read_text()),
    }
    for path, body in stubs.items():
        files[path] = ("text/javascript", body)

    def handler(route):
        url = route.request.url
        path = url[len(ORIGIN):].split("?")[0] if url.startswith(ORIGIN) else ""
        if path.startswith("/assets/js/") and path not in files and path != "/assets/js/lib/carousel.js":
            return route.fulfill(status=200, content_type="text/javascript", body=empty)
        if path in files:
            content_type, body = files[path]
            return route.fulfill(status=200, content_type=content_type, body=body)
        if path.startswith("/nm/"):
            target = ROOT / "node_modules" / path[4:]
            if target.is_file():
                return route.fulfill(status=200, content_type="text/javascript", body=target.read_text())
        return route.fulfill(status=404, body="not found")

    context.route("**/*", handler)
    page = context.new_page()
    page.goto(ORIGIN + "/harness.html")
    page.add_script_tag(type="module", content='import "/assets/js/main.js"; window.__loaded = true;')
    page.wait_for_function("() => window.__loaded === true", timeout=20000)
    page.wait_for_timeout(500)
    if os.environ.get("DEBUG_MAIN"):
        print("DEBUG", page.evaluate("({calls: window.__calls, conditional: window.__conditional, scripts: Array.from(document.scripts).map(s => s.src || s.type)})"))

    violations = page.evaluate(
        """() => {
            const out = [];
            const calls = window.__calls || [];
            const ids = calls.map((call) => call.id).sort();
            if (ids.join(",") !== "a,b") out.push(`initialized ${ids.join(",") || "nothing"}, want a,b`);
            if (new Set(ids).size !== ids.length) out.push(`a container was initialized twice: ${ids}`);

            const mapped = (calls.find((call) => call.id === "b") || {}).options || {};
            const want = { loop: true, fade: true, autoplay: 3000, autoScroll: 0.5, align: "center", dragFree: true };
            for (const key of Object.keys(want)) {
              if (mapped[key] !== want[key]) out.push(`dataset ${key}: ${JSON.stringify(mapped[key])} want ${want[key]}`);
            }
            const bare = (calls.find((call) => call.id === "a") || {}).options || {};
            const defaults = { loop: false, fade: false, autoplay: false, autoScroll: false, align: "start", dragFree: false };
            for (const key of Object.keys(defaults)) {
              if (bare[key] !== defaults[key]) out.push(`bare ${key}: ${JSON.stringify(bare[key])} want ${defaults[key]}`);
            }
            const conditional = window.__conditional || [];
            if (conditional.length !== 1 || conditional[0].id !== "c") {
              out.push(`conditional carousels: ${JSON.stringify(conditional.map((c) => c.id))}`);
            }

            // Re-running on content:loaded must not create a second carousel per container.
            window.__calls.length = 0;
            window.dispatchEvent(new CustomEvent("content:loaded"));
            window.dispatchEvent(new CustomEvent("content:loaded"));
            if (window.__calls.length !== 0) out.push(`content:loaded re-initialized ${window.__calls.length} existing`);

            // A container added later is picked up exactly once.
            const late = document.createElement("div");
            late.id = "d";
            late.setAttribute("data-carousel", "");
            late.innerHTML = document.getElementById("a").innerHTML;
            document.body.appendChild(late);
            window.dispatchEvent(new CustomEvent("content:loaded"));
            window.dispatchEvent(new CustomEvent("content:loaded"));
            const lateCalls = window.__calls.filter((call) => call.id === "d").length;
            if (lateCalls !== 1) out.push(`late container initialized ${lateCalls}x`);
            return out;
        }"""
    )
    page.close()
    context.close()
    report("main-init", violations, "cases=6" if not violations else f"violations={len(violations)}")


# ── layout-loyalty.js: one floating button, on the correct side, opening the SDK once ──
def prop_loyalty(browser):
    page = browser.new_page()
    source = (ROOT / "assets/js/layout-loyalty.js").read_text()
    violations = []
    for direction, side in (("rtl", "left"), ("ltr", "right")):
        page.set_content("<body></body>")
        page.add_script_tag(
            content=f"window.loyalty_button_direction = '{direction}'; window.text_loyalty_rewards = 'Rewards';"
        )
        page.evaluate(
            """() => { window.__opens = 0;
                 window.loyalty_rewards_dialog = { open() { window.__opens += 1; } }; }"""
        )
        page.add_script_tag(content=source)
        page.evaluate("window.dispatchEvent(new Event('load'))")
        page.wait_for_timeout(150)
        state = page.evaluate(
            """() => {
                 const buttons = document.querySelectorAll("#loyalty-floating-btn");
                 const box = buttons[0] && buttons[0].style;
                 return { count: buttons.length, css: box ? box.cssText : "",
                          label: buttons[0] ? buttons[0].innerText.trim() : null,
                          display: box ? box.display : null, opacity: box ? box.opacity : null };
               }"""
        )
        if state["count"] != 1:
            violations.append(f"{direction}: {state['count']} floating buttons")
        if state["display"] != "inline-block" or state["opacity"] != "1":
            violations.append(f"{direction}: button not shown ({state['display']}/{state['opacity']})")
        if state["label"] != "Rewards":
            violations.append(f"{direction}: label {state['label']!r}")
        if f"{side}: 40px" not in state["css"]:
            violations.append(f"{direction}: {side}:40px missing from {state['css'].strip()[:120]}")
        page.locator("#loyalty-floating-btn .loyalty_footer_btn").click()
        page.wait_for_timeout(100)
        opens = page.evaluate("window.__opens")
        if opens != 1:
            violations.append(f"{direction}: dialog opened {opens}x for one click")

    # Without the translated label the module must not create anything.
    page.set_content("<body></body>")
    page.add_script_tag(content="delete window.text_loyalty_rewards;")
    page.add_script_tag(content=source)
    page.evaluate("window.dispatchEvent(new Event('load'))")
    page.wait_for_timeout(100)
    if page.locator("#loyalty-floating-btn").count():
        violations.append("button created without text_loyalty_rewards")
    page.close()
    report("loyalty-button", violations, "cases=3" if not violations else f"violations={len(violations)}")


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROME, headless=True)
        try:
            prop_escape(browser)
            prop_loading(browser)
            prop_carousel(browser)
            prop_main_init(browser)
            prop_loyalty(browser)
        finally:
            browser.close()
    findings = [p for p in PROPERTIES if p[1] != "ok"]
    print(f"# {len(PROPERTIES)} properties, {len(findings)} finding(s)")


if __name__ == "__main__":
    main()
