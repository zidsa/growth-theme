"""Render home-page sections with plain Jinja2, the way vitrin's `{% template_components %}` does.

Why: the live storefront cannot show most sections. `templates/home.jinja` has no
`home.schema.json`, so with the template-settings DB unreachable vitrin renders `<main>` with
only the hidden <h1> and zero sections. This harness renders the REAL `templates/home.jinja`
and the REAL `sections/*.jinja` and wraps them in a minimal page shell that loads the real
`dist/theme.js` and `styles.css` (URLs taken from the live home page by journeys.py).

Run:  uv run --no-project --with jinja2 python -I render.py < spec.json > page.html
Spec: {"components": [{"template": "sections/hero.jinja", "settings": {...}, "section_id": "s1"}],
       "store": {...}, "dir": "rtl", "lang": "ar", "head_extra": "<link ...>", "body_extra": "<script ...>"}

Stubbed vitrin pieces (they are the platform's, not the theme's):
  * `{% template_components %}`: copies sdk/extensions.py TemplateComponentsTag: components of
    the session language in order, `display: false` skipped, `settings.order` = 1-based position,
    `sectionId` = the component's section_id.
  * `image_url(url, w=, q=, f=)`: "/__img/w=<w>,q=<q>,f=<f>/<url>" (vitrin: img CDN prefix + same
    option string + url); empty url -> "" (ASSUMPTION: vitrin's behaviour for empty is not read here).
  * `safeget` mirrors sdk/v2/filters.py:safeget (dotted path, dict/attr, default on None).
  * `url_for(name, ...)`: "/<name>" with list_categories -> /categories, list_products -> /products.
  * `vitrin:` includes render empty; `_()` returns the English msgid.
"""

import json
import sys
from pathlib import Path

from jinja2 import ChainableUndefined, ChoiceLoader, DictLoader, FileSystemLoader, PrefixLoader, nodes, select_autoescape
from jinja2.ext import Extension
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import Markup

import os

ROOT = Path(os.environ.get("ROOT") or Path(__file__).resolve().parents[3])


class Stub(ChainableUndefined):
    def __call__(self, *a, **k):
        return Stub()


class TemplateComponents(Extension):
    tags = {"template_components"}

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        ctx = nodes.ContextReference()
        call = self.call_method("_render", [ctx], lineno=lineno)
        return nodes.Output([call], lineno=lineno)

    def _render(self, context):
        comps = context.get("components") or []
        lang = (context.get("session") or {}).get("lang", "ar")
        if isinstance(comps, dict):
            comps = comps.get(lang) or next(iter(comps.values()), [])
        out = []
        order = 0
        for comp in comps:
            if comp.get("display") is False:
                continue
            order += 1
            settings = dict(comp.get("settings") or {})
            settings["order"] = order
            tpl = self.environment.get_template(comp["template"])
            ctxvars = dict(context.get_all(), settings=settings, sectionId=comp.get("section_id") or f"auto{order}")
            out.append(tpl.render(ctxvars))
        return Markup("".join(out))


def safeget(obj, path, default=None):
    for part in path.split("."):
        if obj is None:
            return default
        obj = obj.get(part) if isinstance(obj, dict) else getattr(obj, part, None)
    return default if obj is None else obj


def image_url(url, w=None, q=None, f=None, **_):
    if not url:
        return ""
    return f"/__img/w={w},q={q},f={f}/{url}"


URLS = {"list_categories": "/categories", "list_products": "/products", "home": "/"}


def make_env():
    # The layout is a one-block stub: layout.jinja itself is the layout group's, not this one's.
    layout = DictLoader({"layout.jinja": "<!--title:{% block title %}{% endblock %}-->{% block content %}{% endblock %}"})
    env = SandboxedEnvironment(
        loader=ChoiceLoader([layout, FileSystemLoader(str(ROOT)), PrefixLoader({"vitrin": DictLoader({})})]),
        undefined=Stub,
        autoescape=select_autoescape(),  # vitrin sdk/jinja.py: OFF for .jinja
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols", "jinja2.ext.i18n", TemplateComponents],
    )
    real_get = env.get_template

    def get_template(name, *a, **k):
        if isinstance(name, str) and name.startswith("vitrin:"):
            return env.from_string("")
        return real_get(name, *a, **k)

    env.get_template = get_template
    env.install_null_translations(newstyle=True)
    env.globals.update(
        _=lambda s, *a, **k: s,
        url_for=lambda name, *a, **k: URLS.get(name, "/" + name),
        safeget=safeget,
        image_url=image_url,
    )
    env.filters["asset_url"] = lambda v, *a, **k: "/__asset/" + str(v)
    for name in ("currency", "money", "format_price", "tojson_safe", "t", "translate"):
        env.filters.setdefault(name, lambda v, *a, **k: v)
    return env


def main():
    spec = json.load(sys.stdin)
    env = make_env()
    store = spec.get("store") or {"name": "Fixture Store", "settings": {}}
    store.setdefault("settings", {})
    session = {"lang": spec.get("lang", "ar"), "template": "home", "locale": {"language": {"direction": spec.get("dir", "rtl")}}}
    main_html = env.get_template("templates/home.jinja").render(
        store=store, session=session, components=spec["components"]
    )
    sys.stdout.write(
        f"""<!doctype html>
<html lang="{spec.get('lang', 'ar')}" dir="{spec.get('dir', 'rtl')}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{spec.get('head_extra', '')}</head>
<body data-template="home" class="min-h-dvh font-sans antialiased">
<main id="main">{main_html}</main>
{spec.get('body_extra', '')}
</body></html>"""
    )


if __name__ == "__main__":
    main()
