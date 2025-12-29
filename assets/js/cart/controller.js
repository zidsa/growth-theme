/**
 * Cart Controller Module
 *
 * Main orchestrator for cart page functionality.
 * Imports and coordinates all cart sub-modules.
 *
 * Platform Callbacks (MUST KEEP):
 * - window.CartPage - Public API
 * - window.cartProductsHtmlChanged - Platform callback
 * - window.toggleBundleItems - Platform callback
 * - window.refreshCartPage - Global alias
 */

import { setupCouponInput, applyCoupon, removeCoupon } from "./coupon.js";
import {
  initLoyaltyProgram,
  calculateLoyaltyPoints,
  applyLoyaltyRedemption,
  removeLoyaltyRedemption
} from "./loyalty.js";
import {
  handleGiftCardClick,
  editGiftCard,
  deleteGiftCard,
  updateGiftCardDisplay,
  setupGiftEventListener
} from "./gift.js";
import { updateCartTotals, updateFreeShippingProgress } from "./totals.js";
import { setupQuantityInputHandlers, updateQuantity } from "./quantity.js";
import { refreshCartPage, setCartLoadingState, setupZidCartEventListeners } from "./refresh.js";

// ===== State =====
const state = {
  cart: null,
  isInitialized: false
};

// ===== Configuration (set from template) =====
let config = {
  loyaltyEnabled: false,
  cartTotalValue: 0,
  storeCurrencyCode: "",
  cartCurrencyCode: "",
  translations: {
    forPointsGetDiscount: "For %(points)s points get %(discount)s discount",
    itemsCount: "%(count)s items",
    freeShippingApplied: "Free shipping applied!",
    addMoreForFreeShipping: "Add %(total)s more to get free shipping",
    discount: "Discount",
    loyalty: "Loyalty"
  }
};

// ===== Initialization =====

/**
 * Initialize cart controller
 * @param {Object} options - Configuration options
 */
function init(options) {
  if (state.isInitialized) return;

  // Merge configuration
  if (options) {
    Object.assign(config, options);
    if (options.cart) {
      state.cart = options.cart;
    }
    if (options.translations) {
      Object.assign(config.translations, options.translations);
    }
  }

  // Setup event delegation
  setupEventDelegation();

  // Setup coupon input handler
  setupCouponInput();

  // Setup quantity input handlers for cart
  setupQuantityInputHandlers(
    (cartProductId, productId, quantity) => {
      // Custom handler that uses refreshCartPage
      import("./quantity.js").then(({ handleCartQuantityChange }) => {
        handleCartQuantityChange(cartProductId, productId, quantity, refreshCartPage);
      });
    },
    (cartProductId, productId) => {
      // Custom handler that uses refreshCartPage
      import("./quantity.js").then(({ handleCartProductRemove }) => {
        handleCartProductRemove(cartProductId, productId, refreshCartPage);
      });
    }
  );

  // Setup ZidCart event listeners for AJAX refresh
  setupZidCartEventListeners();

  // Setup gift card event listener
  setupGiftEventListener();

  // Initialize loyalty program if enabled
  if (config.loyaltyEnabled) {
    initLoyaltyProgram(config);
  }

  // Expose global cart object for backward compatibility
  window.cartObject = state.cart;

  state.isInitialized = true;
}

// ===== Event Delegation =====

function setupEventDelegation() {
  // Form submit handling
  document.addEventListener("submit", (e) => {
    const form = e.target.closest("[data-coupon-form]");
    if (form) {
      e.preventDefault();
      applyCoupon(refreshCartPage);
    }
  });

  // Click handling
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;

    const action = btn.dataset.action;

    switch (action) {
      case "quantity":
        e.preventDefault();
        handleQuantityAction(btn);
        break;

      case "bundle-toggle":
        e.preventDefault();
        toggleBundleItems(btn.dataset.bundleId);
        break;

      case "coupon-apply":
        e.preventDefault();
        applyCoupon(refreshCartPage);
        break;

      case "coupon-remove":
        e.preventDefault();
        removeCoupon(refreshCartPage);
        break;

      case "gift-edit":
        e.preventDefault();
        editGiftCard();
        break;

      case "gift-delete":
        e.preventDefault();
        deleteGiftCard();
        break;

      case "gift-open":
        e.preventDefault();
        handleGiftCardClick();
        break;

      case "loyalty-apply":
        e.preventDefault();
        applyLoyaltyRedemption(refreshCartPage);
        break;

      case "loyalty-remove":
        e.preventDefault();
        removeLoyaltyRedemption(refreshCartPage);
        break;

      case "login":
        e.preventDefault();
        handleLoginAction(btn.dataset.redirect || "", btn.dataset.addToUrl !== "false");
        break;

      case "product-remove":
        // Call platform's cartProductRemove function
        if (typeof window.cartProductRemove === "function") {
          window.cartProductRemove(btn);
        }
        break;
    }
  });
}

