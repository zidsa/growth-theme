------------------------------ MODULE Refresh ------------------------------
(***************************************************************************)
(* A model of assets/js/cart/refresh.js as it is written today.            *)
(*                                                                         *)
(* The code:                                                               *)
(*                                                                         *)
(*   let isRefreshing = false;                                             *)
(*   export async function refreshCartPage() {                             *)
(*     if (isRefreshing) return;          <-- GuardDrops                  *)
(*     isRefreshing = true;                                                *)
(*     const response = await fetch(location.href);   <-- body composed    *)
(*     ... swapElement(products/totals/coupon/loyalty/...)                 *)
(*     isRefreshing = false;                                              *)
(*   }                                                                     *)
(*   window.addEventListener("zidcart:updated", () => refreshCartPage());   *)
(*                                                                         *)
(* One cart mutation and the `zidcart:updated` it fires are one step: the   *)
(* SDK dispatches the event from the promise callback that resolves the    *)
(* mutation. The refresh's response body is composed when the request is    *)
(* sent (`captured`), and is written into the DOM when it lands (`dom`).    *)
(*                                                                         *)
(* GuardDrops = TRUE is the code as written: an event that arrives while a *)
(* refresh is in flight is dropped, so its cart state is never rendered.    *)
(* GuardDrops = FALSE is the same model with the event remembered and a     *)
(* refresh started after the current one lands — the shape of the fix.      *)
(***************************************************************************)
EXTENDS Naturals

CONSTANTS CartValues,   \* the cart states worth distinguishing ({1, 2} from check.sh)
          GuardDrops    \* TRUE: `if (isRefreshing) return;` drops the event

VARIABLES server,       \* the cart the platform holds
          dom,          \* the cart state the page shows
          captured,     \* the cart state inside the response now in flight
          inflight,     \* a refresh is in flight
          pending       \* (fix only) another refresh is owed

vars == <<server, dom, captured, inflight, pending>>

TypeOK ==
    /\ server \in CartValues
    /\ dom \in CartValues
    /\ captured \in CartValues
    /\ inflight \in BOOLEAN
    /\ pending \in BOOLEAN

Init ==
    /\ server = 1
    /\ dom = 1
    /\ captured = 1
    /\ inflight = FALSE
    /\ pending = FALSE

\* A cart mutation commits, and the `zidcart:updated` it fires is handled at once.
\* Only a change is modelled: an event that leaves the cart as it was can start a
\* refresh but can never make the page disagree with the server.
Commit(v) ==
    /\ v /= server
    /\ server' = v
    /\ IF inflight
         THEN IF GuardDrops
                THEN UNCHANGED <<captured, inflight, pending>>   \* dropped
                ELSE /\ pending' = TRUE                          \* remembered
                     /\ UNCHANGED <<captured, inflight>>
         ELSE /\ inflight' = TRUE                                \* starts a refresh
              /\ captured' = v
              /\ UNCHANGED pending
    /\ UNCHANGED dom

\* The response lands: swapElement() writes the captured body into the page.
Land ==
    /\ inflight
    /\ dom' = captured
    /\ inflight' = FALSE
    /\ UNCHANGED <<server, captured, pending>>

\* The fix: a refresh that was owed starts once the current one has landed.
Restart ==
    /\ ~GuardDrops
    /\ pending
    /\ ~inflight
    /\ inflight' = TRUE
    /\ captured' = server
    /\ pending' = FALSE
    /\ UNCHANGED <<server, dom>>

Next ==
    \/ \E v \in CartValues: Commit(v)
    \/ Land
    \/ Restart

Spec == Init /\ [][Next]_vars /\ WF_vars(Land)

\* The promise: with nothing in flight and nothing owed, the page shows the
\* cart the platform holds. A shopper must never be left reading an older cart.
Consistent == (~inflight /\ ~pending) => (dom = server)

=============================================================================
