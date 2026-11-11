"""Formal properties P1-P3 and the component suite for the layout group's Jinja surface.

Runs plain Jinja2 (as tests/repro does) over the real templates in $ROOT. Prints one
`PROPERTY <id> <ok|finding> <signature>` line per property; check.sh compares those lines
with the recorded outcomes.

    ROOT=<repo> uv run --no-project --with jinja2 python -I props/templates.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from jinja2 import ChainableUndefined, ChoiceLoader, DictLoader, FileSystemLoader, nodes, select_autoescape
from jinja2.ext import Extension
from jinja2.sandbox import SandboxedEnvironment

ROOT = Path(os.environ.get("ROOT", ".")).resolve()
SKILL = Path(__file__).resolve().parents[1]

ROOT_TEMPLATES = ["layout.jinja", "header.jinja", "footer.jinja"]
COMPONENTS = [
    "components/header-announcement-bar.jinja",
    "components/rating-stars.jinja",
    "components/header/logo.jinja",
    "components/header/main-nav.jinja",
    "components/header/mobile-drawer.jinja",
    "components/header/region-selector.jinja",
    "components/header/search.jinja",
    "components/shared/metafields.jinja",
    "components/ui/breadcrumb.jinja",
    "components/ui/disclosure.jinja",
    "components/ui/pagination.jinja",
    "components/ui/phone-input.jinja",
    "components/ui/quantity-input.jinja",
]
GROUP_TEMPLATES = ROOT_TEMPLATES + COMPONENTS + ["templates/404_not_found.jinja"]
SCHEMAS = ["header.schema.json", "footer.schema.json", "layout.schema.json"]

PROPERTIES = []


def report(prop_id, ok, signature="-", detail=""):
    status = "ok" if ok else "finding"
    PROPERTIES.append((prop_id, status, signature))
    print(f"PROPERTY {prop_id} {status} {signature}", flush=True)
    if detail:
        for line in detail.strip().splitlines():
            print(f"    {line}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Render harness (same shape as tests/repro/test_inquiry_728_oos_markup.py)
# ─────────────────────────────────────────────────────────────────────────────
class Stub(ChainableUndefined):
    def __call__(self, *a, **k):
        return Stub()


class VitrinTagStubs(Extension):
    tags = {"vitrin_head", "vitrin_body", "template_components", "ai_component"}

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        while parser.stream.current.type != "block_end":
            next(parser.stream)
        return nodes.Output([nodes.TemplateData("")], lineno=lineno)


URLS = {"profile": "/account", "home": "/", "cart_page": "/cart", "list_products": "/products"}


def url_for(name, **kwargs):
    return URLS.get(name, f"/{name}")


def safeget(obj, path, default=None):
    cur = obj
    for part in str(path).split("."):
        if isinstance(cur, dict):
            if part not in cur:
                return default
            cur = cur[part]
        else:
            cur = getattr(cur, part, None)
            if cur is None:
                return default
    return default if cur is None else cur


def make_env():
    env = SandboxedEnvironment(
        loader=ChoiceLoader([FileSystemLoader(str(ROOT))]),
        undefined=Stub,
        autoescape=select_autoescape(),  # vitrin sdk/jinja.py: OFF for .jinja
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols", "jinja2.ext.i18n", VitrinTagStubs],
    )
    real_get_template = env.get_template

    def get_template(name, *args, **kwargs):
        if isinstance(name, str) and name.startswith("vitrin:"):
            return env.from_string("")
        return real_get_template(name, *args, **kwargs)

    env.get_template = get_template
    env.install_null_translations(newstyle=True)
    env.globals.update(_=lambda s, *a, **k: s, url_for=url_for, safeget=safeget, get_flashed_messages=lambda **k: [])
    env.filters.update(
        currency=lambda v, *a, **k: v,
        money=lambda v, *a, **k: v,
        format_price=lambda v, *a, **k: v,
        asset_url=lambda v, *a, **k: f"/assets/{v}",
        image_url=lambda v, *a, **k: f"/img/{v}",
        tojson_safe=lambda v, *a, **k: json.dumps(v),
        t=lambda v, *a, **k: v,
        translate=lambda v, *a, **k: v,
    )
    # Platform filters we do not model (localized_url, ...) pass their value through, so a
    # template that uses one still renders; their output shape is not what these checks assert.
    used_filters = set()
    for path in list(ROOT.glob("*.jinja")) + list(ROOT.glob("components/**/*.jinja")) + list(
        ROOT.glob("templates/*.jinja")
    ):
        try:
            tree = env.parse(path.read_text(errors="ignore"))
        except Exception:
            continue
        used_filters |= {node.name for node in tree.find_all(nodes.Filter)}
    for name in used_filters - set(env.filters):
        env.filters[name] = lambda value, *a, **k: value
    return env


ENV = make_env()


class Dot:
    """Attribute container: fixture data must not collide with dict methods (.items)."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __contains__(self, key):
        return key in self.__dict__

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def keys(self):
        return self.__dict__.keys()


