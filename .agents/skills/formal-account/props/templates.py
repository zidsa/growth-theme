"""Jinja-side properties of formal-account: the wishlist button template, who includes it, and the
phone-input template's contract with js/features/phone-input.js.

    ROOT=<repo> uv run --no-project --with jinja2 python -I props/templates.py

Prints `PROPERTY <id> <ok|finding> <signature>`.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import ROOT, make_env, report  # noqa: E402

ENV = make_env()


def render(name, **ctx):
    return ENV.get_template(name).render(**ctx)


def attrs_of(html, tag):
    return [m for m in re.findall(rf"<{tag}\b[^>]*>", html, re.S)]


# ── wishlist-template ────────────────────────────────────────────────────────
def wishlist_template():
    bad = []
    cases = {
        "true": ({"products": {"wishlist_enabled": True}}, True),
        "false": ({"products": {"wishlist_enabled": False}}, False),
        "none": ({"products": {"wishlist_enabled": None}}, False),
        "missing-key": ({"products": {}}, False),
        "no-products": ({}, False),
        "string-true": ({"products": {"wishlist_enabled": "true"}}, False),
    }
    for label, (settings, expect) in cases.items():
        html = render(
            "components/products/wishlist-button.jinja",
            store={"settings": settings},
            product_id="P-1",
            **{"class": "extra-cls"},
        )
        n = len(re.findall(r"\bdata-wishlist-btn\b", html))
        if n != (1 if expect else 0):
            bad.append(f"enabled={label}: {n} buttons (expected {int(expect)})")
        if expect:
            if 'data-product-id="P-1"' not in html:
                bad.append("product id missing from the button")
            if "extra-cls" not in html:
                bad.append("class prop not applied")
            if 'type="button"' not in html:
                bad.append("button is not type=button (would submit an enclosing form)")
            if not re.search(r'aria-label="Add to wishlist"', html):
                bad.append("no aria-label")
    # product id is written into an attribute; every id a store can have must be addressable by the JS selector
    for pid in ("0d485f0f1-2959-427d-bdb8-f37c99ffc3ad", "12345", "a" * 40):
        html = render(
            "components/products/wishlist-button.jinja",
            store={"settings": {"products": {"wishlist_enabled": True}}},
            product_id=pid,
        )
        if f'data-product-id="{pid}"' not in html:
            bad.append(f"id {pid!r} altered")
    return report("wishlist-template", bad, f"cases={len(cases)}+3")


# ── wishlist-callers ─────────────────────────────────────────────────────────
def wishlist_callers():
    bad, includes = [], 0
    for path in sorted(ROOT.rglob("*.jinja")):
        rel = path.relative_to(ROOT)
        if any(p in ("node_modules", ".agents", "dist") for p in rel.parts) or rel.as_posix() == "components/products/wishlist-button.jinja":
            continue
        src = path.read_text(errors="ignore")
        if "data-wishlist-btn" in src:
            bad.append(f"{rel}: hand-written data-wishlist-btn outside the component")
        for m in re.finditer(r"\{%\s*include\s+'components/products/wishlist-button\.jinja'\s*%\}", src):
            includes += 1
            before = src[: m.start()]
            last_with = before.rfind("{% with")
            last_end = before.rfind("{% endwith %}")
            block = before[last_with : before.find("%}", last_with) + 2] if last_with > last_end else ""
            if "product_id=" not in block:
                line = src[: m.start()].count("\n") + 1
                bad.append(f"{rel}:{line}: include is not inside a `with product_id=` block (button would have an empty id)")
    js = (ROOT / "assets/js/features/wishlist.js").read_text()
    for hook in ("[data-wishlist-btn]", "dataset.productId"):
        if hook not in js:
            bad.append(f"wishlist.js no longer reads {hook}")
    if includes < 3:
        bad.append(f"expected >=3 includes of the component, found {includes}")
    return report("wishlist-callers", bad, f"includes={includes},violations={len(bad)}")


# ── phone-wiring ─────────────────────────────────────────────────────────────
def phone_wiring():
    js = (ROOT / "assets/js/features/phone-input.js").read_text()
    queried = set(re.findall(r'querySelector(?:All)?\(\s*"(\[data-[a-z-]+(?:=[^\]]+)?\])"\s*\)', js))
    queried |= set(re.findall(r"querySelector(?:All)?\(\s*\"(\[data-[a-z-]+='[^']+'\])\"\s*\)", js))
    option_class = ".phone-country-option" in js
    bad = []
    scenarios = 0
    for all_countries in (False, True):
        for disabled in (False, True):
            for error in (False, True):
                for ident in (None, "my-phone"):
                    for country_code in (None, "+20", "+999"):
                        ctx = {"all_countries": all_countries, "disabled": disabled, "error": error, "session": {"lang": "en"}}
                        if ident:
                            ctx["id"] = ident
                        if country_code:
                            ctx["country_code"] = country_code
                        html = render("components/ui/phone-input.jinja", **ctx)
                        scenarios += 1
                        tag = f"[all={all_countries},disabled={disabled},error={error},id={ident},cc={country_code}]"
                        for sel in sorted(queried):
                            name = re.match(r"\[(data-[a-z-]+)", sel).group(1)
                            count = len(re.findall(rf"(?<![\w-]){re.escape(name)}(?![\w-])", html))
                            if sel.startswith("[data-slot"):
                                count = html.count("data-slot=\"country-trigger\"")
                            if name == "data-phone-input-id":
                                continue
                            if count != 1:
                                bad.append(f"{tag} {sel}: {count} occurrences (JS expects exactly one)")
                        if option_class and not all_countries and "phone-country-option" not in html:
                            bad.append(f"{tag} no .phone-country-option rendered for the static list")
                        trigger = re.search(r'popovertarget="([^"]+)"', html)
                        popover = re.search(r'<el-popover\s+id="([^"]+)"', html)
                        if not trigger or not popover or trigger.group(1) != popover.group(1):
                            bad.append(f"{tag} popovertarget does not match the el-popover id")
                        trigger_tag = re.search(r'<button[^>]*data-slot="country-trigger"[^>]*>', html, re.S)
                        if disabled and not (trigger_tag and "disabled" in trigger_tag.group(0)):
                            bad.append(f"{tag} trigger not disabled")
                        if ident and f'id="{ident}"' not in html:
                            bad.append(f"{tag} id prop not applied to the full-value input")
                        if bool(all_countries) != ("data-all-countries" in html):
                            bad.append(f"{tag} data-all-countries must be present iff all_countries")
    return report("phone-wiring", bad, f"scenarios={scenarios},hooks={len(queried)}")


if __name__ == "__main__":
    wishlist_template()
    wishlist_callers()
    phone_wiring()
