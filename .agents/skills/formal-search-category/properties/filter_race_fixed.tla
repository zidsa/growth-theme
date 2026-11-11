------------------------- MODULE filter_race_fixed -------------------------
\* The same filter state machine with the coalescing fix, to show that
\* `Consistent` is satisfiable and not a property no theme could ever meet.
\*
\* Fix: when a response comes back for a URL that is no longer in the address
\* bar, start the fetch for the current URL instead of going idle
\* (product-filter.js fetchProducts l.56 / applyFilter l.39 would need to
\* remember the URL the response belonged to).
EXTENDS Naturals

CONSTANTS URLS

VARIABLES url, shown, loading, inflight

vars == <<url, shown, loading, inflight>>

Init ==
    /\ url = "A"
    /\ shown = "A"
    /\ loading = FALSE
    /\ inflight = "none"

ApplyFixed(u) ==
    /\ \/ /\ ~loading
          /\ loading' = TRUE
          /\ inflight' = u
          /\ UNCHANGED shown
       \/ /\ loading
          /\ UNCHANGED <<shown, loading, inflight>>
    /\ url' = u

\* The response arrives. If the address bar moved on, fetch again rather than
\* render a stale page and fall idle.
CompleteFixed ==
    \/ /\ loading
       /\ url = inflight
       /\ shown' = inflight
       /\ loading' = FALSE
       /\ UNCHANGED <<url, inflight>>
    \/ /\ loading
       /\ url # inflight
       /\ inflight' = url
       /\ UNCHANGED <<shown, loading, url>>

Next ==
    \/ \E u \in URLS : ApplyFixed(u)
    \/ CompleteFixed

Consistent ==
    (~loading) => (shown = url)

Spec == Init /\ [][Next]_vars

=============================================================================
