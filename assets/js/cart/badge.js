/**
 * Cart Badge Module
 *
 * Updates cart count badge in header/nav
 */

/**
 * Update all cart badges on the page
 */
export async function refreshBadge() {
  try {
    if (!window.zid) return;

    const cart = await window.zid.cart.get();
    const count = cart?.cart_items_quantity ?? cart?.products_count ?? 0;

    document.querySelectorAll("[data-cart-badge]").forEach((el) => {
      el.textContent = count;
      el.hidden = count === 0;
    });
  } catch (err) {
    console.error("[Cart] Refresh badge failed:", err);
  }
}
