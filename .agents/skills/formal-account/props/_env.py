"""Shared harness for formal-account: the Jinja environment and the PROPERTY printer.

The environment mirrors vitrin's (sdk/jinja.py): `.jinja` templates render WITHOUT autoescape
(`select_autoescape()` only matches html/htm/xml), so `autoescape=False` here. Platform filters that
are not modelled pass their value through; `vitrin:` includes render empty; `_()` returns its msgid.
"""

import os
import sys
from pathlib import Path

from jinja2 import ChainableUndefined, ChoiceLoader, FileSystemLoader, nodes
from jinja2.ext import Extension
from jinja2.sandbox import SandboxedEnvironment

ROOT = Path(os.environ.get("ROOT", ".")).resolve()


def report(prop_id, violations, signature, ok_status="ok"):
    status = ok_status if not violations else "finding"
    print(f"PROPERTY {prop_id} {status} {signature}", flush=True)
    for line in violations[:8]:
        print(f"    {line}", flush=True)
    return status


def report_finding(prop_id, violations, signature):
    """A recorded finding: the counterexample must reproduce (`finding`), and `ok` means the bug is gone."""
    status = "finding" if violations else "ok"
    print(f"PROPERTY {prop_id} {status} {signature}", flush=True)
    for line in violations[:8]:
        print(f"    {line}", flush=True)
    return status


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


def make_env():
    env = SandboxedEnvironment(
        loader=ChoiceLoader([FileSystemLoader(str(ROOT))]),
        undefined=Stub,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols", "jinja2.ext.i18n", VitrinTagStubs],
    )
    real_get = env.get_template

    def get_template(name, *a, **k):
        if isinstance(name, str) and name.startswith("vitrin:"):
            return env.from_string("")
        return real_get(name, *a, **k)

    env.get_template = get_template
    env.install_null_translations(newstyle=True)
    env.globals.update(_=lambda s, *a, **k: s, url_for=lambda name, **k: "/" + name, safeget=lambda o, p, d=None: d)
    for name in ("currency", "money", "format_price", "asset_url", "image_url", "tojson_safe", "t", "translate"):
        env.filters.setdefault(name, lambda v, *a, **k: v)
    return env


def python_exe_note():
    return sys.version.split()[0]