def dot(value):
    if isinstance(value, dict):
        return Dot(**{key: dot(item) for key, item in value.items()})
    if isinstance(value, list):
        return [dot(item) for item in value]
    return value


def base_ctx(**over):
    ctx = {
        "settings": {},
        "store": {
            "name": "Property Store",
            "logo": None,
            "languages": [{"code": "ar"}, {"code": "en"}],
            "countries": [{"code": "SA", "name": "Saudi Arabia"}],
            "settings": dot({
                "products": {"low_stock_label_enabled": False, "is_metafields_enabled": False},
                "checkout": {"is_loyalty_enabled": True},
                "menus": {"main_menu": {"items": []}},
                "zones": {"selection_enabled": False, "precision": "city"},
                "branding": {"copyrights": ""},
                "contact": {},
            }),
        },
        "session": {
            "lang": "ar",
            "template": "home",
            "locale": {"language": {"direction": "rtl"}},
            "country": {"name": "Saudi Arabia"},
        },
        "user_custom_css": None,
    }
    ctx.update(over)
    return dot(ctx)


def render(template, **ctx):
    return ENV.get_template(template).render(**ctx)


def count(html, needle):
    return html.count(needle)


# ─────────────────────────────────────────────────────────────────────────────
# P1 settings-keys: no template may read a key its schemas do not declare, and the
# three group schemas may not declare a key nothing reads.
# ─────────────────────────────────────────────────────────────────────────────
def declared_keys():
    declared = {}
    for name in SCHEMAS:
        data = json.loads((ROOT / name).read_text())
        for group in data.get("groups", []):
            for setting in group.get("settings", []):
                declared[f"{group['id']}_{setting['id']}"] = name
    return declared


def read_keys(text):
    """Theme-settings keys a template reads, straight from the Jinja AST.

    Counts `settings.<key>` (any depth: settings.theme_primary, settings.x.y) and
    `safeget(settings, "<key>")`. `store.settings.<key>` is store data, not a theme setting.
    """
    keys = set()
    try:
        tree = ENV.parse(text)
    except Exception:
        return keys
    for node in tree.find_all((nodes.Getattr, nodes.Call)):
        if isinstance(node, nodes.Getattr):
            base = node.node
            while isinstance(base, nodes.Getattr):
                if base.attr == "settings" and isinstance(base.node, nodes.Name) and base.node.name == "store":
                    base = None
                    break
                base = base.node
            if isinstance(base, nodes.Name) and base.name == "settings":
                keys.add(node.attr)
        else:
            fn = node.node
            fn_name = fn.attr if isinstance(fn, nodes.Getattr) else getattr(fn, "name", None)
            if (
                fn_name == "safeget"
                and len(node.args) >= 2
                and isinstance(node.args[0], nodes.Name)
                and node.args[0].name == "settings"
                and isinstance(node.args[1], nodes.Const)
                and isinstance(node.args[1].value, str)
            ):
                keys.add(node.args[1].value)
    return keys