/**
 * Handle quantity button action
 * @param {HTMLElement} btn - Button element
 */
async function handleQuantityAction(btn) {
  const cartProductId = btn.dataset.cartId;
  const productId = btn.dataset.productId;
  const delta = parseInt(btn.dataset.delta, 10);

  setCartLoadingState(true, cartProductId);
  await updateQuantity(cartProductId, productId, delta, refreshCartPage);
  setCartLoadingState(false);
}

// ===== Auth Helper =====

function handleLoginAction(redirectTo = "", addToUrl = true) {
  if (window.customerAuthState && window.customerAuthState.isAuthenticated) {
    return;
  }

  if (window.auth_dialog?.open && typeof window.auth_dialog.open === "function") {
    if (redirectTo && addToUrl) {
      const currentUrl = new URL(window.location.href);
      currentUrl.searchParams.set("redirect_to", redirectTo);
      window.history.replaceState({}, "", currentUrl.toString());
    }
    window.auth_dialog.open();
  } else {
    const redirectUrl = redirectTo ? "/auth/login?redirect_to=" + encodeURIComponent(redirectTo) : "/auth/login";
    window.location.href = redirectUrl;
  }
}

// ===== Bundle Items =====

/**
 * Toggle bundle items visibility
 * Supports both desktop (bundle-{id}) and mobile (bundle-mobile-{id}) patterns
 * @param {string} id - Bundle element ID
 */
function toggleBundleItems(id) {
  const content = document.getElementById(id);
  if (!content) return;

  // Determine if mobile and extract product ID
  const isMobile = id.includes("bundle-mobile-");
  const productId = id.replace("bundle-mobile-", "").replace("bundle-", "");

  // Find the correct arrow based on desktop/mobile
  const arrowSelector = isMobile
    ? '[data-bundle-arrow-mobile="' + productId + '"]'
    : '[data-bundle-arrow="' + productId + '"]';
  const arrow = document.querySelector(arrowSelector);

  const isHidden = content.classList.contains("hidden");
  content.classList.toggle("hidden");
  content.classList.toggle("flex");

  if (arrow) {
    arrow.style.transform = isHidden ? "rotate(180deg)" : "";
  }
}

// ===== Platform Integration =====

/**
 * Called by Vitrin platform when cart products HTML changes
 * This is the callback for client-side cart updates
 * @param {string} html - New HTML content
 * @param {Object} cart - Updated cart object
 */
function cartProductsHtmlChanged(html, cart) {
  // Update state
  state.cart = cart;

  // Update products list
  const productsList = document.querySelector("[data-cart-products-list]");
  if (productsList) {
    productsList.innerHTML = html;
  }

  // Update items count
  const itemsCount = document.querySelector("[data-cart-items-count]");
  if (itemsCount) {
    itemsCount.textContent = config.translations.itemsCount.replace("%(count)s", cart.products_count);
  }

  // Update totals
  updateCartTotals(cart, config);

  // Update free shipping progress
  updateFreeShippingProgress(cart, config);

  // Update cart badge
  if (window.cartManager) {
    window.cartManager.refreshBadge();
  }
}

// ===== Public API =====

const CartController = {
  init,
  state,

  // Auth
  handleLoginAction,

  // Product operations
  toggleBundleItems,
  updateQuantity: (cartId, productId, delta) => updateQuantity(cartId, productId, delta, refreshCartPage),

  // Loyalty
  applyLoyaltyRedemption: () => applyLoyaltyRedemption(refreshCartPage),
  removeLoyaltyRedemption: () => removeLoyaltyRedemption(refreshCartPage),

  // Coupon
  applyCoupon: () => applyCoupon(refreshCartPage),
  removeCoupon: () => removeCoupon(refreshCartPage),

  // Gift card
  editGiftCard,
  deleteGiftCard,
  handleGiftCardClick,

  // Platform integration
  cartProductsHtmlChanged,

  // AJAX refresh
  refreshCartPage
};

// ===== Global Exports (Platform Compatibility) =====

// Main API
window.CartPage = CartController;

// Platform callback aliases (backward compatibility)
window.toggleBundleItems = toggleBundleItems;
window.updateCartQuantity = CartController.updateQuantity;
window.handleLoginAction = handleLoginAction;
window.applyLoyaltyRedemption = CartController.applyLoyaltyRedemption;
window.removeLoyaltyRedemption = CartController.removeLoyaltyRedemption;
window.sendCoupon = CartController.applyCoupon;
window.deleteCoupon = CartController.removeCoupon;
window.editGiftCard = editGiftCard;
window.deleteGiftCard = deleteGiftCard;
window.handleGiftCardClick = handleGiftCardClick;
window.cartProductsHtmlChanged = cartProductsHtmlChanged;
window.refreshCartPage = refreshCartPage;

export default CartController;
