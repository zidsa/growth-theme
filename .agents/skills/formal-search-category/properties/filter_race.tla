------------------------- MODULE filter_race -------------------------
\* What a shopper sees after two filter actions land close together.
\*
\* Model of assets/js/features/product-filter.js as it is written today:
\*   applyFilter()  pushes the new URL, then calls fetchProducts()  (l.19-42)
\*   fetchProducts() returns at once when this.isLoading is set        (l.56)
\*   the in-flight response renders the content of the URL it fetched  (l.68-82)
\*
\* url       the query string in the address bar (window.location)
\* shown     the URL whose products are inside #products-content
\* loading   this.isLoading
\* inflight  the URL the outstanding fetch was issued for ("none" if idle)
\*
\* Two URLs are enough: one action starts a fetch, the next one arrives while
\* it is still running.
EXTENDS Naturals

CONSTANTS URLS

VARIABLES url, shown, loading, inflight

vars == <<url, shown, loading, inflight>>

Init ==
    /\ url = "A"
    /\ shown = "A"
    /\ loading = FALSE
    /\ inflight = "none"

\* A filter action: the drawer's Apply, a sort change, a chip removal.
\* pushState happens first, unconditionally (applyFilter l.39).
Apply(u) ==
    /\ \/ /\ ~loading
          /\ loading' = TRUE
          /\ inflight' = u
          /\ UNCHANGED shown
       \/ /\ loading
          /\ UNCHANGED <<shown, loading, inflight>>
    /\ url' = u        \* the address bar moves either way

\* The fetch that was issued for `inflight` comes back and replaces the grid.
Complete ==
    /\ loading
    /\ shown' = inflight
    /\ loading' = FALSE
    /\ UNCHANGED <<url, inflight>>

Next ==
    \/ \E u \in URLS : Apply(u)
    \/ Complete

\* What the shopper is promised: whenever the page is not busy, the products on
\* screen are the products for the URL they can see and share.
Consistent ==
    (~loading) => (shown = url)

Spec == Init /\ [][Next]_vars

=============================================================================