def prop_settings_keys():
    declared = declared_keys()
    unknown = {}
    for template in GROUP_TEMPLATES:
        if not (ROOT / template).exists():
            unknown.setdefault("missing-template", set()).add(template)
            continue
        for key in read_keys((ROOT / template).read_text()):
            if key not in declared:
                unknown.setdefault(key, set()).add(template)

    # Reverse: a declared key must be read by some template or script in the repo.
    everywhere = []
    for path in list(ROOT.glob("*.jinja")) + list(ROOT.glob("templates/**/*.jinja")) + list(
        ROOT.glob("components/**/*.jinja")
    ) + list(ROOT.glob("sections/*.jinja")):
        everywhere.append(path.read_text(errors="ignore"))
    for path in (ROOT / "assets/js").rglob("*.js"):
        everywhere.append(path.read_text(errors="ignore"))
    haystack = "\n".join(everywhere)
    unread = sorted(key for key in declared if key not in read_keys(haystack))

    detail = []
    if unknown:
        detail.append("templates read undeclared keys:")
        for key, templates in sorted(unknown.items()):
            detail.append(f"  {key} <- {', '.join(sorted(templates))}")
    if unread:
        detail.append("declared in the group's schemas but read by no template or script:")
        detail.append("  " + ", ".join(f"{key} ({declared[key]})" for key in unread))
    ok = not unknown and not unread
    signature = "unknown=%d,unread=%s" % (len(unknown), ",".join(unread) or "-")
    report("settings-keys", ok, signature, "\n".join(detail))


# ─────────────────────────────────────────────────────────────────────────────
# P2 layout-gates: shell invariants and the loyalty / announcement gates.
# ─────────────────────────────────────────────────────────────────────────────
LOYALTY_EXCLUDED = {"product_details", "cart_page", "page_details"}


