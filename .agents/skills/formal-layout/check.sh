#!/usr/bin/env bash
#
# formal-layout: check every stated property of the layout group against its recorded outcome.
#
#   bash .agents/skills/formal-layout/check.sh            # checks this checkout
#   ROOT=/path/to/copy bash .agents/skills/formal-layout/check.sh
#
# Exit 0 = every property matched its recorded outcome (including the recorded findings).
# Exit 1 = `CHANGED <property>` for each property whose outcome differs. A property that
#          needs re-recording after an intended change is edited in the EXPECTED table below.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "$HERE/../../.." && pwd)}"
export ROOT
SYNC=2b1c67df1fb4f69637887f375d22099b90dafeb5

# Files this check describes; drift is reported for them (git diff --stat <sync-commit>).
COVERED=(
  layout.jinja header.jinja footer.jinja
  layout.schema.json header.schema.json footer.schema.json
  components/header-announcement-bar.jinja components/rating-stars.jinja
  components/header components/shared components/ui
  templates/404_not_found.jinja
  assets/js/data/countries.js assets/js/features/layout.js assets/js/layout-loyalty.js
  assets/js/lib/carousel.js assets/js/main.js
  assets/js/utils/customer-location.js assets/js/utils/escape.js
  assets/js/utils/events.js assets/js/utils/loading.js
)

EXPECTED="$(cat <<'EOF'
404-countdown ok violations=0
auth-redirect finding escapes=1,minimal=/..//attacker.test
breadcrumb finding labels-unescaped
carousel-bounds ok cases=14
country-table ok countries=199,defaults=18
disclosure ok violations=0
escape-attr ok cases=13163
events ok cases=11
footer finding violations=2
layout-gates ok violations=0
loading ok sequences=63
location-gate ok cases=curated+400+32
logo ok violations=0
loyalty-button ok cases=3
main-init ok cases=6
main-nav ok violations=0
metafields finding violations=1
mobile-drawer ok violations=0
pagination ok violations=0
phone-input ok violations=0
quantity-input ok violations=0
rating-stars ok violations=0
region-selector ok violations=0
settings-keys finding unknown=0,unread=gifting_cart_page
EOF
)"

for tool in uv node; do
  command -v "$tool" >/dev/null 2>&1 || { echo "missing $tool on PATH"; exit 2; }
done
[ -f "$ROOT/assets/js/main.js" ] || { echo "ROOT=$ROOT does not look like the growth-theme checkout"; exit 2; }

actual="$(mktemp)"
log="$(mktemp)"
trap 'rm -f "$actual" "$log"' EXIT

echo "formal-layout: ROOT=$ROOT"
echo "properties: $(wc -l <<< "$EXPECTED" | tr -d ' ') recorded | sync-commit $SYNC"
echo

{
  uv run --no-project --with jinja2 python -I "$HERE/props/templates.py"
  node "$HERE/props/node.mjs"
  uv run --no-project --with playwright python -I "$HERE/props/browser.py"
} >"$log" 2>&1

grep -E '^PROPERTY ' "$log" | sed -E 's/^PROPERTY +//' | sort >"$actual"

status=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  id="${line%% *}"
  got="$(grep -m1 "^$id " "$actual" || true)"
  if [ -z "$got" ]; then
    echo "CHANGED $id (missing from this run)"
    status=1
  elif [ "$got" != "$line" ]; then
    echo "CHANGED $id (recorded: ${line#"$id "}; now: ${got#"$id "})"
    status=1
  fi
done <<<"$EXPECTED"

while IFS= read -r line; do
  [ -n "$line" ] || continue
  id="${line%% *}"
  grep -q "^$id " <<<"$EXPECTED" || { echo "CHANGED $id (new property, not recorded)"; status=1; }
done <"$actual"

echo
grep -E '^(PROPERTY|    )' "$log" || true
grep -vE '^(PROPERTY|    |# )' "$log" | sed -n '1,20p' | sed 's/^/  tool: /'

if [ -z "$(grep -E '^PROPERTY ' "$log")" ]; then
  echo "no PROPERTY lines: the harness itself failed, see $log output above"
  status=1
fi

if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  if ! git -C "$ROOT" diff --quiet "$SYNC" -- "${COVERED[@]}" 2>/dev/null; then
    echo
    echo "NOTE drift: covered files changed since $SYNC — re-read the properties, then move sync-commit"
    git -C "$ROOT" diff --stat "$SYNC" -- "${COVERED[@]}"
  fi
fi

echo
if [ "$status" -eq 0 ]; then
  # Recorded "finding" outcomes are known product bugs (SKILL.md): say so loudly on a pass.
  grep -E '^[a-z0-9-]+ finding' <<<"$EXPECTED" | while read -r id _; do
    echo "FINDING: $id still reproduces (see SKILL.md)"
  done
  echo "outcome: all $(wc -l <<< "$EXPECTED" | tr -d ' ') properties matched their recorded outcome"
else
  echo "outcome: CHANGED — see the lines above"
fi
exit "$status"
