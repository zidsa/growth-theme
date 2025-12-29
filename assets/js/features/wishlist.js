/**
 * Wishlist Module
 *
 * Handles all wishlist functionality with a single-button approach.
 * Updates button content (SVG icon) dynamically based on state.
 */

// ─────────────────────────────────────────────────────────────
// Icons
// ─────────────────────────────────────────────────────────────

const ICONS = {
  EMPTY_HEART: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" class="text-primary" fill="none" > <path d="M12.001 4.52853C14.35 2.42 17.98 2.49 20.2426 4.75736C22.5053 7.02472 22.583 10.637 20.4786 12.993L11.9999 21.485L3.52138 12.993C1.41705 10.637 1.49571 7.01901 3.75736 4.75736C6.02157 2.49315 9.64519 2.41687 12.001 4.52853ZM18.827 6.1701C17.3279 4.66794 14.9076 4.60701 13.337 6.01687L12.0019 7.21524L10.6661 6.01781C9.09098 4.60597 6.67506 4.66808 5.17157 6.17157C3.68183 7.66131 3.60704 10.0473 4.97993 11.6232L11.9999 18.6543L19.0201 11.6232C20.3935 10.0467 20.319 7.66525 18.827 6.1701Z" fill="currentColor" ></path> </svg>`,
  FILLED_HEART: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"> <path d="M12 8C12 8 12 8 12.76 7C13.64 5.84 14.94 5 16.5 5C18.99 5 21 7.01 21 9.5C21 10.43 20.72 11.29 20.24 12C19.43 13.21 12 21 12 21C12 21 4.57 13.21 3.76 12C3.28 11.29 3 10.43 3 9.5C3 7.01 5.01 5 7.5 5C9.06 5 10.37 5.84 11.24 7C12 8 12 8 12 8Z" fill="#C22B51"/> <path d="M12 8C12 8 12 8 11.24 7C10.36 5.84 9.06 5 7.5 5C5.01 5 3 7.01 3 9.5C3 10.43 3.28 11.29 3.76 12C4.57 13.21 12 21 12 21M12 8C12 8 12 8 12.76 7C13.64 5.84 14.94 5 16.5 5C18.99 5 21 7.01 21 9.5C21 10.43 20.72 11.29 20.24 12C19.43 13.21 12 21 12 21" stroke="#C22B51" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/> </svg>`,
  SPINNER: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="size-4 animate-spin text-primary" role="status" aria-label="Loading"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>`
};

// ─────────────────────────────────────────────────────────────
// Wishlist Manager Class
// ─────────────────────────────────────────────────────────────

class WishlistManager {
  constructor() {
    this.LABELS = {
      addToWishlist: window.wishlistConfig?.labels?.addToWishlist || "Add to wishlist",
      removeFromWishlist: window.wishlistConfig?.labels?.removeFromWishlist || "Remove from wishlist",
      loading: window.wishlistConfig?.labels?.loading || "Loading"
    };

    this.wishlistProductIds = new Set();
    this.isLoggedIn = false;
    this.isInitialized = false;
    this.isZidReady = false;

    this.handleWishlistClick = this.handleWishlistClick.bind(this);
  }

  async waitForZidSDK() {
    const MAX_RETRIES = 20;
    const INITIAL_DELAY = 100;
    const MAX_DELAY = 2000;

    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      if (window.zid) {
        this.isZidReady = true;
        return true;
      }
      const delay = Math.min(INITIAL_DELAY * Math.pow(1.5, attempt), MAX_DELAY);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }

    this.isZidReady = false;
    return false;
  }

  async initialize() {
    if (this.isInitialized) return;

    await this.waitForZidSDK();

    if (this.isZidReady) {
      await this.syncWishlistState();
    } else {
      this.isLoggedIn = false;
      this.updateAllButtons();
    }

    document.addEventListener("click", this.handleWishlistClick);
    window.addEventListener("products-updated", () => this.updateAllButtons());
    window.addEventListener("content:loaded", () => this.updateAllButtons());

    this.isInitialized = true;
  }

  handleWishlistClick(event) {
    const button = event.target.closest("[data-wishlist-btn]");
    if (!button) return;

    event.preventDefault();
    event.stopPropagation();

    const productId = button.dataset.productId;
    if (!productId) return;

    if (!this.isLoggedIn) {
      this.redirectToLogin();
      return;
    }

    if (this.wishlistProductIds.has(productId)) {
      this.removeFromWishlist(productId);
    } else {
      this.addToWishlist(productId);
    }
  }

  async syncWishlistState() {
    if (!window.zid?.account?.wishlists) {
      this.isLoggedIn = false;
      this.updateAllButtons();
      return;
    }

    try {
      const response = await window.zid.account.wishlists();
      this.isLoggedIn = true;

      let productIds = [];
      if (response?.results && Array.isArray(response.results)) {
        productIds = response.results.map((item) => item.id);
      } else if (Array.isArray(response)) {
        productIds = response;
      }

      this.wishlistProductIds = new Set(productIds);
      this.updateAllButtons();
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        this.isLoggedIn = false;
        this.updateAllButtons();
      }
    }
  }

  async addToWishlist(productId) {
    const button = this.getButton(productId);
    if (!button) return;

    this.setButtonState(button, "loading");

    try {
      const response = await window.zid.account.addToWishlists(
        { product_ids: [productId] },
        { showErrorNotification: true }
      );

      if (response) {
        this.wishlistProductIds.add(productId);
        this.setButtonState(button, "filled");
      }
    } catch (error) {
      this.setButtonState(button, "empty");
    }
  }

  async removeFromWishlist(productId) {
    const button = this.getButton(productId);
    if (!button) return;

    this.setButtonState(button, "loading");

    try {
      await window.zid.account.removeFromWishlist(productId, { showErrorNotification: true });
      this.wishlistProductIds.delete(productId);
      this.setButtonState(button, "empty");
    } catch (error) {
      this.setButtonState(button, "filled");
    }
  }

  updateAllButtons() {
    const buttons = document.querySelectorAll("[data-wishlist-btn]");

    buttons.forEach((button) => {
      const productId = button.dataset.productId;
      if (!productId) return;

      if (!this.isLoggedIn) {
        this.setButtonState(button, "guest");
      } else if (this.wishlistProductIds.has(productId)) {
        this.setButtonState(button, "filled");
      } else {
        this.setButtonState(button, "empty");
      }
    });
  }

  setButtonState(button, state) {
    switch (state) {
      case "guest":
      case "empty":
        button.innerHTML = ICONS.EMPTY_HEART;
        button.setAttribute("aria-label", this.LABELS.addToWishlist);
        button.disabled = false;
        break;
      case "filled":
        button.innerHTML = ICONS.FILLED_HEART;
        button.setAttribute("aria-label", this.LABELS.removeFromWishlist);
        button.disabled = false;
        break;
      case "loading":
        button.innerHTML = ICONS.SPINNER;
        button.setAttribute("aria-label", this.LABELS.loading);
        button.disabled = true;
        break;
    }
  }

  getButton(productId) {
    return document.querySelector(`[data-wishlist-btn][data-product-id="${productId}"]`);
  }

  redirectToLogin() {
    const currentPath = window.location.pathname;
    window.location.href = `/auth/login?redirect_to=${encodeURIComponent(currentPath)}`;
  }

  isInWishlist(productId) {
    return this.wishlistProductIds.has(productId);
  }

  async refresh() {
    if (!this.isZidReady) {
      await this.waitForZidSDK();
    }
    if (this.isZidReady) {
      await this.syncWishlistState();
    }
  }

  destroy() {
    document.removeEventListener("click", this.handleWishlistClick);
    this.wishlistProductIds.clear();
    this.isInitialized = false;
  }
}

// ─────────────────────────────────────────────────────────────
// Global Instance
// ─────────────────────────────────────────────────────────────

const wishlistManager = new WishlistManager();
window.wishlistManager = wishlistManager;

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  wishlistManager.initialize();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

export { wishlistManager };
export default WishlistManager;