def prop_layout_gates():
    problems = []
    for template in ["home", "product_details", "cart_page", "page_details", "list_products", "404_not_found.jinja"]:
        for direction in ("rtl", "ltr"):
            for loyalty in (True, False):
                ctx = base_ctx()
                ctx["session"]["template"] = template
                ctx["session"]["locale"]["language"]["direction"] = direction
                ctx["store"]["settings"]["checkout"]["is_loyalty_enabled"] = loyalty
                html = render("layout.jinja", **ctx)
                want_loyalty = loyalty and template not in LOYALTY_EXCLUDED
                checks = {
                    "html dir": f'dir="{direction}"' in html,
                    "html lang": 'lang="ar"' in html,
                    "one main#main": count(html, 'id="main"') == 1 and count(html, "<main") == 1,
                    "data-template": f'data-template="{template}"' in html,
                    "one header": count(html, "<header") == 1,
                    "one footer": count(html, 'id="footer"') == 1,
                    "one theme bundle": count(html, "dist/theme.js") == 1,
                    "layoutConfig": 'profileUrl: "/account"' in html,
                    "loyalty gate": count(html, "js/layout-loyalty.js") == (1 if want_loyalty else 0),
                    "loyalty globals": count(html, "text_loyalty_rewards") == (1 if want_loyalty else 0),
                }
                for name, ok in checks.items():
                    if not ok:
                        problems.append(f"{template}/{direction}/loyalty={loyalty}: {name}")

    for template in ("home", "cart_page"):
        for display in (False, True):
            for page_display in ("", "home", "all"):
                ctx = base_ctx()
                ctx["settings"] = {
                    "announcement_bar_display": display,
                    "announcement_bar_page_display": page_display,
                    "announcement_bar_texts": [{"text": "Free shipping"}],
                }
                ctx["session"]["template"] = template
                html = render("layout.jinja", **ctx)
                want = display and (
                    not page_display or (template == "home" and page_display == "home") or page_display == "all"
                )
                if count(html, "data-announcement-bar") != (1 if want else 0):
                    problems.append(f"announcement {template}/{display}/{page_display!r}")
    report(
        "layout-gates",
        not problems,
        f"violations={len(problems)}",
        "\n".join(problems[:12]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# P3 404-countdown: the rendered countdown script ticks 3-2-1-0 then goes home once.
# ─────────────────────────────────────────────────────────────────────────────
def prop_404():
    html = render("templates/404_not_found.jinja", **base_ctx())
    problems = []
    if count(html, 'id="redirectCountdown"') != 1:
        problems.append("countdown element is not unique")
    if not re.search(r'id="redirectCountdown">3<', html):
        problems.append("countdown does not start at 3")
    if count(html, 'href="/"') < 1:
        problems.append("no home call to action")
    script = next((m for m in re.finditer(r"<script>(.*?)</script>", html, re.S) if "startRedirectCountdown" in m.group(1)), None)
    if not script:
        problems.append("countdown script not found in the rendered page")
        report("404-countdown", False, f"violations={len(problems)}", "\n".join(problems))
        return

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "countdown.js"
        path.write_text(script.group(1))
        run = subprocess.run(
            [os.environ.get("NODE", "node"), str(SKILL / "props/run_script.mjs"), str(path)],
            capture_output=True,
            text=True,
        )
    try:
        state = json.loads(run.stdout.strip().splitlines()[-1])
    except Exception:
        report(
            "404-countdown",
            False,
            "script-error",
            (run.stdout + run.stderr)[-800:],
        )
        return
    ticks, redirects = state["ticks"], state["navigations"]
    if ticks != [3, 2, 1, 0]:
        problems.append(f"tick sequence {ticks} != [3, 2, 1, 0]")
    if any(t < 0 for t in ticks):
        problems.append(f"negative tick in {ticks}")
    if len(redirects) != 1:
        problems.append(f"{len(redirects)} navigations: {redirects}")
    elif redirects[0] != "/":
        problems.append(f"redirect target {redirects[0]!r} is not the home path")
    if not state["cleared"]:
        problems.append("interval was not cleared, ticks would continue")
    report("404-countdown", not problems, f"violations={len(problems)}", "\n".join(problems))


# ─────────────────────────────────────────────────────────────────────────────
# P4 components
# ─────────────────────────────────────────────────────────────────────────────
def prop_rating_stars():
    import math

    problems = []
    for rating in [0, 0.1, 0.25, 0.5, 0.74, 0.75, 1, 1.2, 2.5, 3.4, 4.1, 4.5, 4.9, 5.0, 5.7, -1]:
        html = render("components/rating-stars.jinja", rating=rating, size=16)
        full = html.count('class="text-warning"')
        half = html.count("url(#half-star-")
        empty = html.count('class="text-muted-foreground"')
        want = min(5.0, max(0.0, math.ceil(rating * 2) / 2))
        if full + half * 0.5 != want:
            problems.append(f"rating {rating}: {full} full + {half} half, want {want}")
        if full + half + empty != 5:
            problems.append(f"rating {rating}: {full + half + empty} stars rendered, want 5")
    if render("components/rating-stars.jinja", rating=None).strip():
        problems.append("rating=None still renders stars")
    report("rating-stars", not problems, f"violations={len(problems)}", "\n".join(problems[:6]))


def menu_items(n):
    return [dot({"label": f"Item {i}", "url": f"/p/{i}", "resource_type": "custom", "items": []}) for i in range(n)]


def store_with_menu(n, **extra):
    ctx = base_ctx()
    ctx["store"]["settings"]["menus"]["main_menu"]["items"] = menu_items(n)
    for key, value in extra.items():
        ctx["store"]["settings"][key] = value
    return ctx


def prop_main_nav():
    problems = []
    for n in range(0, 11):
        html = render("components/header/main-nav.jinja", **store_with_menu(n))
        rendered = len(re.findall(r'data-menu-index="\d+"', html))
        more = "More" in html
        expected_visible = min(n, 6)
        if n == 0:
            if rendered:
                problems.append(f"{n} items rendered {rendered} links")
            continue
        if more != (n > 6):
            problems.append(f"{n} items: More trigger present={more}")
        visible_part, _, overflow_part = html.partition("more-menu-popover")
        labels = set(re.findall(r">\s*Item (\d+)\s*<", visible_part))
        if len(labels) != expected_visible:
            problems.append(f"{n} items: {len(labels)} visible labels, want {expected_visible}")
        overflow = set(re.findall(r">\s*Item (\d+)\s*<", overflow_part)) if more else set()
        if more and len(overflow) != n - 6:
            problems.append(f"{n} items: {len(overflow)} overflow labels, want {n - 6}")
        if more and (labels & overflow):
            problems.append(f"{n} items: an item is both visible and overflow")
    report("main-nav", not problems, f"violations={len(problems)}", "\n".join(problems[:6]))


def prop_mobile_drawer():
    problems = []
    for n in (0, 1, 6, 7, 9):
        for countries, languages in ((1, 1), (2, 1), (1, 2)):
            ctx = store_with_menu(n)
            ctx["store"]["countries"] = [{"code": f"C{i}", "name": f"C{i}"} for i in range(countries)]
            ctx["store"]["languages"] = [{"code": c} for c in ("ar", "en")[:languages]]
            html = render("components/header/mobile-drawer.jinja", **ctx)
            labels = re.findall(r">\s*Item (\d+)\s*<", html)
            if len(labels) != n or len(set(labels)) != n:
                problems.append(f"{n} items/{countries}c/{languages}l: drawer shows {labels}")
            region = "zidOpenRegionSettingDialog" in html
            if region != (countries > 1 or languages > 1):
                problems.append(f"{n} items/{countries}c/{languages}l: region control={region}")
            if html.count('id="mobile-login-btn"') != 1:
                problems.append(f"{n} items: {html.count('id=\"mobile-login-btn\"')} login entries")
    report("mobile-drawer", not problems, f"violations={len(problems)}", "\n".join(problems[:6]))


def prop_logo():
    problems = []
    ctx = base_ctx()
    ctx["settings"] = {"logo_desktop": "logo.png"}
    html = render("components/header/logo.jinja", **ctx)
    if html.count("<img") != 1:
        problems.append(f"desktop logo: {html.count('<img')} images")
    ctx["settings"] = {"logo_mobile": "m.png"}
    html = render("components/header/logo.jinja", **ctx)
    if html.count("<img") != 1:
        problems.append(f"mobile-only logo: {html.count('<img')} images")
    ctx["settings"] = {}
    ctx["store"]["logo"] = "store.png"
    html = render("components/header/logo.jinja", **ctx)
    if html.count("<img") != 1:
        problems.append(f"store logo: {html.count('<img')} images")
    ctx["store"]["logo"] = None
    html = render("components/header/logo.jinja", **ctx)
    if "<h2" not in html or "<img" in html:
        problems.append("no logo at all: expected the store-name heading only")
    report("logo", not problems, f"violations={len(problems)}", "\n".join(problems))


def prop_region_selector():
    problems = []
    cases = []
    for countries in (1, 2):
        for languages in (1, 2):
            for zones in (False, True):
                for hide_country in (False, True):
                    cases.append((countries, languages, zones, hide_country))
    for countries, languages, zones, hide_country in cases:
        ctx = base_ctx()
        ctx["store"]["countries"] = [{"code": f"C{i}"} for i in range(countries)]
        ctx["store"]["languages"] = [{"code": c} for c in ("ar", "en")[:languages]]
        ctx["store"]["settings"]["zones"] = {"selection_enabled": zones, "precision": "coordinates"}
        ctx["settings"] = {"header_hide_country": hide_country}
        html = render("components/header/region-selector.jinja", **ctx)
        want = zones or (countries > 1 and not hide_country) or languages > 1
        has_button = "zidOpenRegionSettingDialog" in html and "<li" in html
        if has_button != want:
            problems.append(
                f"countries={countries} languages={languages} zones={zones} hide_country={hide_country}:"
                f" button={has_button} want={want}"
            )
        if zones and "zid_kit_select_branch" not in html:
            problems.append("coordinates mode does not render the stored-branch script")
    report("region-selector", not problems, f"violations={len(problems)}", "\n".join(problems[:6]))


def prop_quantity_input():
    problems = []
    for qty, low, high in [(1, 1, None), (3, 1, 10), (0, 1, 5), (7, 2, 5), (1, 1, 0)]:
        html = render(
            "components/ui/quantity-input.jinja", id="q", name="quantity", quantity=qty, min=low, max=high
        )
        if html.count('type="number"') != 1:
            problems.append(f"qty={qty} min={low} max={high}: {html.count('type=\"number\"')} number inputs")
        if f'value="{qty}"' not in html:
            problems.append(f"qty={qty}: value attribute missing")
        if f'min="{low}"' not in html:
            problems.append(f"qty={qty}: min={low} missing")
        has_max = high is not None and high
        if bool(has_max) != ('max="' in html):
            problems.append(f"qty={qty} max={high}: max attribute present={('max=\"' in html)}")
        actions = re.findall(r'data-qty-action="(\w+)"', html)
        if "increase" not in actions or "decrease" not in actions:
            problems.append(f"qty={qty}: actions {actions}")
    html = render("components/ui/quantity-input.jinja", id="q", quantity=1, min=1, show_delete=True)
    if 'data-qty-action="remove"' not in html:
        problems.append("show_delete does not render the remove action")
    report("quantity-input", not problems, f"violations={len(problems)}", "\n".join(problems[:6]))


def prop_disclosure():
    problems = []
    for multi in (True, False):
        html = render("components/ui/disclosure.jinja", id="d1", title="T", content="<b>body</b>", multi=multi, group="g")
        want = "checkbox" if multi else "radio"
        if html.count('type="checkbox"') != (1 if multi else 0):
            problems.append(f"multi={multi}: checkbox count wrong")
        if html.count('type="radio"') != (0 if multi else 1):
            problems.append(f"multi={multi}: radio count wrong")
        if not multi and 'name="g"' not in html:
            problems.append("single-open disclosure has no radio group name")
        if f'for="d1"' not in html or 'id="d1"' not in html:
            problems.append(f"multi={multi}: label/input id wiring")
        if "<b>body</b>" not in html:
            problems.append("content is not passed through as HTML")
        if html.count("<input") != 1:
            problems.append(f"multi={multi}: {html.count('<input')} inputs")
    report("disclosure", not problems, f"violations={len(problems)}", "\n".join(problems[:6]))


def prop_breadcrumb():
    """Labels are merchant data (category.jinja passes category.name) and must be escaped."""
    problems = []
    html = render(
        "components/ui/breadcrumb.jinja",
        items=[
            {"href": "/", "label": "Home"},
            {"href": "/c", "label": "<img src=x onerror=alert(1)>"},
            {"label": "Current"},
        ],
    )
    raw = "<img src=x onerror=alert(1)>" in html
    escaped = "&lt;img src=x onerror=alert(1)&gt;" in html
    if raw and not escaped:
        problems.append(
            "label '<img src=x onerror=alert(1)>' is rendered unescaped (components/ui/breadcrumb.jinja:19,29 use |safe)"
        )
    if html.count('aria-current="page"') != 1:
        problems.append("exactly one aria-current page expected")
    if html.count('role="presentation"') != 2:
        problems.append(f"{html.count('role=\"presentation\"')} separators for 3 items (want 2)")
    report(
        "breadcrumb",
        not problems,
        "labels-unescaped" if raw and not escaped else f"violations={len(problems)}",
        "\n".join(problems),
    )


def prop_pagination():
    import html as html_mod

    problems = []
    module = ENV.get_template("components/ui/pagination.jinja").module
    href = "/products?q=ab&page=2&sort=price"
    escape = lambda markup: html_mod.unescape(markup)
    link = escape(module.PaginationLink(href=href, page="2", isActive=False))
    if f'href="{href}"' not in link:
        problems.append("inactive page link does not keep its full query string")
    active = escape(module.PaginationLink(href=href, page="2", isActive=True))
    if "href=" in active or 'aria-current="page"' not in active:
        problems.append("active page link is a link or lacks aria-current")
    for name in ("PaginationFirst", "PaginationPrevious", "PaginationNext", "PaginationLast"):
        enabled = escape(getattr(module, name)(href=href, disabled=False))
        disabled = escape(getattr(module, name)(href=href, disabled=True))
        if f'href="{href}"' not in enabled:
            problems.append(f"{name}: enabled control lost its href")
        if "href=" in disabled:
            problems.append(f"{name}: disabled control still links to {href}")
        if 'aria-disabled="true"' not in disabled:
            problems.append(f"{name}: disabled control is not aria-disabled")
    nav = escape(module.Pagination(id="p", ariaLabel="pagination"))
    if 'data-slot="pagination"' not in nav:
        problems.append("pagination wrapper slot missing")
    report("pagination", not problems, f"violations={len(problems)}", "\n".join(problems[:6]))


def prop_metafields():
    problems = []
    entity = {"metafields": [{"name": {"ar": "الوزن", "en": "Weight"}, "data_type": "text", "value": {"ar": "1 كجم", "en": "1 kg"}}]}
    store = base_ctx()["store"]
    store["settings"]["products"]["is_metafields_enabled"] = False
    html = render("components/shared/metafields.jinja", entity=entity, store=store, session={"lang": "ar"})
    if html.strip():
        problems.append("metafields render while the store flag is off")

    store["settings"]["products"]["is_metafields_enabled"] = True
    fields = [
        {"name": {"ar": "نص"}, "data_type": "text", "value": {"ar": "<b>x</b>"}},
        {"name": {"ar": "رقم"}, "data_type": "number", "value": 42},
        {"name": {"ar": "json"}, "data_type": "json", "value": {"a": 1}},
        {"name": {"ar": "صورة"}, "data_type": "image", "value": {"small": "s.png"}},
        {
            "name": {"ar": "جدول"},
            "data_type": "table",
            "value": {
                "headers": [{"name": {"ar": "أ"}}, {"name": {"ar": "ب"}}],
                "cells": [[{"value": 1}, {"value": 2}], [{"value": 3}, {"value": 4}]],
            },
        },
    ]
    html = render("components/shared/metafields.jinja", entity={"metafields": fields}, store=store, session={"lang": "ar"})
    if html.count("<dt") != 4:
        problems.append(f"{html.count('<dt')} rows for 5 fields (json must be skipped)")
    if "&lt;b&gt;x&lt;/b&gt;" not in html:
        problems.append("text metafield value is not escaped")
    if ">42<" not in html.replace(" ", ""):
        problems.append("number metafield value missing")
    if html.count("<tr") != 3:
        problems.append(f"table renders {html.count('<tr')} <tr> for a header row + 2 body rows")
    if html.count("<td") != 4:
        problems.append(f"table renders {html.count('<td')} cells for 4 cells")
    report("metafields", not problems, f"violations={len(problems)}", "\n".join(problems[:6]))


def prop_phone_input():
    problems = []
    html = render("components/ui/phone-input.jinja", id="ph", name="phone", country_code="+966", all_countries=True)
    options = re.findall(r'data-dial-code="(\+\d+)"', html)
    if len(options) != 18:
        problems.append(f"{len(options)} default country options, want 18")
    if 'data-all-countries="true"' not in html:
        problems.append("all_countries does not set data-all-countries")
    if 'value="+966"' not in html:
        problems.append("hidden country code / full value is not seeded from country_code")
    if html.count('data-phone-country-code') != 1 or html.count("data-phone-full-value") != 1:
        problems.append("hidden inputs missing")
    if 'data-phone-country-search' not in html:
        problems.append("country search input missing")
    custom = render(
        "components/ui/phone-input.jinja",
        id="ph2",
        countries=[{"code": "SA", "dial_code": "+966", "name": "Saudi", "name_ar": "السعودية"}],
        country_code="+971",
    )
    if len(re.findall(r'data-dial-code="\+\d+"', custom)) != 1:
        problems.append("explicit countries list not honoured")
    if '+966' not in custom:
        problems.append("unknown country_code does not fall back to the first country")
    report("phone-input", not problems, f"violations={len(problems)}", "\n".join(problems[:6]))


def prop_footer():
    """Grouped footer links: one list per visible group, every link kept, labels escaped."""
    problems = []
    groups = [
        {"title": "Shop", "hide": False, "links": [{"title": "All", "url": "/products"}, {"title": "New", "url": "/products?sort=new"}]},
        {"title": "Help", "hide": False, "links": [{"title": "FAQ", "url": "/faqs"}]},
        {"title": "Hidden", "hide": True, "links": [{"title": "Gone", "url": "/nope"}]},
        {"title": "Empty", "hide": False, "links": []},
        {"title": "Unsafe", "hide": False, "links": [{"title": "<b>x</b>", "url": "/x"}]},
    ]
    ctx = base_ctx()
    ctx["settings"] = {
        "link_groups_items": groups,
        "about_us_about_us": "<p>about <b>us</b></p>",
        "contact_info_contact_info_title": "Reach us",
    }
    ctx["store"]["settings"]["contact"] = {"title": "Reach us", "email": "a@b.test"}
    html = render("footer.jinja", **ctx)
    if html.count('role="list"') != 4:
        problems.append(f"{html.count('role=\"list\"')} lists: want 3 visible groups + 1 contact list")
    for title in ("Shop", "Help", "Unsafe"):
        if title not in html:
            problems.append(f"group {title} missing")
    for title in ("Hidden", "Gone", "Empty"):
        if title in html:
            problems.append(f"group {title} rendered although hidden/empty")
    for href in ("/products", "/products?sort=new", "/faqs"):
        if f'href="{href}"' not in html:
            problems.append(f"link {href} lost (autoescape: {html.count(href)})")
    if "<b>x</b>" in html:
        problems.append("link title '<b>x</b>' rendered unescaped")
    if "&lt;b&gt;x&lt;/b&gt;" not in html:
        problems.append("link title not escaped at all")
    if "<p>about <b>us</b></p>" not in html:
        problems.append("about_us richtext is not passed through as HTML")
    if "Reach us" not in html or "a@b.test" not in html:
        problems.append("contact block missing")
    if "Contact us" in html:
        problems.append("configured contact title did not replace the default heading")
    plain = base_ctx()
    plain["settings"] = {"link_groups_items": groups}
    if "Contact us" not in render("footer.jinja", **plain):
        problems.append("contact heading lost its translated fallback")
    report("footer", not problems, f"violations={len(problems)}", "\n".join(problems[:6]))


def main():
    prop_settings_keys()
    prop_layout_gates()
    prop_footer()
    prop_404()
    prop_rating_stars()
    prop_main_nav()
    prop_mobile_drawer()
    prop_logo()
    prop_region_selector()
    prop_quantity_input()
    prop_disclosure()
    prop_breadcrumb()
    prop_pagination()
    prop_metafields()
    prop_phone_input()
    sys.exit(0)


if __name__ == "__main__":
    main()
