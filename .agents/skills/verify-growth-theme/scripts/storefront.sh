#!/usr/bin/env bash
# Run Vitrin against THIS growth-theme checkout and serve its built assets locally.
# Usage: storefront.sh up|doctor|down|logs [n]
# Env (all optional): PORT (8995), ASSET_PORT (PORT+1), VITRIN_ROOT, STORE_HOST,
#   API_BASE_URL, VITRIN_API_TOKEN, VERIFY_HOME.
set -euo pipefail

THEME="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
# Sibling checkouts sit next to the main growth-theme checkout, also from a worktree.
ZID_ROOT="$(cd "$THEME" && cd "$(git rev-parse --path-format=absolute --git-common-dir)/../.." && pwd)"
VITRIN_ROOT="${VITRIN_ROOT:-$ZID_ROOT/vitrin}"
PORT="${PORT:-8995}"
ASSET_PORT="${ASSET_PORT:-$((PORT + 1))}"
STORE_HOST="${STORE_HOST:-my-store-2.zidtest.com}"
API_BASE_URL="${API_BASE_URL:-https://testing-api.zid.sa/}"
VERIFY_HOME="${VERIFY_HOME:-$HOME/.cache/verify-growth-theme}"
STATE="$VERIFY_HOME/run-$PORT"
URL="http://127.0.0.1:$PORT"
ASSET_URL="http://127.0.0.1:$ASSET_PORT"
# Own venv per run dir, so the vitrin checkout's .venv is never rebuilt or reused.
export UV_PROJECT_ENVIRONMENT="$STATE/venv"
# Apple Silicon: vitrin's .python-version can resolve to an x86_64 (Rosetta) Python,
# whose venv then fails to load arm64 wheels. Pin a native interpreter.
if [[ $(uname -s) == Darwin && $(uname -m) == arm64 && -z ${UV_PYTHON:-} ]]; then
  export UV_PYTHON="cpython-3.14-macos-aarch64-none"
fi

alive() { [[ -f $1 ]] && kill -0 "$(cat "$1")" 2>/dev/null; }
listener_pid() { lsof -nP -t -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -1 || true; }
# A process and its descendants: the uv wrapper forks the real uvicorn.
tree() { local p=$1; echo "$p"; for c in $(pgrep -P "$p" 2>/dev/null); do tree "$c"; done; }

start_bg() { # start_bg <pidfile> <log> <dir> <cmd...>: new session, pid recorded by the child itself
  local pidfile=$1 log=$2 dir=$3; shift 3
  (cd "$dir" && exec python3 -I -c 'import os,sys; os.setsid(); open(sys.argv[1],"w").write(str(os.getpid())); os.execvp(sys.argv[2], sys.argv[2:])' \
    "$pidfile" "$@" >"$log" 2>&1 </dev/null) &
  for _ in $(seq 1 25); do [[ -s $pidfile ]] && return; sleep 0.2; done
}

up() {
  if alive "$STATE/vitrin.pid" && alive "$STATE/assets.pid"; then echo "already running: $URL (pid $(cat "$STATE/vitrin.pid"))"; return; fi
  # A half-alive run (one of the two servers died) is restarted whole.
  if alive "$STATE/vitrin.pid" || alive "$STATE/assets.pid"; then down; fi
  for p in "$PORT" "$ASSET_PORT"; do
    [[ -z $(listener_pid "$p") ]] || { echo "port $p is taken by a process this script did not start; set PORT=<free>" >&2; exit 1; }
  done
  case "$API_BASE_URL" in *api.zid.sa*) [[ $API_BASE_URL == *testing-api* ]] || { echo "refusing a production API_BASE_URL" >&2; exit 1; } ;; esac
  [[ -f $VITRIN_ROOT/vitrin/main.py ]] || { echo "vitrin checkout not found at $VITRIN_ROOT (set VITRIN_ROOT)" >&2; exit 1; }
  [[ -f $THEME/assets/dist/theme.js && -f $THEME/assets/dist/cart-controller.js && -f $THEME/assets/styles.css ]] || {
    echo "built bundle missing: run 'npm ci && npm run build' in $THEME first" >&2; exit 1; }
  mkdir -p "$STATE"
  # doctor checks the vitrin process against the checkout THIS run used, not the env default.
  echo "$VITRIN_ROOT" >"$STATE/vitrin.root"
  (cd "$VITRIN_ROOT" && uv sync --frozen -q)
  # asset_url renders <AWS_S3_CUSTOM_DOMAIN>/<theme hash>/<path>; the asset server drops the
  # hash segment and serves $THEME/assets, so the browser loads this checkout's bundle.
  start_bg "$STATE/assets.pid" "$STATE/assets.log" "$THEME" \
    python3 -I "$THEME/.agents/skills/verify-growth-theme/scripts/asset_server.py" "$ASSET_PORT" "$THEME/assets"
  (
    # SECRET_KEY is the public dev Fernet key from vitrin's .env.example, not a secret.
    # Templates DB points at a closed port: testing's theme settings are out of reach, so
    # pages render this theme's schema defaults.
    export APP_ENV=development API_BASE_URL HOST_OVERRIDE="$STORE_HOST" \
      USE_DEVELOPMENT_THEME=True DEVELOPMENT_THEME_ROOT="$THEME" CACHE_ENABLED=False \
      AWS_S3_CUSTOM_DOMAIN="$ASSET_URL" \
      REDIS_HOST=127.0.0.1 REDIS_PORT=6379 REDIS_DB=14 \
      TEMPLATES_DB_HOST=127.0.0.1 TEMPLATES_DB_PORT=1 TEMPLATES_DB_DATABASE=vitrin TEMPLATES_DB_USER=verify \
      SECRET_KEY=UwwfcCnNfxLDwcsl8Vi943ZqiDpnsU-lmE9mXKtwT8g= \
      TURNSTILE_MODE=off SSO_ENABLED=False SENTRY_DSN=
    [[ -n ${VITRIN_API_TOKEN:-} ]] && export API_TOKEN="$VITRIN_API_TOKEN"
    start_bg "$STATE/vitrin.pid" "$STATE/server.log" "$VITRIN_ROOT" \
      uv run --frozen uvicorn vitrin.main:app --host 127.0.0.1 --port "$PORT"
  )
  for _ in $(seq 1 90); do
    if curl -sf -o /dev/null "$URL/healthz" && [[ $(curl -s -o /dev/null -w '%{http_code}' "$URL/") == 200 ]]; then
      echo "ready: $URL (theme $THEME @ $(git -C "$THEME" rev-parse --short HEAD), assets $ASSET_URL, store $STORE_HOST)"; return
    fi
    alive "$STATE/vitrin.pid" || { echo "vitrin exited; tail of $STATE/server.log:" >&2; tail -25 "$STATE/server.log" >&2; exit 1; }
    sleep 1
  done
  echo "not ready after 90s; see $STATE/server.log" >&2; exit 1
}

