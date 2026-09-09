/**
 * Gifting Widgets Module
 *
 * Shows the header gifting hint popup after a product is added to the cart.
 */

const POPUP_HIDE_DELAY = 4000;

let popupTimer = null;

/**
 * Show the header gifting hint under the cart badge, then auto-hide
 */
function showGiftPopup() {
  const popup = document.querySelector("[data-gift-cart-popup]");
  if (!popup) return;

  popup.hidden = false;
  clearTimeout(popupTimer);
  popupTimer = setTimeout(() => {
    popup.hidden = true;
  }, POPUP_HIDE_DELAY);
}

function init() {
  window.addEventListener("cart:updated", (e) => {
    if (e.detail?.action === "add") showGiftPopup();
  });

  document.querySelector("[data-gift-popup-close]")?.addEventListener("click", () => {
    const popup = document.querySelector("[data-gift-cart-popup]");
    if (popup) popup.hidden = true;
    clearTimeout(popupTimer);
  });
}

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
