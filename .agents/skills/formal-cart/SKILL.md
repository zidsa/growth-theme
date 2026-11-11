---
name: formal-cart
description: Verify the growth-theme cart group — totals, coupon, gifting, loyalty, badge, quantity, refresh — against stated promises, with property checks on the real .jinja and .js files and a TLA+ model of the refresh race. Use when a change touches the cart page or its JS, or before believing a cart fix.
sync-commit: 2b1c67df1fb4f69637887f375d22099b90dafeb5
---

# formal-cart

`verify-cart` drives the cart in a browser and shows what a shopper gets. This skill
states the cart's promises as properties and checks every case in a stated scope: every
totals shape, every coupon/quantity sequence up to a bound, and every order of the
refresh events. It runs offline in ~15 s and prints one line per property.

```bash
bash .agents/skills/formal-cart/check.sh                 # this checkout
ROOT=/path/to/checkout bash .agents/skills/formal-cart/check.sh
```

Exit 0 means every property still has the outcome recorded below — including the seven
recorded as **violations** (five distinct defects), which are open, not passes. Exit 1 with a `CHANGED`
line means an outcome moved: a finding was fixed, or a new break appeared. Exit 2 means
the harness or the model no longer describes the code — read the code, do not guess.

## The properties

Tools: **J** = plain-Jinja2 render of the real template (`harness/render_props.py`);
**N** = Node, stdlib only, importing the real module with a fake browser
(`harness/js_props.mjs`); **T** = TLC over `model/Refresh.tla`. Jinja is chosen for
template invariants because the template *is* the code under test; Node for the cart JS
because the modules run unchanged with a small DOM stand-in; TLA+ for the refresh
because the harm comes from event order, not from one input.

Template properties:

- **CartPageShape** (J) — Promise: an empty cart renders only the empty state, a filled
  cart renders one product list, one totals block and a checkout link, and the page
  always loads `dist/cart-controller.js` once and calls `CartPage.init`. Harm: a shopper
  with nothing in the cart gets an order summary and a checkout button, or a full cart
  loses its totals and cannot check out.
- **SectionGating** (J) — Promise: the coupon form, gift-order block, loyalty block and
  gift-card block each appear exactly when the store setting allows it and the cart has
  lines; a closed store shows the disabled notice instead of the checkout link. Harm: a
  merchant switches coupons off and shoppers still see the field, or a closed store
  still takes them to checkout.
- **TotalsRows** (J) — Promise: every `cart.totals` entry reaches the summary, the
  `total` row is last and the only bold one, and the items count rides the `sub_totals`
  row only. Harm: a summary that drops VAT or buries the total misstates what the
  shopper will pay.
- **DiscountSign** (J) — Promise: a discount renders with exactly one leading `-`.
  Harm: `--22.00` reads as a surcharge.
- **CouponSectionState** (J) — Promise: an applied coupon renders the chip and remove
  button and no form; otherwise the form renders with its submit disabled. Harm: the
  shopper cannot remove a coupon, or can submit an empty one.
- **ProgressWidth** (J) — Promise: the free-shipping bar's width and truck offset stay
  inside `[0,100]`. Harm: the bar and truck run off the card, the shopper cannot tell
  how close they are to free shipping. **FINDING 3.**
- **CartTextEscaping** (J) — Promise: a string the cart API supplies is written into the
  page as text. Harm: a coupon or gift-card code containing `<` is truncated on screen,
  and the same interpolation is an XSS sink for any field that becomes user-typed.
  **FINDING 5.**

JavaScript properties:

- **TotalsRows** (N, `updateCartTotals`) — same promise and harm as above, on the AJAX
  path the platform uses to rewrite the summary.
- **DiscountSign** (N, `formatDiscount` inside `updateCartTotals`) — same promise.
- **TotalsTextEscaping** (N, `updateCartTotals`) — same promise as CartTextEscaping on
  the JS path. **FINDING 5.**
- **ProgressWidth** (N, `updateFreeShippingProgress`) — same promise as above; the JS
  twin sets the same unclamped width. **FINDING 3.**
- **QuantityBounds** (N, `features/qty-input.js`) — Promise: every `qty:change` the
  component reports is an integer in `[max(1,min), max]`. Harm: the cart receives 0 or a
  quantity above stock and the order cannot be placed.
