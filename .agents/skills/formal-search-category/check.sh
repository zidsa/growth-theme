#!/usr/bin/env bash
# Every formal-search-category property, one command.
#
#   ./check.sh              # check this worktree
#   ROOT=/path/to/copy ./check.sh
#
# Exit 0 = every property matched its recorded outcome in expected.txt.
# Exit 1 = one or more printed `CHANGED <property>` (and why).
# Exit 2 = TLC did not run (missing or crashed): no outcome, never read as PASS.
# Prints `NOTE drift` + the diff stat when a covered file changed after the
# sync commit recorded in SKILL.md.

set -u

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${ROOT:-$(cd "$HERE/../../.." && pwd)}
TLC=${TLC:-$(command -v tlc || echo tlc)}
WORK=$(mktemp -d "${TMPDIR:-/tmp}/formal-search-category.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

if [[ ! -f "$ROOT/templates/products.jinja" ]]; then
  echo "CHANGED harness: $ROOT is not a growth-theme checkout" >&2
  exit 1
fi

run() { # name, command...
  local name=$1; shift
  if ! "$@" >"$WORK/$name.log" 2>&1; then
    echo "! $name exited non-zero (see below)" >&2
  fi
  grep -E '^PROP [a-z0-9-]+ (PASS|FAIL|ERROR)$' "$WORK/$name.log" >>"$WORK/props.txt" || true
  grep -vE '^PROP [a-z0-9-]+ (PASS|FAIL|ERROR)$' "$WORK/$name.log" | sed 's/^/    /' >>"$WORK/detail.txt" || true
}

: >"$WORK/props.txt"
: >"$WORK/detail.txt"

run templates uv run --no-project --with jinja2 python -I "$HERE/properties/templates.py" --root "$ROOT"
run js        node "$HERE/properties/url_builder.mjs" --root "$ROOT"
run dom       uv run --no-project --with playwright python -I "$HERE/properties/browser.py" --root "$ROOT"

# The state machine: today's model must still violate the invariant, the
# coalescing fix must still satisfy it (so the invariant is not vacuous).
race() { # spec, cfg, expect-violation
  local spec=$1 cfg=$2 want=$3 out
  out=$("$TLC" -workers 1 -metadir "$WORK/tla-$(basename "$spec" .tla)" -config "$cfg" "$spec" 2>&1)
  echo "$out" >>"$WORK/tla.log"
  if grep -q "Invariant Consistent is violated" <<<"$out"; then
    echo "violated"
  elif grep -q "No error has been found" <<<"$out"; then
    echo "holds"
  else
    echo "error"
  fi
}
cd "$HERE/properties" || exit 1
today=$(race filter_race.tla filter_race.cfg violated)
fixed=$(race filter_race_fixed.tla filter_race_fixed.cfg holds)
cd - >/dev/null || exit 1
echo "PROP filter-request-order $([[ $today == violated ]] && echo FAIL || echo PASS)" >>"$WORK/props.txt"
echo "PROP filter-request-order-model-sanity $([[ $fixed == holds ]] && echo PASS || echo FAIL)" >>"$WORK/props.txt"
if [[ $today == error || $fixed == error ]]; then
  # A TLC that did not run proves nothing either way: never read it as PASS or FAIL.
  echo "ERROR: tlc did not finish cleanly (today: $today, fixed: $fixed); tail of its log:" >&2
  tail -20 "$WORK/tla.log" >&2
  exit 2
fi

# ── compare with the recorded outcomes ─────────────────────────────────────
changed=0
while read -r id want; do
  [[ -z ${id:-} || $id == \#* ]] && continue
  got=$(awk -v id="$id" '$2 == id {print $3}' "$WORK/props.txt" | tail -1)
  if [[ -z $got ]]; then
    echo "CHANGED $id (no result: the check did not run)"
    changed=1
  elif [[ $got != "$want" ]]; then
    echo "CHANGED $id (recorded $want, now $got)"
    changed=1
  fi
done <"$HERE/expected.txt"

while read -r _ id _; do
  grep -qE "^$id " "$HERE/expected.txt" || {
    echo "CHANGED $id (not in expected.txt)"
    changed=1
  }
done <"$WORK/props.txt"

# ── drift: has anything covered by these properties moved since the sync commit? ──
SYNC=$(sed -n 's/^sync-commit: *//p' "$HERE/SKILL.md" | head -1)
if [[ -n ${SYNC:-} ]] && git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  stat=$(git -C "$ROOT" diff --stat "$SYNC" -- \
    templates/products.jinja templates/category.jinja templates/brand.jinja \
    templates/categories.jinja templates/brands.jinja \
    components/categories components/brands \
    assets/js/features/search.js assets/js/features/price-slider.js \
    assets/js/features/product-filter.js 2>/dev/null)
  if [[ -n $stat ]]; then
    echo "NOTE drift: covered files changed since $SYNC"
    echo "$stat" | sed 's/^/    /'
    echo "    rerun the break proof (SKILL.md) before moving sync-commit forward"
  fi
fi

if [[ $changed -ne 0 ]]; then
  echo
  echo "detail:"
  sed 's/^/  /' "$WORK/detail.txt" | head -60
  exit 1
fi

# Recorded FAILs are known product bugs (SKILL.md "Findings"): say so loudly on a pass.
while read -r id want; do
  [[ -z ${id:-} || $id == \#* ]] && continue
  [[ $want == FAIL && $id != *-model-sanity ]] && echo "FINDING: $id still reproduces (see SKILL.md)"
done <"$HERE/expected.txt"
echo "ok: every property matched expected.txt"
