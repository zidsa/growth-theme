#!/usr/bin/env python3
"""Read the refresh model's only constant from assets/js/cart/refresh.js.

The question this answers: does the code drop a `zidcart:updated` that arrives while a
refresh is in flight, or remember it? The answer comes from live code, never from words:
comments are stripped first, and each answer needs an exact statement shape.

- TRUE (drops): `refreshCartPage` starts with `if (isRefreshing) return; isRefreshing = true;`.
- FALSE (remembers): a pending flag is set to `true` and a `finally` re-runs
  `refreshCartPage` under that same flag.
- Anything else (guard commented out, wrapped, moved, weakened): the model no longer
  describes the file, so exit 2 instead of guessing.

Usage: python3 -I read_flags.py <theme root>
Prints `GuardDrops = TRUE|FALSE` on stdout; exit 2 when neither shape is found.
"""

import re
import sys
from pathlib import Path

COMMENTS = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
FLAG = r"(pendingRefresh|needsRefresh|isQueued|refreshQueued)"
DROP = re.compile(
    r"function\s+refreshCartPage\s*\(\s*\)\s*\{\s*if\s*\(\s*isRefreshing\s*\)\s*return\s*;\s*isRefreshing\s*=\s*true\s*;"
)
SET = re.compile(r"\b" + FLAG + r"\s*=\s*true\b")
RERUN = re.compile(r"finally\s*\{[^}]*?if\s*\(\s*" + FLAG + r"\s*\)\s*\{[^}]*?refreshCartPage\s*\(")
EVENT = re.compile(r"""addEventListener\(\s*["']zidcart:updated["']""")
FETCH = re.compile(r"fetch\(\s*(window\.)?location\.href")


def main() -> int:
    path = Path(sys.argv[1]).resolve() / "assets/js/cart/refresh.js"
    code = COMMENTS.sub("", path.read_text(encoding="utf-8"))
    if not (EVENT.search(code) and FETCH.search(code)):
        print("refresh.js lost the zidcart:updated listener or the page fetch: re-read model/Refresh.tla", file=sys.stderr)
        return 2
    pending, rerun = SET.search(code), RERUN.search(code)
    if pending and rerun and pending.group(1) == rerun.group(1):
        print("GuardDrops = FALSE")
        return 0
    if DROP.search(code):
        print("GuardDrops = TRUE")
        return 0
    print(
        "refresh.js: refreshCartPage no longer starts with `if (isRefreshing) return; isRefreshing = true;`"
        " and has no queued re-run: re-read it against model/Refresh.tla",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