- **QuantityMirrorsDisplay** (N, `features/qty-input.js`) — Promise: the field text and
  the delete/minus buttons always match the value the component reports. Harm: the
  field says 0 while the cart gets 1, and at qty 2 the trash icon stays where the minus
  should be, so a shopper who wants 1 clicks remove. **FINDING 4.**
- **QuantityTargets** (N, `cart/quantity.js`) — Promise: a quantity event mutates the
  **cart line id** it came from (not the catalog id) and product-card inputs are
  ignored. Harm: changing one line changes or removes another line.
- **QtyFailureSurfaces** (N, `cart/quantity.js`) — Promise: a rejected update or remove
  fires `zidcart:error` and never runs the success callback. Harm: a failed change looks
  applied, and the shopper checks out believing the quantity is right.
- **CouponFormState** (N, `cart/coupon.js`) — Promise: the apply button is disabled
  exactly while the trimmed input is empty. Harm: a dead button, or an empty POST.
- **CouponSubmitOnce** (N, `cart/coupon.js`) — Promise: one request per enabled submit,
  a busy button sends nothing, and a rejected code re-enables the button, hides the
  spinner, restores the label and refocuses the input. Harm: the coupon applies twice,
  or the form stays disabled with a spinner and no way to retry.
- **RedemptionRecovers** (N, `cart/loyalty.js`) — Promise: a rejected (or `ok:false`)
  redemption restores the control; a successful one hands over to the refresh. Harm: the
  loyalty control stays dead after a failed redemption.
- **GiftDeleteRecovers** (N, `cart/gift.js`) — Promise: a failed gift-card delete
  restores the icon and spinner; a successful one reloads once. Harm: a spinner spins
  forever over a gift card the shopper cannot remove.
- **BadgeConsistency** (N, `cart/badge.js`) — Promise: every `[data-cart-badge]` shows
  the same count (`cart_items_quantity`, else `products_count`, else 0), hides at 0, and
  is left alone when the cart read fails. Harm: the header count contradicts the cart.
- **BadgeOnRefresh** (N, `refresh.js:refreshCartPage`, `controller.js:cartProductsHtmlChanged`)
  — Promise: after the theme re-renders the cart, the header badge equals the new
  `products_count`. Harm: the header says 2 items while the cart holds 1. **FINDING 1.**
- **ControllerInitOnce** (N, `cart/controller.js`) — Promise: a second `CartPage.init`
  adds no second submit delegation. Harm: one coupon submit applies the code twice.
  **holds.**
- **AddToCartBindsOnce** (N, `cart/add-to-cart.js`) — Promise: a second `initButtons`
  adds no second click binding, and a disabled button adds nothing. Harm: one click adds
  the product twice.
- **GiftPopupTimer** (N, `features/gifting.js`) — Promise: the header gift hint shows
  after an add, a second add keeps one timer, and it hides ~4 s after the last add.
  Harm: the hint covers the header forever, or vanishes before it is read.
- **RewardsRowsOnce** (N, `features/loyalty-rewards.js`) — Promise: each active
  redemption method is listed exactly once however often the popup is populated.
  Harm: duplicated reward options with different point costs on screen.
- **RefreshFailureFallback** (N, `refresh.js`) — Promise: a failed refresh reloads the
  page once and clears the loading state (`aria-busy`, `pointer-events`). Harm: the
  products list stays dimmed and unclickable after a network blip.
- **RefreshConverges** (T) — Promise: with no refresh in flight and none owed, the page
  shows the cart the platform holds. Harm: the shopper reads and acts on an older cart —
  wrong quantity, wrong total — until something else makes the page refresh.
  **FINDING 2.**

## Coverage record (property → file:function)

