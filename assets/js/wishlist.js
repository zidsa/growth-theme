/**
 * Wishlist Manager
 *
 * Handles all wishlist functionality with a single-button approach.
 * Updates button content (SVG icon) dynamically based on state.
 *
 * Dependencies: Zid SDK (window.zid)
 *
 * Usage:
 * 1. Include this script in your layout
 * 2. Add wishlist buttons using the WishlistButton component
 * 3. The manager auto-initializes on page load
 */

class WishlistManager {
  constructor() {
    // Translatable strings (can be overridden via window.wishlistConfig)
    this.LABELS = {
      addToWishlist: window.wishlistConfig?.labels?.addToWishlist || "Add to wishlist",
      removeFromWishlist: window.wishlistConfig?.labels?.removeFromWishlist || "Remove from wishlist",
      loading: window.wishlistConfig?.labels?.loading || "Loading"
    };

    // SVG Icons as constants
    this.ICONS = {
      EMPTY_HEART: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" class="text-primary" fill="none" > <path d="M12.001 4.52853C14.35 2.42 17.98 2.49 20.2426 4.75736C22.5053 7.02472 22.583 10.637 20.4786 12.993L11.9999 21.485L3.52138 12.993C1.41705 10.637 1.49571 7.01901 3.75736 4.75736C6.02157 2.49315 9.64519 2.41687 12.001 4.52853ZM18.827 6.1701C17.3279 4.66794 14.9076 4.60701 13.337 6.01687L12.0019 7.21524L10.6661 6.01781C9.09098 4.60597 6.67506 4.66808 5.17157 6.17157C3.68183 7.66131 3.60704 10.0473 4.97993 11.6232L11.9999 18.6543L19.0201 11.6232C20.3935 10.0467 20.319 7.66525 18.827 6.1701Z" fill="currentColor" ></path> </svg>`,
      FILLED_HEART: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"> <path d="M12 8C12 8 12 8 12.76 7C13.64 5.84 14.94 5 16.5 5C18.99 5 21 7.01 21 9.5C21 10.43 20.72 11.29 20.24 12C19.43 13.21 12 21 12 21C12 21 4.57 13.21 3.76 12C3.28 11.29 3 10.43 3 9.5C3 7.01 5.01 5 7.5 5C9.06 5 10.37 5.84 11.24 7C12 8 12 8 12 8Z" fill="#C22B51"/> <path d="M12 8C12 8 12 8 11.24 7C10.36 5.84 9.06 5 7.5 5C5.01 5 3 7.01 3 9.5C3 10.43 3.28 11.29 3.76 12C4.57 13.21 12 21 12 21M12 8C12 8 12 8 12.76 7C13.64 5.84 14.94 5 16.5 5C18.99 5 21 7.01 21 9.5C21 10.43 20.72 11.29 20.24 12C19.43 13.21 12 21 12 21" stroke="#C22B51" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/> </svg>`,
      SPINNER: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="size-4 animate-spin text-primary" role="status" aria-label="Loading"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>`
    };

    // Cache of wishlist product IDs for quick lookups
    this.wishlistProductIds = new Set();

    this.isLoggedIn = false;

    this.isInitialized = false;

    this.isZidReady = false;

    // Bind methods to maintain context
    this.handleWishlistClick = this.handleWishlistClick.bind(this);

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => this.initialize());
    } else {
      this.initialize();
    }
  }

  /**
   * Wait for Zid SDK to be ready
   * Uses polling with exponential backoff
   */
  async waitForZidSDK() {
    const MAX_RETRIES = 20; // Maximum number of attempts
    const INITIAL_DELAY = 100; // Start with 100ms
    const MAX_DELAY = 2000; // Cap at 2 seconds

    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      // Check if Zid SDK is ready
      if (window.zid) {
        this.isZidReady = true;
        return true;
      }

      const delay = Math.min(INITIAL_DELAY * Math.pow(1.5, attempt), MAX_DELAY);
      // Wait before next attempt
      await new Promise((resolve) => setTimeout(resolve, delay));
    }

    this.isZidReady = false;
    return false;
  }

  /**
   * Initialize the wishlist manager
   */
  async initialize() {
    if (this.isInitialized) {
      return;
    }

    await this.waitForZidSDK();

    // Sync wishlist state if SDK is ready
    if (this.isZidReady) {
      await this.syncWishlistState();
    } else {
      // SDK not ready, user is likely not logged in or SDK failed to load
      this.isLoggedIn = false;
      this.updateAllButtons();
    }

    // Setup event click all wishlist buttons
    document.addEventListener("click", this.handleWishlistClick);

    // Subscribe to products-updated event (AJAX filtering)
    window.addEventListener("products-updated", () => this.updateAllButtons());

    // Re-sync buttons when quick view modal loads content
    window.addEventListener("quick-view-content-loaded", () => this.updateAllButtons());

    this.isInitialized = true;
  }

  /**
   * Event handler for wishlist button clicks
   */
  handleWishlistClick(event) {
    // Find closest wishlist button
    const button = event.target.closest("[data-wishlist-btn]");
    if (!button) return;

    event.preventDefault();
    event.stopPropagation();

    const productId = button.dataset.productId;
    if (!productId) {
      return;
    }

    // Check if user is guest (not logged in)
    if (!this.isLoggedIn) {
      this.redirectToLogin();
      return;
    }

    // Toggle wishlist state
    if (this.wishlistProductIds.has(productId)) {
      this.removeFromWishlist(productId);
    } else {
      this.addToWishlist(productId);
    }
  }

  /**
   * Fetch wishlist items from server and update UI
   */
  async syncWishlistState() {
    // Check if Zid SDK and account API are available
    if (!window.zid?.account?.wishlists) {
      this.isLoggedIn = false;
      this.updateAllButtons();
      return;
    }

    try {
      const response = await window.zid.account.wishlists();

      // User is logged in if we got a response
      this.isLoggedIn = true;

      // Extract product IDs from response
      let productIds = [];

      if (response?.results && Array.isArray(response.results)) {
        productIds = response.results.map((item) => item.id);
      } else if (Array.isArray(response)) {
        productIds = response;
      }

      this.wishlistProductIds = new Set(productIds);

      // Update all wishlist buttons on the page
      this.updateAllButtons();
    } catch (error) {
      // If error is 401/403, user is not logged in
      if (error.status === 401 || error.status === 403) {
        this.isLoggedIn = false;
        this.updateAllButtons();
      }
    }
  }

  /**
   * Add product to wishlist
   * @param {string} productId - Product ID to add
   */
  async addToWishlist(productId) {
    const button = this.getButton(productId);
    if (!button) return;

    // Show loading state
    this.setButtonState(button, "loading");

    try {
      const response = await window.zid.account.addToWishlists(
        { product_ids: [productId] },
        { showErrorNotification: true }
      );

      if (response) {
        this.wishlistProductIds.add(productId);

        // Update UI to filled state
        this.setButtonState(button, "filled");
      }
    } catch (error) {
      // Revert to empty state on error
      this.setButtonState(button, "empty");
    }
  }

  /**
   * Remove product from wishlist
   * @param {string} productId - Product ID to remove
   */
  async removeFromWishlist(productId) {
    const button = this.getButton(productId);
    if (!button) return;

    // Show loading state
    this.setButtonState(button, "loading");

    try {
      await window.zid.account.removeFromWishlist(productId, { showErrorNotification: true });
      // Update cache
      this.wishlistProductIds.delete(productId);

      this.setButtonState(button, "empty");
    } catch (error) {
      // Revert to filled state on error
      this.setButtonState(button, "filled");
    }
  }

  /**
   * Update all wishlist buttons on the page
   */
  updateAllButtons() {
    const buttons = document.querySelectorAll("[data-wishlist-btn]");

    buttons.forEach((button) => {
      const productId = button.dataset.productId;
      if (!productId) return;

      // Determine button state
      if (!this.isLoggedIn) {
        this.setButtonState(button, "guest");
      } else if (this.wishlistProductIds.has(productId)) {
        this.setButtonState(button, "filled");
      } else {
        this.setButtonState(button, "empty");
      }
    });
  }

  /**
   * Set button state (updates icon and styling)
   * @param {HTMLElement} button - Button element
   * @param {string} state - State: 'guest', 'empty', 'filled', 'loading'
   */
  setButtonState(button, state) {
    switch (state) {
      case "guest":
        // Guest user - show empty heart
        button.innerHTML = this.ICONS.EMPTY_HEART;
        button.setAttribute("aria-label", this.LABELS.addToWishlist);
        button.disabled = false;
        break;

      case "empty":
        // Logged-in, not in wishlist - show empty heart
        button.innerHTML = this.ICONS.EMPTY_HEART;
        button.setAttribute("aria-label", this.LABELS.addToWishlist);
        button.disabled = false;
        break;

      case "filled":
        // In wishlist - show filled heart in red
        button.innerHTML = this.ICONS.FILLED_HEART;
        button.setAttribute("aria-label", this.LABELS.removeFromWishlist);
        button.disabled = false;
        break;

      case "loading":
        // Loading state - show spinner
        button.innerHTML = this.ICONS.SPINNER;
        button.setAttribute("aria-label", this.LABELS.loading);
        button.disabled = true;
        break;
    }
  }

  /**
   * Get wishlist button for a product
   * @param {string} productId - Product ID
   * @returns {HTMLElement|null} Button element
   */
  getButton(productId) {
    return document.querySelector(`[data-wishlist-btn][data-product-id="${productId}"]`);
  }

  /**
   * Redirect guest users to login page
   */
  redirectToLogin() {
    const currentPath = window.location.pathname;

    window.location.href = `/auth/login?redirect_to=${encodeURIComponent(currentPath)}`;
  }

  /**
   * Check if a product is in the wishlist
   * @param {string} productId - Product ID
   * @returns {boolean} Whether product is in wishlist
   */
  isInWishlist(productId) {
    return this.wishlistProductIds.has(productId);
  }

  /**
   * Manually refresh wishlist state
   */
  async refresh() {
    // Ensure Zid SDK is ready
    if (!this.isZidReady) {
      await this.waitForZidSDK();
    }

    // Sync if SDK is ready
    if (this.isZidReady) {
      await this.syncWishlistState();
    }
  }

  /**
   * Cleanup event listeners
   */
  destroy() {
    document.removeEventListener("click", this.handleWishlistClick);
    this.wishlistProductIds.clear();
    this.isInitialized = false;
  }
}

// Initialize global wishlist manager instance
window.wishlistManager = new WishlistManager();

// Export for module usage (optional)
if (typeof module !== "undefined" && module.exports) {
  module.exports = WishlistManager;
}
