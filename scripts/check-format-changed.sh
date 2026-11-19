#!/usr/bin/env bash
#
# Check that every file this branch changes is formatted, without asking anyone to
# reformat the files they did not touch.
#
#   bash scripts/check-format-changed.sh [base-ref]     # base-ref defaults to origin/main
#
# Exit 0 = every changed file passes Prettier, or the branch changes none of the
#          formatted extensions.
# Exit 1 = Prettier named one or more changed files; run `npm run format` for them.
#
# CI runs this exact script, so a green local run means a green check.
set -uo pipefail

BASE="${1:-origin/main}"
[ "$#" -gt 0 ] && shift
EXTENSIONS=(css js json jinja html)

if ! git rev-parse --verify --quiet "$BASE" >/dev/null; then
  echo "base ref '$BASE' is not available; pass one, for example: $0 origin/main" >&2
  exit 2
fi

paths=()
for ext in "${EXTENSIONS[@]}"; do
  paths+=("*.${ext}")
done

mapfile -t changed < <(git diff --name-only --diff-filter=ACMR "$BASE"... "$@" -- "${paths[@]}")

if [ "${#changed[@]}" -eq 0 ]; then
  echo "format check: this branch changes no .css/.js/.json/.jinja/.html file"
  exit 0
fi

echo "format check: ${#changed[@]} changed file(s) against $BASE"
printf '  %s\n' "${changed[@]}"

if npx prettier --check "${changed[@]}"; then
  echo "format check: ok"
  exit 0
fi

echo
echo "format check: the files above are not formatted."
echo "Run 'npm run format' and commit the result, then run this script again."
exit 1