| Property | Tool | file:function | Today |
|---|---|---|---|
| CartPageShape | J | `templates/cart.jinja` (content block) | holds |
| SectionGating | J | `templates/cart.jinja`; `components/cart/coupon-code.jinja`, `loyalty-program.jinja`, `gift-order.jinja`, `gift-card-display.jinja`, `checkout-buttons.jinja`, `empty-state.jinja` | holds |
| TotalsRows | J | `components/cart/order-summary.jinja` (`for cartTotal in cart.totals`) | holds |
| DiscountSign | J | `components/cart/order-summary.jinja` (discount branch) | holds |
| CouponSectionState | J | `components/cart/coupon-code.jinja` | holds |
| ProgressWidth | J | `components/cart/shipping-progress.jinja` (`style="width: …%"`, truck offset) | **violation** |
| CartTextEscaping | J | `components/cart/order-summary.jinja`, `components/cart/coupon-code.jinja` | **violation** |
| TotalsRows (JS) | N | `assets/js/cart/totals.js:updateCartTotals` | holds |
| DiscountSign (JS) | N | `assets/js/cart/totals.js:updateCartTotals` (`formatDiscount`) | holds |
| TotalsTextEscaping | N | `assets/js/cart/totals.js:updateCartTotals` | **violation** |
| ProgressWidth (JS) | N | `assets/js/cart/totals.js:updateFreeShippingProgress` | **violation** |
| QuantityBounds | N | `assets/js/features/qty-input.js:updateQuantity`, `handleInputChange` | holds |
| QuantityMirrorsDisplay | N | `assets/js/features/qty-input.js:updateQuantity`, `updateButtonVisibility` | **violation** |
| QuantityTargets | N | `assets/js/cart/quantity.js:setupQuantityInputHandlers`, `handleCartQuantityChange`, `handleCartProductRemove` | holds |
| QtyFailureSurfaces | N | `assets/js/cart/quantity.js:handleCartQuantityChange`, `handleCartProductRemove` | holds |
| CouponFormState | N | `assets/js/cart/coupon.js:setupCouponInput` | holds |
| CouponSubmitOnce | N | `assets/js/cart/coupon.js:applyCoupon`, `removeCoupon` | holds |
| RedemptionRecovers | N | `assets/js/cart/loyalty.js:applyLoyaltyRedemption`, `removeLoyaltyRedemption` | holds |
| GiftDeleteRecovers | N | `assets/js/cart/gift.js:deleteGiftCard` | holds |
| BadgeConsistency | N | `assets/js/cart/badge.js:refreshBadge` | holds |
| BadgeOnRefresh | N | `assets/js/cart/refresh.js:refreshCartPage`; `assets/js/cart/controller.js:cartProductsHtmlChanged` | **violation** |
| ControllerInitOnce | N | `assets/js/cart/controller.js:init`, `setupEventDelegation` | holds |
| AddToCartBindsOnce | N | `assets/js/cart/add-to-cart.js:initButtons`, `addToCart` | holds |
| GiftPopupTimer | N | `assets/js/features/gifting.js:showGiftPopup`, `init` | holds |
| RewardsRowsOnce | N | `assets/js/features/loyalty-rewards.js:populateRewardsPopup` | holds |
| RefreshFailureFallback | N | `assets/js/cart/refresh.js:refreshCartPage` (catch/finally) | holds |
| RefreshConverges | T | `assets/js/cart/refresh.js:refreshCartPage` (`isRefreshing` guard), `setupZidCartEventListeners` | **violation** |

Every module of the group is on that list. `assets/js/features/loyalty-rewards.js` is
included even though it never runs on the cart page (`layout.jinja` excludes
`cart_page`): its populating logic is the module's own promise.

## Findings, in code terms

1. **The header badge goes stale** (`refreshCartPage`, `cartProductsHtmlChanged`). Both
   call `window.cartManager.refreshBadge()` if a platform global exists — it does not on
   this storefront — so the badge keeps its server-rendered number. Counterexample:
   two lines, remove one, the products list and totals re-render, the badge still says
   `2` while `/api/v1/cart` says `products_count: 1`. `refreshBadge` is imported and
   called from `add-to-cart.js`, so the capability exists in the theme.
2. **A refresh that arrives during a refresh is dropped** (`if (isRefreshing) return;`).
   The event is forgotten instead of owed, and the in-flight response carries the cart as
   of its request, so the swap can write an older cart and nothing else fires. TLC
   counterexample (`server / dom / captured / inflight`):
   `1 / 1 / 1 / FALSE → 2 / 1 / 2 / TRUE → 1 / 1 / 2 / TRUE → 1 / 2 / 2 / FALSE` — the
   page shows 2 while the cart holds 1. The live replay (`cart-refresh-race`) reproduces
   it with the page stuck for the whole 12 s window.
