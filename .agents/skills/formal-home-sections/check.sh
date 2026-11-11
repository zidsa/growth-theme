#!/usr/bin/env bash
# formal-home-sections: one command. ROOT = repo to check (default: this repo). Exit 0 = every
# property matched expected.txt (a recorded finding that still reproduces counts as matched).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "$HERE/../../.." && pwd)}"; export ROOT
SYNC=2b1c67df1fb4f69637887f375d22099b90dafeb5
OUT="$(mktemp)"; trap 'rm -f "$OUT"' EXIT

uv run --no-project --with jinja2 python -I "$HERE/props.py" >"$OUT" 2>"$OUT.err" || { cat "$OUT.err"; echo "CHANGED harness-error (props.py)"; rm -f "$OUT.err"; exit 1; }
rm -f "$OUT.err"
node "$HERE/countdown.mjs" >>"$OUT" 2>&1 || { cat "$OUT"; echo "CHANGED harness-error (countdown.mjs)"; exit 1; }

cat "$OUT" | grep -v '^RESULT '
status=0
while read -r id outcome n; do
  [ -z "$id" ] && continue
  got="$(grep "^RESULT $id " "$OUT" | cut -d' ' -f3-)"
  want="$outcome${n:+ $n}"
  if [ "$got" != "$want" ]; then echo "CHANGED $id (recorded: $want, now: ${got:-missing})"; status=1
  elif [ "$outcome" = finding ]; then echo "FINDING: $id still reproduces ($want)"
  else echo "OK $id holds"; fi
done <"$HERE/expected.txt"

COVERED="templates/home.jinja sections components/products/product-card.jinja components/products/products-carousel.jinja assets/js/lib/carousel.js"
if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  # shellcheck disable=SC2086
  D="$(git -C "$ROOT" diff --stat "$SYNC" -- $COVERED 2>/dev/null)"
  if [ -n "$D" ]; then echo "NOTE drift: covered files changed since sync-commit $SYNC"; echo "$D"; fi
fi
[ $status -eq 0 ] && echo "check: all properties match expected.txt"
exit $status
