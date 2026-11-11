#!/usr/bin/env bash
# formal-product: run every property and compare it with its recorded outcome.
#
#   ROOT=/path/to/growth-theme BASE=http://127.0.0.1:8995 bash check.sh
#
# Exit 0  every property matched its recorded outcome (findings still reproduce)
# Exit 1  CHANGED <property> on stdout — read SKILL.md before touching anything
# Exit 2  BLOCKED: the storefront is not reachable, so P2-P8 could not run

set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=${ROOT:-$(cd "$HERE/../../.." && pwd)}
BASE=${BASE:-http://127.0.0.1:8995}
SYNC=$(sed -n 's/^sync-commit: *//p' "$HERE/SKILL.md" | head -1)

COVERED=(
  assets/js/time-ago.js
  assets/js/question-form.js
  assets/js/product/gallery.js
  assets/js/product/lightbox.js
  assets/js/product/variants.js
  assets/js/product/sticky-bar.js
  assets/js/product/quick-view.js
  assets/js/features/bundle-offers.js
  assets/js/features/notify-me.js
  templates/product.jinja
  templates/reviews.jinja
  templates/questions.jinja
  components/products/product-card.jinja
  components/products/product-gallery.jinja
  components/products/product-reviews.jinja
  components/products/review-card.jinja
  components/products/product-questions.jinja
  components/products/question-form.jinja
  components/products/notify-me-dialog.jinja
  components/products/quick-view-modal.jinja
  components/products/sticky-product-actions.jinja
  components/products/product-options.jinja
  components/products/product-variant.jinja
)

if [ -n "$SYNC" ] && git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  if ! git -C "$ROOT" diff --quiet "$SYNC" -- "${COVERED[@]}" 2>/dev/null; then
    echo "NOTE drift: covered files changed since $SYNC"
    git -C "$ROOT" diff --stat "$SYNC" -- "${COVERED[@]}"
    echo
  fi
fi

status=0

node "$HERE/props/time_ago.mjs" --root "$ROOT" || status=1

uv run --no-project --with jinja2 python -I "$HERE/props/render_contracts.py" --root "$ROOT" || status=1

BUNDLE_ARGS=()
[ -f "$ROOT/assets/dist/theme.js" ] && BUNDLE_ARGS=(--bundle "$ROOT/assets/dist/theme.js")
uv run --no-project --with playwright python -I "$HERE/props/dom_states.py" --base "$BASE" ${BUNDLE_ARGS[@]+"${BUNDLE_ARGS[@]}"}
browser_status=$?
case "$browser_status" in
  0) ;;
  2) [ "$status" -eq 0 ] && status=2 ;;
  *) status=1 ;;
esac

if [ "$status" -eq 2 ]; then
  echo
  echo "BLOCKED: start the storefront first (verify-growth-theme: storefront.sh up) and rerun."
fi

exit "$status"
