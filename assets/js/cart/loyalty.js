/**
 * Cart Loyalty Module
 *
 * Handles loyalty points calculations, redemption methods, and applying/removing redemptions.
 */

// Module state
const state = {
  loyaltyPoints: 0,
  redemptionMethods: [],
  config: null,
  initialized: false
};

/**
 * Initialize loyalty program
 * @param {Object} config - Configuration object
 * @param {number} config.cartTotalValue - Cart total value
 * @param {string} config.storeCurrencyCode - Store currency code
 * @param {Object} config.translations - Translation strings
 */
export function initLoyaltyProgram(config) {
  // Store config for re-init after cart updates (use passed config or stored config)
  if (config) {
    state.config = config;
  }

  const cfg = state.config;
  if (!cfg) return;

  // Calculate points for this purchase
  calculateLoyaltyPoints(cfg.cartTotalValue);

  // If logged in, get customer points and redemption methods
  if (window.customerAuthState && window.customerAuthState.isAuthenticated) {
    getCustomerLoyaltyPoints(() => {
      getRedemptionMethods(cfg.storeCurrencyCode, cfg.cartCurrencyCode, cfg.translations);
    });
  }

  // Listen for cart-updated event only once
  if (!state.initialized) {
    state.initialized = true;
    window.addEventListener("cart-updated", () => initLoyaltyProgram());
    window.addEventListener("vitrin:auth:success", () => initLoyaltyProgram());
  }
}

/**
 * Calculate loyalty points for a total amount
 * @param {number} total - Cart total value
 */
export function calculateLoyaltyPoints(total) {
  if (!window.zid?.cart?.getCalculatedPoints) return;

  window.zid.cart
    .getCalculatedPoints(total, { showErrorNotification: false })
    .then((response) => {
      if (response && response.points !== undefined) {
        const pointsEls = document.querySelectorAll("[data-loyalty-calculated-points]");
        pointsEls.forEach((el) => {
          el.textContent = response.points;
        });
      }
    })
    .catch((err) => {
      console.error("Error calculating loyalty points:", err);
    });
}

/**
 * Get customer's current loyalty points balance
 * @param {Function} callback - Callback after fetching points
 */
export function getCustomerLoyaltyPoints(callback) {
  if (!window.zid?.cart?.getCustomerLoyaltyPoints) return;

  window.zid.cart
    .getCustomerLoyaltyPoints({ showErrorNotification: false })
    .then((response) => {
      if (response && response.balance !== undefined) {
        state.loyaltyPoints = response.balance;

        // Update balance display
        const balanceEl = document.querySelector("[data-loyalty-customer-points]");
        if (balanceEl) {
          balanceEl.textContent = state.loyaltyPoints;
        }

        // Update remaining points after redemption
        const remainingEl = document.querySelector("[data-loyalty-remaining-points]");
        if (remainingEl) {
          remainingEl.textContent = state.loyaltyPoints;
        }

        if (callback) callback();
      }
    })
    .catch((err) => {
      console.error("Error getting customer loyalty points:", err);
    });
}

/**
 * Get available redemption methods
 * @param {string} storeCurrencyCode - Store currency code
 * @param {string} cartCurrencyCode - Cart currency code
 * @param {Object} translations - Translation strings
 */
export function getRedemptionMethods(storeCurrencyCode, cartCurrencyCode, translations) {
  if (!window.zid?.cart?.getRedemptionMethods) return;

  window.zid.cart
    .getRedemptionMethods(storeCurrencyCode, { showErrorNotification: false })
    .then((response) => {
      if (response && response.options) {
        state.redemptionMethods = response.options;
        populateRedemptionSelect(state.redemptionMethods, cartCurrencyCode, translations);
      }
    })
    .catch((err) => {
      console.error("Error getting redemption methods:", err);
    });
}

/**
 * Populate redemption select dropdown
 * @param {Array} methods - Available redemption methods
 * @param {string} cartCurrencyCode - Cart currency code
 * @param {Object} translations - Translation strings
 */
