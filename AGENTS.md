
## Verify before opening a PR

Both verifications must run, and pass, before you open a PR. Skills live in
`.agents/skills/` (`.claude/`, `.codex/`, `.cursor/` and `.hermes/` skills
folders link to the same copies).

1. **Verification skill** for every feature group your change touches:
   `verify-account`, `verify-blog`, `verify-cart`, `verify-content-pages`,
   `verify-home-sections`, `verify-layout`, `verify-product`,
   `verify-search-category`. Launch vitrin rendering this checkout once with the
   base skill `verify-growth-theme`, then drive that group's journeys:

   ```bash
   npm ci && npm run build        # theme.js, cart-controller.js and styles.css
   npx playwright test            # the repo's spec harness (tests/*.spec.js)
   S=.agents/skills/verify-growth-theme/scripts
   export VITRIN_API_TOKEN="$(kubectl -n testing get secret vitrin-secret -o jsonpath='{.data.API_TOKEN}' | base64 -d)"
   $S/storefront.sh up && $S/storefront.sh doctor   # must end "doctor: healthy"
   uv run --no-project --with playwright python -I $S/drive.py --list   # every journey
   uv run --no-project --with playwright python -I $S/drive.py <journey>
   $S/storefront.sh down
   ```

2. **Formal verification skill** for the same groups: `formal-account`,
   `formal-blog`, `formal-cart`, `formal-content-pages`, `formal-home-sections`,
   `formal-layout`, `formal-product`, `formal-search-category`:

   ```bash
   .agents/skills/formal-<group>/check.sh
   ```

   `formal-product` drives part of its properties in the browser: keep the
   storefront up while it runs (exit 2 `BLOCKED` means it was down, not a pass). Any
   `check.sh` exit 2 means the harness or TLC did not run: not a pass.

Pass means the recorded outcome still holds: `npx playwright test` passes, every
journey you ran exits 0 and every `check.sh` exits 0. A journey that replays a
known product bug is listed in its skill's `KNOWN` table (`journeys.py`); it
exits 0 with a `FINDING` line only while it fails exactly the recorded checks,
and exits 1 with `CHANGED` on any other failure, a crash, or once the bug is
fixed. Each formal skill records known product bugs too: its exit 0 prints `FINDING` lines and means those bugs still reproduce, so
do not read it as the property holding. A `check.sh` that exits 1 means a
recorded outcome changed (a fix, or a new break): read that skill's section on
telling a real bug from a modelling error, then update the model and its
recorded outcome or fix the code. If you change a group's behavior, update its
skills in the same PR.
