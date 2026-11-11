#!/usr/bin/env bash
# Formal checks for the growth-theme cart group.
#
#   ROOT=/path/to/checkout bash check.sh      # default: this script's repo root
#   bash check.sh --root /path/to/checkout    # same, as a flag
#   bash check.sh -v                          # keep the modules' console output
#
#     exit 0 = every property matched its recorded outcome (the FINDING lines are open
#              defects still reproducing — they are the record, not a pass)
#     exit 1 = an outcome changed (a finding was fixed, or a new break appeared)
#     exit 2 = the harness could not run or no longer describes the code (read, don't guess)
#
# Runs three suites: templates (jinja2), JavaScript (node), and the refresh race (TLC).
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ARG_ROOT=""
VERBOSE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ARG_ROOT="$2"; shift 2 ;;
    -v|--verbose) VERBOSE=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
ROOT="${ARG_ROOT:-${ROOT:-}}"
if [[ -z "$ROOT" ]]; then
  ROOT="$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || true)"
fi
[[ -n "$ROOT" ]] || ROOT="$(cd "$HERE/../../../.." && pwd)"
ROOT="$(cd "$ROOT" && pwd)"
if [[ ! -f "$ROOT/assets/js/cart/refresh.js" ]]; then
  echo "not a growth-theme checkout: $ROOT (set ROOT or pass --root)" >&2
  exit 2
fi

SYNC="$(sed -n 's/^sync-commit: //p' "$HERE/SKILL.md" | head -1)"
OUT="${FORMAL_CART_OUT:-$HOME/.cache/verify-growth-theme/formal-cart/$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"
echo "checkout: $ROOT"
echo "out:      $OUT"

# ── drift: covered files that moved since the recorded commit ──────────────
COVERED=(
  assets/js/cart
  assets/js/features/qty-input.js
  assets/js/features/gifting.js
  assets/js/features/loyalty-rewards.js
  components/cart
  templates/cart.jinja
)
if [[ -n "$SYNC" ]] && git -C "$ROOT" cat-file -e "$SYNC^{commit}" 2>/dev/null; then
  if ! git -C "$ROOT" diff --quiet "$SYNC" -- "${COVERED[@]}"; then
    echo "NOTE drift: covered files changed since sync-commit $SYNC — re-read them against the properties:"
    git -C "$ROOT" diff --stat "$SYNC" -- "${COVERED[@]}" | sed 's/^/  /'
  fi
else
  echo "NOTE drift: sync-commit '$SYNC' is not in this clone; cannot tell what changed since it."
fi

fail=0
broke=0  # exit 2: a harness crashed or TLC did not run (not a code change)

# harness <summary-regex> <cmd...>: exit 0 = matched, 1 with its summary line = CHANGED,
# anything else (a traceback, a throw, no summary) = the harness broke.
harness() {
  local summary=$1; shift
  local log rc
  log="$(mktemp)"
  "$@" 2>&1 | tee "$log"; rc=${PIPESTATUS[0]}
  if [[ $rc -eq 1 ]] && grep -qE "$summary" "$log"; then fail=1
  elif [[ $rc -ne 0 ]]; then echo "ERROR    harness exited $rc without its summary line: the harness broke"; broke=1; fi
  rm -f "$log"
}

# ── the model's constant, read from refresh.js ─────────────────────────────
FLAGS="$(python3 -I "$HERE/model/read_flags.py" "$ROOT")" || exit 2
echo "code flags:"; echo "$FLAGS" | sed 's/^/  /'
GUARD="$(echo "$FLAGS" | sed -n 's/^GuardDrops = //p')"

# ── 1. templates ───────────────────────────────────────────────────────────
echo
echo "== templates =="
harness '^template properties: [0-9]+ checks, [0-9]+ outcome\(s\) changed' \
  uv run --no-project --with jinja2 python -I "$HERE/harness/render_props.py" --root "$ROOT" ${VERBOSE:+--verbose}

# ── 2. JavaScript ──────────────────────────────────────────────────────────
echo
echo "== javascript =="
harness '^js properties: [0-9]+ outcome\(s\) changed' \
  node "$HERE/harness/js_props.mjs" --root "$ROOT" ${VERBOSE:+--verbose}