3. **The free-shipping bar overflows its track** (`shipping-progress.jinja`,
   `updateFreeShippingProgress`). `products_subtotal_percentage_from_min` goes into
   `width` unclamped; store 1 returns `status: max_exceeded`, `percentage: 202`, so the
   cart renders `style="width: 202%"` and a truck at `calc(202% - 12px)`. Only
   `status == 'applied'` is forced to 100.
4. **The quantity field and its buttons drift from the reported value**
   (`updateQuantity`, `handleInputChange`). Typing `0` (or clearing) leaves the raw text
   in the field because `clampedValue !== value` compares against the already-normalised
   number, so the component reports 1 while the field shows `0`; and `updateQuantity`
   changes the value without calling `updateButtonVisibility`, so at qty 2 the trash
   icon is still shown and the minus stays hidden.
5. **Cart strings are written as markup** (`updateCartTotals` and the matching
   templates). `innerHTML` concatenation interpolates `coupon.code`,
   `gift_card_details.code`, the loyalty label, `total.title` and `total.value_string`
   unescaped, and vitrin renders `.jinja` with `autoescape=select_autoescape()`, which
   leaves `.jinja` unescaped — both renders pass markup through. Today that is a display
   defect for a code containing `<`; it becomes an XSS sink the day any of those fields
   is shopper- or merchant-typed.

## The refresh race

`model/Refresh.tla` models `refresh.js` as written: a mutation and the `zidcart:updated`
it fires are one step; a refresh captures the server's cart when its request goes out and
writes it into the page when it lands. `model/read_flags.py` reads the one constant the
model cannot guess — whether the guard drops the event (`GuardDrops`) or a pending flag
remembers it — from the live code of `refresh.js`, comments stripped. TRUE needs
`refreshCartPage` to start with `if (isRefreshing) return; isRefreshing = true;`; FALSE
needs a pending flag set to `true` and re-run from a `finally`. Any other shape (the guard
commented out, wrapped in an `if`, moved after the fetch, weakened) exits 2.

`check.sh` runs TLC twice: `as-coded` (must report `Consistent` violated) and `queued`
(the same model with the event remembered — must hold). The green `queued` run is what a
fix looks like, and keeps the property from being vacuously true. Both runs cover
`CartValues = {1, 2}`, two orderings of two commits around one in-flight response.

Read a TLC result with the pstack `/statechart` skill: it turns the `Consistent`
violation into the shortest sequence of steps in the code's words, and draws the state
chart when the property holds. Do not copy `/statechart`'s commands or paths here — they
change between releases.

If TLC is missing, `check.sh` exits 2 with the install hint; a JDK 11+ and
`~/.local/share/tla/tla2tools.jar` (or a `tlc` wrapper on `PATH`) is enough.

## Reading a result

- `ok … holds` — the property still holds on every case in the bound.
- `ok … violation` + `FINDING:` — the recorded defect still reproduces. Not a failure of
  the run; it is the record. `check.sh` exits 0.
- `CHANGED <property>: recorded X, now Y` — the code moved. If Y is `holds`, the finding
  is fixed: delete it here and un-fail the matching `verify-cart` journey. If Y is
  `violation`, a regression landed: report it, keep the property.
- A template that raises (a syntax error, a missing filter) is a change, not a crash:
  `CHANGED <property>: recorded holds, now error`, with the Jinja error under it. Exit 1.
- `refresh.js: refreshCartPage no longer starts with ...`/exit 2: the refresh code has a
  shape the race model does not describe. Re-read `refresh.js` against `model/Refresh.tla`
  before touching `read_flags.py`; a dropped guard is a regression, not a harness bug.
- Any other `ERROR`/exit 2: the setup or the harness broke (no TLC, no node, a module
  that throws on import). Fix that, not the property.

## What the harness stands in for, and the bounds

- **Browser**: `harness/fakedom.mjs` builds an `EventTarget` element (`dataset`,
  `classList`, `style`, `hidden`, `disabled`, `value`, `textContent`), an `EventTarget`
  document and a `window` proxy that mirrors writes onto Node's globals (browsers expose
  `window.zid` as `zid`). Node's real `Event`/`CustomEvent`/`EventTarget` are used.