doctor() {
  local ok=1 pid lp
  for role in vitrin:$PORT assets:$ASSET_PORT; do
    local name=${role%%:*} port=${role##*:}
    if alive "$STATE/$name.pid"; then
      pid=$(cat "$STATE/$name.pid"); lp=$(listener_pid "$port")
      if [[ -n $lp ]] && tree "$pid" | grep -qx "$lp"; then echo "ok   $name: pid $pid owns :$port"
      else echo "FAIL $name: :$port listener '${lp:-none}' is not ours (pid $pid)"; ok=0; fi
    else echo "FAIL $name: no live pid in $STATE/$name.pid"; ok=0; fi
  done
  local vroot="$VITRIN_ROOT" vcwd="" vlp; vlp=$(listener_pid "$PORT")
  [[ -s $STATE/vitrin.root ]] && vroot=$(cat "$STATE/vitrin.root")
  [[ -n $vlp ]] && vcwd=$(lsof -a -p "$vlp" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1 || true)
  [[ $vcwd == "$vroot" ]] && echo "ok   vitrin checkout: $vcwd @ $(git -C "$vroot" rev-parse --short HEAD)" \
    || { echo "FAIL vitrin checkout: '$vcwd', expected $vroot (the one 'up' started)"; ok=0; }
  curl -sf -o /dev/null "$URL/healthz" && echo "ok   /healthz 200" || { echo "FAIL /healthz"; ok=0; }
  local html; html=$(curl -s "$URL/" || true)
  if grep -q "$ASSET_URL/[^\"]*/dist/theme.js" <<<"$html"; then echo "ok   home renders and points dist/theme.js at $ASSET_URL"
  else echo "FAIL home page does not load theme.js from $ASSET_URL (store lookup, upstream or theme broken; see logs)"; ok=0; fi
  if cmp -s <(curl -s "$ASSET_URL/x/dist/theme.js") "$THEME/assets/dist/theme.js"; then echo "ok   served theme.js == $THEME/assets/dist/theme.js"
  else echo "FAIL served theme.js differs from this checkout's build"; ok=0; fi
  # Without VITRIN_API_TOKEN the upstream API answers 401 and vitrin sends every product page to login.
  local slug code
  slug=$(curl -s "http://127.0.0.1:$PORT/api/v1/products" | python3 -Ic 'import json,sys; d=json.load(sys.stdin); r=d.get("results",d) if isinstance(d,dict) else d; print(r[0]["slug"])' 2>/dev/null || true)
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/products/$slug" || true)
  [[ -n $slug && $code == 200 ]] && echo "ok   product page 200 (upstream API token accepted)" \
    || { echo "FAIL product page '$slug' -> $code (307 to login = VITRIN_API_TOKEN missing at 'up')"; ok=0; }
  if [[ -f $THEME/assets/styles.css ]] && cmp -s <(curl -s "$ASSET_URL/x/styles.css") "$THEME/assets/styles.css"; then echo "ok   served styles.css == $THEME/assets/styles.css"
  else echo "FAIL styles.css missing or not served (run 'npm run build')"; ok=0; fi
  ((ok)) && echo "doctor: healthy" || { echo "doctor: NOT healthy"; exit 1; }
}

down() {
  for name in vitrin assets; do
    local f="$STATE/$name.pid"
    if alive "$f"; then
      local pid; pid=$(cat "$f")
      kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
      for _ in $(seq 1 10); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
      kill -KILL -- "-$pid" 2>/dev/null || true
      echo "stopped $name (session $pid)"
    else echo "$name: nothing running"; fi
    rm -f "$f"
  done
  rm -f "$STATE/vitrin.root"
  # Logs stay in $STATE; evidence directories are never touched here.
}

case "${1:-}" in
  up) up ;; doctor) doctor ;; down) down ;; logs) tail -n "${2:-50}" "$STATE/server.log" ;;
  *) echo "usage: $0 up|doctor|down|logs [n]" >&2; exit 2 ;;
esac