# ── 3. the refresh race (TLC) ──────────────────────────────────────────────
echo
echo "== refresh race (TLC) =="
TLC=""
if command -v tlc >/dev/null 2>&1; then
  TLC="tlc"
elif [[ -n "${TLA2TOOLS:-}" && -f "${TLA2TOOLS}" ]]; then
  TLC="java -cp $TLA2TOOLS tlc2.TLC"
elif [[ -f "$HOME/.local/share/tla/tla2tools.jar" ]]; then
  TLC="java -cp $HOME/.local/share/tla/tla2tools.jar tlc2.TLC"
fi
if [[ -z "$TLC" ]]; then
  echo "TLC not found. Install tla2tools.jar (~/.local/share/tla/tla2tools.jar) and a JDK 11+,"
  echo "or put a 'tlc' wrapper on PATH; then re-run. See SKILL.md > Refresh race." >&2
  exit 2
fi

# run_tlc <name> <GuardDrops> <expected: pass|Consistent>
run_tlc() {
  local name="$1" guard="$2" want="$3"
  local dir="$OUT/$name"
  mkdir -p "$dir"
  cp "$HERE/model/Refresh.tla" "$dir/"
  cat >"$dir/Refresh.cfg" <<CFG
SPECIFICATION Spec
CONSTANTS
  CartValues = {1, 2}
  GuardDrops = $guard
INVARIANTS TypeOK Consistent
CHECK_DEADLOCK FALSE
CFG
  ( cd "$dir" && $TLC -workers 2 -metadir "$dir/states" -config Refresh.cfg Refresh.tla ) >"$dir/tlc.out" 2>&1
  local got
  if grep -q "No error has been found" "$dir/tlc.out"; then
    got=pass
  else
    got="$(sed -n 's/^Error: Invariant \([A-Za-z]*\) is violated.*/\1/p' "$dir/tlc.out" | head -1)"
    got="${got:-tlc-error}"
  fi
  if [[ "$got" == tlc-error ]]; then
    echo "ERROR    $name: TLC did not run (see $dir/tlc.out)"; broke=1; return
  fi
  local states
  states="$(grep -oE '[0-9,]+ distinct states found' "$dir/tlc.out" | tail -1 || true)"
  if [[ "$got" != "$want" ]]; then
    echo "CHANGED  $name: recorded $want, now $got ($states) -> $dir/tlc.out"
    echo "         If the code was fixed, update the recorded outcome in the run_tlc call below, in SKILL.md, and the finding."
    fail=1
  elif [[ "$got" == pass ]]; then
    echo "ok       $name: Consistent holds ($states) -> $dir/tlc.out"
  else
    echo "ok       $name: $got violated as recorded ($states) -> $dir/tlc.out"
    echo "FINDING: a zidcart:updated that arrives while a refresh is in flight is dropped, so the"
    echo "         page keeps the cart from the earlier response and no further event repairs it."
    echo "         counterexample (server / dom / captured / inflight / pending):"
    awk '
      function flush() {
        if (line == "") return
        print line "  server=" v["server"] " dom=" v["dom"] " captured=" v["captured"] \
              " inflight=" v["inflight"] " pending=" v["pending"]
        delete v
      }
      /^State [0-9]+:/ { flush(); line = "  " $2; next }
      /^\/\\ [a-z]+ =/ { key = $2; val = $4; v[key] = val }
      END { flush() }
    ' "$dir/tlc.out" | head -12
  fi
}

# As the code is written: an event during a refresh is dropped. FINDING.
run_tlc as-coded "$GUARD" "Consistent"
# The shape of the fix: remember the event and refresh again after the swap. Must hold.
run_tlc queued "FALSE" "pass"

echo
if [[ $broke -ne 0 ]]; then
  echo "formal-cart: a harness broke — see ERROR lines above (exit 2)"
  exit 2
elif [[ $fail -eq 0 ]]; then
  echo "formal-cart: every property matches its recorded outcome"
else
  echo "formal-cart: outcomes changed — see CHANGED lines above"
fi
exit $fail