- **Imports**: where an import drags in a module the property does not exercise
  (`refresh.js` → `totals.js`/`coupon.js`/`layout.js`, `loyalty.js` → `layout.js`,
  `controller.js`/`add-to-cart.js` → their dependencies), the loader removes the import
  statements and injects the named stubs. The module body under test is unmodified; the
  stub list sits at each call site.
- **Templates**: `layout.jinja` and the `vitrin:*` partials are minimal stubs (other
  groups' files); every `components/*` and `templates/*` file under test is the real
  file, rendered with `autoescape=False` to match vitrin's `select_autoescape()`.
- **Network**: `fetch`, `DOMParser` and `window.zid` are stubs; nothing leaves the box.
- **Bounds**: quantity sequences up to length 3 over {±1 click, `0`, `7`, `99`, clear}
  for three min/max ranges; totals over the shapes declared in each harness; refresh
  over two cart values and two booleans, exhaustively. Exhaustive inside those bounds,
  silent outside.

## Not covered here

- The authenticated halves of `loyalty.js`/`gift.js` and a coupon *success* (no valid
  code for store 1). `verify-cart` lists the same gap.
- Vitrin's own partials (`vitrin:v2/cart/product_card.jinja`, `payment_widgets.jinja`,
  `apple-pay-quick-checkout.jinja`) and the platform SDK, which the cart only calls.
- Anything visual: the bar overflow is caught as a number, not as a painted layout.

## Proving the suite still has teeth

Five mutants are realistic regressions. Run each on a copy, never on this checkout (the
shared storefront serves these files):

- `mutants/QuantityBounds.patch` removes the lower clamp in `qty-input.js` (a shopper
  decrements to 0). It breaks the JavaScript half.
- `mutants/CartPageShape.patch` renames the `CartPage.init(` call in `templates/cart.jinja`,
  so the cart page never boots. It breaks the template half.
- `mutants/GuardCommented.patch`, `GuardWrapped.patch` and `GuardMoved.patch` comment out
  the refresh guard, wrap it in an `if` that is never true, or move it after the fetch.
  Each one changes what the race model describes, so `read_flags.py` must refuse it.

```bash
SCRATCH="${TMPDIR:-/tmp}"
for m in QuantityBounds CartPageShape GuardCommented GuardWrapped GuardMoved; do
  rsync -a --exclude node_modules --exclude .git \
    "$(git rev-parse --show-toplevel)/" "$SCRATCH/gt-cart-break/"
  patch -p1 -d "$SCRATCH/gt-cart-break" < .agents/skills/formal-cart/mutants/$m.patch
  ROOT="$SCRATCH/gt-cart-break" bash "$SCRATCH/gt-cart-break/.agents/skills/formal-cart/check.sh"
  # QuantityBounds, CartPageShape: exit 1 (CHANGED). Guard*: exit 2 (read_flags refuses).
  rm -rf "$SCRATCH/gt-cart-break"
done
```

QuantityBounds and CartPageShape each print exactly one `CHANGED` line and
`formal-cart: outcomes changed`, then exit 1. The three Guard mutants each exit 2 with
`refresh.js: refreshCartPage no longer starts with ...` before any suite runs.
The QuantityBounds counterexample is `min1/maxinf dec reports >= 1: reported 0 below 1`.
Unpatched, `check.sh` exits 0. If a mutant prints its `CHANGED` line and then
`ERROR harness exited 1 without its summary line`, the summary regex in `check.sh` has
drifted from its harness: fix the regex, not the property. Any other exit 2 is the setup
(no TLC, no node, no `uv`): read the `ERROR` or `TLC` line.

## When a change lands

1. Read the `NOTE drift:` line `check.sh` prints — `git diff --stat` of every covered
   file since `sync-commit`.
2. If the change is intended, re-read the property against the new code, then move
   `sync-commit:` to the new HEAD **only after** confirming the checks describe the code
   at that commit.
3. A property flipping to `holds` means its finding was fixed: delete the finding here
   and the "expected to fail" note in `verify-cart` in the same PR.
4. New cart behaviour needs a new property, not a looser existing one: add the code under
   the bound, record its outcome in both harnesses' `EXPECTED` and in this table.

For bringing this skill back in line after a large change, use the pstack
`/maintain-formal-verification-skill` skill.
