"""Drive a running verify-growth-theme storefront (vitrin rendering THIS theme) in headless Chrome and save evidence.

Run: uv run --no-project --with playwright python -I drive.py <journey> [--port 8993]
Journeys: home, catalog, add-to-cart, plus every JOURNEYS entry in the group skills'
.agents/skills/verify-*/journeys.py (list them with --list).

Exit 0 = the journey passed, or it is a recorded finding (the group's KNOWN table) that failed
exactly the recorded checks (prints `FINDING`). Exit 1 = any other outcome: a failure, a crash, a
recorded finding that failed differently, or one that no longer reproduces (prints `CHANGED`).
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

_MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME = os.environ.get(
    "CHROME", _MAC_CHROME if sys.platform == "darwin" else "/usr/bin/google-chrome"
)


def evidence_dir(journey: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    root = Path(os.environ.get("VERIFY_HOME", Path.home() / ".cache/verify-growth-theme")) / "evidence"
    d = root / f"{stamp}-{journey}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def home(page, base, out, checks):
    resp = page.goto(base + "/", wait_until="load")
    checks["status"] = resp.status
    checks["title"] = page.title()
    checks["header_cart_link"] = page.locator("a[href*='/cart']").count() > 0
    page.screenshot(path=out / "home.png", full_page=True)
    return resp.status == 200 and checks["header_cart_link"]


def catalog(page, base, out, checks):
    page.goto(base + "/", wait_until="load")
    page.screenshot(path=out / "1-home.png")
    # The store menu's "all products" link; matched by href, not by its translated label.
    # The mobile drawer holds a hidden copy of the menu, so take the visible one.
    page.locator("header a[href$='/products'], header a[href$='/products/']").locator(
        "visible=true"
    ).first.click()
    page.wait_for_url(re.compile(r"/products/?(\?.*)?$"))
    page.wait_for_load_state("load")
    checks["url"] = page.url
    checks["product_cards"] = page.locator("[data-product-card]").count()
    # products-header.jinja: "{current} out of {total} products" (translated in ar).
    header = (
        page.locator("span", has_text=re.compile(r"\d+\D+\d+"))
        .filter(has_text=re.compile("products|منتج"))
        .first
    )
    checks["count_text"] = (
        " ".join(header.inner_text().split()) if header.count() else None
    )
    page.screenshot(path=out / "2-products.png")
    # Cross-check the rendered total against the JSON API for the same store.
    api = page.request.get(base + "/api/v1/products?page_size=1")
    checks["api_status"] = api.status
    checks["api_count"] = api.json().get("count") if api.ok else None
    numbers = [int(n) for n in re.findall(r"\d+", checks["count_text"] or "")]
    checks["listing_total"] = max(numbers) if numbers else None
    return (
        checks["product_cards"] > 0
        and api.ok
        and checks["listing_total"] == checks["api_count"]
    )


def add_to_cart(page, base, out, checks):
    # Pick an in-stock simple product through the public listing API.
    api = page.request.get(base + "/api/v1/products?page_size=50&availability=in_stock")
    product = next(
        p for p in api.json()["results"] if not p["has_options"] and not p["has_fields"]
    )
    checks["product"] = {"id": product["id"], "slug": product["slug"]}
    page.goto(base + "/products/" + product["slug"], wait_until="load")
    checks["product_page_url"] = page.url
    if "/auth/login" in page.url:
        checks["failure"] = (
            "product page redirected to login: an upstream call returned 401 (API_TOKEN missing?)"
        )
        page.screenshot(path=out / "product.png")
        return False
    page.screenshot(path=out / "1-product.png")
    with page.expect_response(
        lambda r: r.url.endswith("/api/v1/cart/items") and r.request.method == "POST"
    ) as added:
        page.locator("[data-in-stock] button[data-add-to-cart-form]").first.click()
    checks["add_status"] = added.value.status
    add_body = added.value.json() if added.value.ok else {}
    (out / "add-response.json").write_text(json.dumps(add_body, ensure_ascii=False, indent=2))
    checks["add_cart_id"] = (add_body.get("cart") or add_body).get("id")
    page.wait_for_timeout(1000)
    page.screenshot(path=out / "2-after-add.png")
    # The cart lists product_id as bare UUID hex ("7157...d781"); the listing API uses dashes.
    want = product["id"].replace("-", "")
    # The upstream cart read can lag the 201 by a few seconds: poll it, up to ~10 s.
    for attempt in range(10):
        cart = page.request.get(base + "/api/v1/cart")
        body = cart.json() if cart.ok else {}
        checks["product_in_cart"] = any(
            str(p.get("product_id", "")).replace("-", "") == want
            for p in body.get("products", [])
        )
        if checks["product_in_cart"]:
            break
        page.wait_for_timeout(1000)
    checks["cart_status"], checks["cart_reads"] = cart.status, attempt + 1
    checks["read_cart_id"] = body.get("id")
    (out / "cart.json").write_text(json.dumps(body, ensure_ascii=False, indent=2))
    page.goto(base + "/cart", wait_until="load")
    page.screenshot(path=out / "3-cart.png", full_page=True)
    # Store 1 is shared: empty this session's cart (DELETE /api/v1/cart/items, 204).
    checks["cart_cleared_status"] = page.request.delete(base + "/api/v1/cart/items").status
    return cart.ok and checks["product_in_cart"]


JOURNEYS = {"home": home, "catalog": catalog, "add-to-cart": add_to_cart}
# Recorded product bugs: {journey: (failed_checks the bug produces, one-line finding)}. Each group
# skill exports its own KNOWN next to its JOURNEYS; a journey listed here must set
# checks["failed_checks"] (the names of its conditions that failed).
KNOWN = {}


def load_group_journeys() -> None:
    """Add journeys from sibling group skills: .agents/skills/verify-*/journeys.py.

    Each file exports JOURNEYS = {"<name>": fn(page, base, out, checks) -> bool}.
    Names must be unique across skills; a clash stops the run instead of shadowing.
    """
    import importlib.util

    skills = Path(__file__).resolve().parents[2]
    for path in sorted(skills.glob("verify-*/journeys.py")):
        spec = importlib.util.spec_from_file_location(f"journeys_{path.parent.name}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, fn in module.JOURNEYS.items():
            if name in JOURNEYS:
                sys.exit(f"journey {name!r} in {path} clashes with an existing journey")
            JOURNEYS[name] = fn
        for name, known in getattr(module, "KNOWN", {}).items():
            if name not in module.JOURNEYS:
                sys.exit(f"KNOWN {name!r} in {path} names no journey of that skill")
            KNOWN[name] = known


def outcome(journey, passed, checks):
    """pass | finding | changed | fail, and the line that explains it."""
    if journey not in KNOWN:
        return ("pass", None) if passed else ("fail", None)
    want, finding = KNOWN[journey]
    if passed:
        return "changed", f"CHANGED {journey}: the recorded finding no longer reproduces ({finding}). Fixed? Drop it from KNOWN and the skill's findings."
    got = checks.get("failed_checks")
    if "error" not in checks and not checks.get("theme_errors") and got is not None and set(got) == set(want):
        return "finding", f"FINDING {journey} still reproduces: {finding}"
    return "changed", f"CHANGED {journey}: recorded failed_checks {sorted(want)}, now {got} (error: {checks.get('error')}, theme errors: {checks.get('theme_errors')})"


load_group_journeys()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey", nargs="?", choices=JOURNEYS)
    ap.add_argument("--port", type=int, default=8995)
    ap.add_argument("--list", action="store_true", help="print journey names and exit")
    args = ap.parse_args()
    if args.list or not args.journey:
        print("\n".join(sorted(JOURNEYS)))
        sys.exit(0 if args.list else 2)
    base = f"http://127.0.0.1:{args.port}"
    out = evidence_dir(args.journey)
    checks, network, console = {}, [], []
    started = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        ctx = browser.new_context(
            locale="ar-SA", viewport={"width": 1280, "height": 900}
        )
        page = ctx.new_page()
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}"))
        page.on(
            "response",
            lambda r: (
                network.append(f"{r.status} {r.request.method} {r.url}")
                if r.url.startswith(base)
                else None
            ),
        )
        try:
            passed = JOURNEYS[args.journey](page, base, out, checks)
        except Exception as exc:  # the failure itself is evidence
            passed, checks["error"] = False, repr(exc)
            page.screenshot(path=out / "error.png")
        browser.close()
    (out / "network.log").write_text("\n".join(network))
    (out / "console.log").write_text("\n".join(console))
    result, note = outcome(args.journey, passed, checks)
    summary = {
        "journey": args.journey,
        "passed": passed,
        "outcome": result,
        "base": base,
        "seconds": round(time.time() - started, 1),
        "checks": checks,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.stdout.write(
        json.dumps(summary, ensure_ascii=False, indent=2) + (f"\n{note}" if note else "") + f"\nevidence: {out}\n"
    )
    sys.exit(0 if result in ("pass", "finding") else 1)


if __name__ == "__main__":
    main()
