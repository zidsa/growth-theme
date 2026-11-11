#!/usr/bin/env bash
# formal-blog: one command. ROOT defaults to the repo root containing this script.
# exit 0 = every property matched its recorded outcome (props/expected.txt); exit 1 = CHANGED <property>.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "$HERE/../../.." && pwd)}"; export ROOT
SYNC=2b1c67df1fb4f69637887f375d22099b90dafeb5
COVERED="templates/blog.jinja templates/blogs.jinja components/blogs components/ui/pagination.jinja components/ui/breadcrumb.jinja"
OUT="$(mktemp)"; trap 'rm -f "$OUT"' EXIT
command -v uv >/dev/null || { echo "ERROR uv not found"; exit 1; }
(cd "$HERE" && uv run --no-project --with jinja2 python -I props/templates.py) >"$OUT" 2>&1
(cd "$HERE" && uv run --no-project --with jinja2 --with playwright python -I props/browser.py) >>"$OUT" 2>&1
grep -E '^(PROPERTY|    )' "$OUT" | grep -E '^PROPERTY' >"$OUT.got"
grep -vE '^(PROPERTY|    )' "$OUT" | sed 's/^/HARNESS /'
rc=0
while read -r _ id status sig; do
  want="$(grep -E "^PROPERTY $id " "$HERE/props/expected.txt" || true)"
  if [ "$want" != "PROPERTY $id $status $sig" ]; then echo "CHANGED $id: got '$status $sig', recorded '${want#PROPERTY $id }'"; grep -A4 -E "^PROPERTY $id " "$OUT" | grep '^    ' ; rc=1; fi
  case "$status" in finding) echo "FINDING: $id ($sig) still reproduces (recorded)";; esac
done <"$OUT.got"
for id in $(awk '{print $2}' "$HERE/props/expected.txt"); do grep -qE "^PROPERTY $id " "$OUT.got" || { echo "CHANGED $id: property did not run"; rc=1; }; done
rm -f "$OUT.got"
if ! git -C "$ROOT" diff --quiet "$SYNC" -- $COVERED 2>/dev/null; then echo "NOTE drift: covered files changed since $SYNC"; git -C "$ROOT" diff --stat "$SYNC" -- $COVERED; fi
[ $rc = 0 ] && echo "formal-blog: all $(wc -l <"$HERE/props/expected.txt" | tr -d ' ') properties match their recorded outcome"
exit $rc