function populateRedemptionSelect(methods, cartCurrencyCode, translations) {
  const select = document.querySelector("[data-loyalty-redemption-select]");
  const optionsContainer = document.querySelector("[data-loyalty-options]");
  if (!select || !optionsContainer) return;

  // Clear existing options
  optionsContainer.innerHTML = "";

  // Add redemption options
  methods.forEach((method) => {
    if (method.is_active) {
      const isDisabled = method.points_to_redeem > state.loyaltyPoints;

      // Format: "For X points get Y discount"
      const discountValue = method.reward.discount_value ? method.reward.discount_value.toFixed(2) : "0.00";
      const template = translations?.forPointsGetDiscount || "For %(points)s points get %(discount)s discount";
      const label = template
        .replace("%(points)s", method.points_to_redeem)
        .replace("%(discount)s", discountValue + " " + cartCurrencyCode);

      const option = document.createElement("el-option");
      // Use setAttribute for custom elements, not property assignment
      option.setAttribute("value", method.id);
      option.className = `text-foreground text-sm hover:bg-secondary aria-selected:bg-secondary block w-full cursor-pointer px-4 py-3 text-start transition-colors ${isDisabled ? "opacity-50 pointer-events-none" : ""}`;
      option.textContent = label;

      if (isDisabled) {
        option.setAttribute("disabled", "");
      }

      optionsContainer.appendChild(option);
    }
  });

  // Setup change handler using the element's onchange pattern (like sort-filter)
  select.onchange = function () {
    const applyBtn = document.querySelector("[data-loyalty-apply-btn]");
    if (applyBtn) {
      applyBtn.disabled = !this.value;
    }
  };
}

/**
 * Apply loyalty redemption
 * @param {Function} onSuccess - Callback after successful apply (typically refreshCartPage)
 */
export function applyLoyaltyRedemption(onSuccess) {
  const select = document.querySelector("[data-loyalty-redemption-select]");
  const btn = document.querySelector("[data-loyalty-apply-btn]");
  const text = document.querySelector("[data-loyalty-apply-text]");
  const spinner = document.querySelector("[data-loyalty-apply-spinner]");

  if (!select || !select.value || !btn) return;
  if (btn.disabled) return;

  // Get selected redemption method ID
  const id = select.value;

  if (!id) {
    console.error("No redemption method selected");
    return;
  }

  // Helper to reset button state
  const resetButton = () => {
    btn.disabled = false;
    if (text) text.classList.remove("hidden");
    if (spinner) spinner.classList.add("hidden");
  };

  // Show loading state
  btn.disabled = true;
  if (text) text.classList.add("hidden");
  if (spinner) spinner.classList.remove("hidden");

  window.zid.cart
    .addRedemptionMethod({ id}, { showErrorNotification:true })
    .then((response) => {
      if (response.ok) {
        if (onSuccess) onSuccess();
      } else {
        resetButton();
      }
    })
    .catch((err) => {
      console.error("Error applying redemption:", err);
      resetButton();
    });
}

/**
 * Remove applied loyalty redemption
 * @param {Function} onSuccess - Callback after successful remove (typically refreshCartPage)
 */
export function removeLoyaltyRedemption(onSuccess) {
  const btn = document.querySelector("[data-loyalty-remove-btn]");
  const icon = document.querySelector("[data-loyalty-remove-icon]");
  const spinner = document.querySelector("[data-loyalty-remove-spinner]");

  if (!btn) return;

  // Helper to reset button state
  const resetButton = () => {
    if (icon) icon.classList.remove("hidden");
    if (spinner) spinner.classList.add("hidden");
  };

  // Show loading state
  if (icon) icon.classList.add("hidden");
  if (spinner) spinner.classList.remove("hidden");

  window.zid.cart
    .removeRedemptionMethod({ showErrorNotification: true })
    .then((response) => {
      if (response.ok) {
        if (onSuccess) onSuccess();
      } else {
        resetButton();
      }
    })
    .catch((err) => {
      console.error("Error removing redemption:", err);
      resetButton();
    });
}

/**
 * Get current loyalty state
 * @returns {Object} Loyalty state
 */
export function getLoyaltyState() {
  return { ...state };
}
