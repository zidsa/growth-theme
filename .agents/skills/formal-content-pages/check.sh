#!/usr/bin/env bash
# Formal checks for the growth-theme content-pages group (faqs, custom pages, shipping & payment).
#
#   ROOT=/path/to/checkout bash check.sh      # default: this script's repo root
#   bash check.sh --root /path/to/checkout    # same, as a flag
#
#     exit 0 = every property matched its recorded outcome (FINDING lines are open defects
#              still reproducing: the record, not a pass)
#     exit 1 = an outcome changed (CHANGED <property>): a finding was fixed or a new break appeared
#     exit 2 = the harness could not run
#
# Two suites: templates (plain Jinja2) and browser JS (headless Chrome via Playwright, no server).
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1

HERE="$(cd "$(dirname "$0")" && pwd)"
ARG_ROOT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ARG_ROOT="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
ROOT="${ARG_ROOT:-${ROOT:-}}"
[[ -n "$ROOT" ]] || ROOT="$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$ROOT" ]] || ROOT="$(cd "$HERE/../../.." && pwd)"
ROOT="$(cd "$ROOT" && pwd)"
if [[ ! -f "$ROOT/assets/js/shipping-payment.js" ]]; then
  echo "not a growth-theme checkout: $ROOT (set ROOT or pass --root)" >&2
  exit 2
fi

SYNC="$(sed -n 's/^sync-commit: //p' "$HERE/SKILL.md" | head -1)"
# Run output goes under ~/.cache, never into the skill directory.
OUT="${FORMAL_CONTENT_PAGES_OUT:-$HOME/.cache/formal-content-pages/$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"
echo "checkout: $ROOT"
echo "out:      $OUT"

COVERED=(
  components/shipping-payment
  assets/js/shipping-payment.js
  templates/faqs.jinja
  templates/page.jinja
  templates/shipping_payment.jinja
)
if [[ -n "$SYNC" ]] && git -C "$ROOT" cat-file -e "$SYNC^{commit}" 2>/dev/null; then
  if ! git -C "$ROOT" diff --quiet "$SYNC" -- "${COVERED[@]}"; then
    echo "NOTE drift: covered files changed since sync-commit $SYNC; re-read them against the properties:"
    git -C "$ROOT" diff --stat "$SYNC" -- "${COVERED[@]}" | sed 's/^/  /'
  fi
else
  echo "NOTE drift: sync-commit '$SYNC' is not in this clone; cannot tell what changed since it."
fi

fail=0
rc=0

echo
echo "== templates =="
uv run --no-project --with jinja2 python -I "$HERE/harness/render_props.py" --root "$ROOT"
rc=$?
if [[ $rc -eq 2 ]]; then exit 2; elif [[ $rc -ne 0 ]]; then fail=1; fi

echo
echo "== javascript (real assets/js/shipping-payment.js in headless Chrome) =="
uv run --no-project --with playwright --with jinja2 python -I "$HERE/harness/dom_props.py" --root "$ROOT" --out "$OUT/dom"
rc=$?
if [[ $rc -eq 2 ]]; then exit 2; elif [[ $rc -ne 0 ]]; then fail=1; fi

echo
if [[ $fail -eq 0 ]]; then
  echo "formal-content-pages: every property matches its recorded outcome"
else
  echo "formal-content-pages: outcomes changed; see CHANGED lines above"
fi
exit $fail
