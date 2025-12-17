/**
 * Cart Page Module
 *
 * Consolidated JavaScript for the cart page following separation of concerns:
 * - Components handle presentation (Jinja templates)
 * - This module handles all behavior and state management
 *
 * Uses event delegation for all interactions instead of inline onclick handlers.
 */

window.CartPage = (function () {
  // ===== State =====
  const state = {
    cart: null,
    loyaltyPoints: 0,
    redemptionMethods: [],
    isRefreshing: false
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

  // ===== Selectors for AJAX refresh =====
  const selectors = {
    cartContainer: ".cart-with-products",
    productsList: "[data-cart-products-list]",
    orderSummary: "[data-cart-totals]",
    shippingProgress: "[data-free-shipping-bar]",
    paymentWidgets: "[data-payment-widgets]",
    emptyState: ".theme-container"
  };

  // ===== Initialization =====
  function init(options) {
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
    setupQuantityInputHandlers();

    // Setup ZidCart event listeners for AJAX refresh
    setupZidCartEventListeners();

    // Initialize loyalty program if enabled
    if (config.loyaltyEnabled) {
      initLoyaltyProgram();
    }

    // Expose global cart object for backward compatibility
    window.cartObject = state.cart;
  }

  // ===== Event Delegation =====
  function setupEventDelegation() {
    // Form submit handling
    document.addEventListener("submit", function (e) {
      const form = e.target.closest("[data-coupon-form]");
      if (form) {
        e.preventDefault();
        applyCoupon();
      }
    });

    // Click handling
    document.addEventListener("click", function (e) {
      const btn = e.target.closest("[data-action]");
      if (!btn) return;

      const action = btn.dataset.action;

      switch (action) {
        case "quantity":
          e.preventDefault();
          updateQuantity(btn.dataset.cartId, btn.dataset.productId, parseInt(btn.dataset.delta, 10));
          break;

        case "bundle-toggle":
          e.preventDefault();
          toggleBundleItems(btn.dataset.bundleId);
          break;

        case "coupon-apply":
          e.preventDefault();
          applyCoupon();
          break;

        case "coupon-remove":
          e.preventDefault();
          removeCoupon();
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
          applyLoyaltyRedemption();
          break;

        case "loyalty-remove":
          e.preventDefault();
          removeLoyaltyRedemption();
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

  // ===== Auth Helper =====
  function handleLoginAction(redirectTo, addToUrl) {
    if (redirectTo === undefined) redirectTo = "";
    if (addToUrl === undefined) addToUrl = true;

    if (window.customerAuthState && window.customerAuthState.isAuthenticated) {
      return;
    }

    if (window.auth_dialog && window.auth_dialog.open && typeof window.auth_dialog.open === "function") {
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

  // ===== Product Operations =====

  /**
   * Toggle bundle items visibility
   * Supports both desktop (bundle-{id}) and mobile (bundle-mobile-{id}) patterns
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

  /**
   * Update cart product quantity (legacy - for data-action="quantity" buttons)
   * New approach uses qty:change events from quantity-input component
   */
  async function updateQuantity(cartProductId, productId, delta) {
    const valueEl = document.querySelector('[data-quantity-value="' + cartProductId + '"]');
    const valueMobileEl = document.querySelector('[data-quantity-value-mobile="' + cartProductId + '"]');

    if (!valueEl) return;

    const currentQty = parseInt(valueEl.textContent, 10) || 1;
    const newQty = Math.max(0, currentQty + delta);

    // Update display immediately for better UX
    if (valueEl) valueEl.textContent = newQty;
    if (valueMobileEl) valueMobileEl.textContent = newQty;

    // Show loading state
    setCartLoadingState(true, cartProductId);

    try {
      if (newQty === 0) {
        // Remove product from cart
        await zid.cart.removeProduct({ product_id: cartProductId }, { showErrorNotification: true });
      } else {
        // Update quantity
        await zid.cart.updateProduct({ product_id: cartProductId, quantity: newQty }, { showErrorNotification: true });
      }

      // Refresh cart via AJAX instead of full page reload
      await refreshCartPage();
    } catch (error) {
      console.error("Error updating cart:", error);
      // Revert the display on error
      if (valueEl) valueEl.textContent = currentQty;
      if (valueMobileEl) valueMobileEl.textContent = currentQty;
      setCartLoadingState(false);
    }
  }

  // ===== Loyalty Program =====

  function initLoyaltyProgram() {
    // Calculate points for this purchase
    calculateLoyaltyPoints(config.cartTotalValue);

    // If logged in, get customer points and redemption methods
    if (window.customerAuthState && window.customerAuthState.isAuthenticated) {
      getCustomerLoyaltyPoints(function () {
        getRedemptionMethods();
      });
    }

    // Setup redemption select change handler
    const select = document.querySelector("[data-loyalty-redemption-select]");
    const applyBtn = document.querySelector("[data-loyalty-apply-btn]");
    if (select) {
      select.addEventListener("change", function (e) {
        if (applyBtn) {
          applyBtn.disabled = !e.target.value;
        }
      });
    }
  }

  function calculateLoyaltyPoints(total) {
    if (!window.zid || !window.zid.cart || !window.zid.cart.getCalculatedPoints) return;

    zid.cart
      .getCalculatedPoints(total, { showErrorNotification: false })
      .then(function (response) {
        if (response && response.points !== undefined) {
          const pointsEls = document.querySelectorAll("[data-loyalty-calculated-points]");
          pointsEls.forEach(function (el) {
            el.textContent = response.points;
          });
        }
      })
      .catch(function (err) {
        console.error("Error calculating loyalty points:", err);
      });
  }

  function getCustomerLoyaltyPoints(callback) {
    if (!window.zid || !window.zid.cart || !window.zid.cart.getCustomerLoyaltyPoints) return;

    zid.cart
      .getCustomerLoyaltyPoints({ showErrorNotification: false })
      .then(function (response) {
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
      .catch(function (err) {
        console.error("Error getting customer loyalty points:", err);
      });
  }

  function getRedemptionMethods() {
    if (!window.zid || !window.zid.cart || !window.zid.cart.getRedemptionMethods) return;

    zid.cart
      .getRedemptionMethods(config.storeCurrencyCode, { showErrorNotification: false })
      .then(function (response) {
        if (response && response.options) {
          state.redemptionMethods = response.options;
          populateRedemptionSelect(state.redemptionMethods);
        }
      })
      .catch(function (err) {
        console.error("Error getting redemption methods:", err);
      });
  }

  function populateRedemptionSelect(methods) {
    const select = document.querySelector("[data-loyalty-redemption-select]");
    if (!select) return;

    // Clear existing options except first
    while (select.options.length > 1) {
      select.remove(1);
    }

    // Add redemption options
    methods.forEach(function (method) {
      if (method.is_active) {
        const option = document.createElement("option");
        option.value = method.id;
        option.disabled = method.points_to_redeem > state.loyaltyPoints;

        // Format: "For X points get Y discount"
        const discountValue = method.reward.discount_value ? method.reward.discount_value.toFixed(2) : "0.00";
        option.textContent = config.translations.forPointsGetDiscount
          .replace("%(points)s", method.points_to_redeem)
          .replace("%(discount)s", discountValue + " " + config.cartCurrencyCode);

        select.appendChild(option);
      }
    });
  }

  function applyLoyaltyRedemption() {
    const select = document.querySelector("[data-loyalty-redemption-select]");
    const btn = document.querySelector("[data-loyalty-apply-btn]");
    const text = document.querySelector("[data-loyalty-apply-text]");
    const spinner = document.querySelector("[data-loyalty-apply-spinner]");

    if (!select || !select.value || !btn) return;
    if (btn.disabled) return;

    // Find selected method
    const selectedMethod = state.redemptionMethods.find(function (m) {
      return m.id === select.value;
    });

    if (!selectedMethod) {
      console.error("Redemption method not found");
      return;
    }

    // Show loading state
    btn.disabled = true;
    if (text) text.classList.add("hidden");
    if (spinner) spinner.classList.remove("hidden");

    zid.cart
      .addRedemptionMethod(selectedMethod, { showErrorNotification: true })
      .then(function (response) {
        if (response.ok) {
          refreshCartPage();
        } else {
          return response.json();
        }
      })
      .then(function (data) {
        if (data && data.message) {
          console.error("Redemption error:", data.message);
        }
        // Reset button state
        btn.disabled = false;
        if (text) text.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");
      })
      .catch(function (err) {
        console.error("Error applying redemption:", err);
        btn.disabled = false;
        if (text) text.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");
      });
  }

  function removeLoyaltyRedemption() {
    const btn = document.querySelector("[data-loyalty-remove-btn]");
    const icon = document.querySelector("[data-loyalty-remove-icon]");
    const spinner = document.querySelector("[data-loyalty-remove-spinner]");

    if (!btn) return;

    // Show loading state
    if (icon) icon.classList.add("hidden");
    if (spinner) spinner.classList.remove("hidden");

    zid.cart
      .removeRedemptionMethod({ showErrorNotification: true })
      .then(function (response) {
        if (response.ok) {
          refreshCartPage();
        } else {
          return response.json();
        }
      })
      .then(function (data) {
        if (data && data.message) {
          console.error("Remove redemption error:", data.message);
        }
        // Reset button state
        if (icon) icon.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");
      })
      .catch(function (err) {
        console.error("Error removing redemption:", err);
        if (icon) icon.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");
      });
  }

  // ===== Coupon Functions =====

  function setupCouponInput() {
    const couponInput = document.querySelector("[data-coupon-input]");
    const couponBtn = document.querySelector("[data-coupon-submit-btn]");
    if (couponInput && couponBtn) {
      couponInput.addEventListener("input", function (e) {
        couponBtn.disabled = !e.target.value.trim();
      });
    }
  }

  // ===== Quantity Input Handlers =====

  function setupQuantityInputHandlers() {
    // Listen for qty:change events from quantity inputs with cart context
    document.addEventListener("qty:change", function (e) {
      const wrapper = e.target.closest("[data-qty-input]");
      if (!wrapper) return;

      // Only handle if this is a cart quantity input (has cart-product-id)
      const cartProductId = wrapper.dataset.cartProductId;
      const productId = wrapper.dataset.productId;
      if (!cartProductId) return;

      const newQty = e.detail.value;
      handleCartQuantityChange(cartProductId, productId, newQty);
    });

    // Listen for qty:remove events (delete button clicked at qty=1)
    document.addEventListener("qty:remove", function (e) {
      const wrapper = e.target.closest("[data-qty-input]");
      if (!wrapper) return;

      const cartProductId = wrapper.dataset.cartProductId;
      const productId = wrapper.dataset.productId;
      if (!cartProductId) return;

      handleCartProductRemove(cartProductId, productId);
    });
  }

  function handleCartQuantityChange(cartProductId, productId, quantity) {
    // Dispatch loading event
    window.dispatchEvent(
      new CustomEvent("zidcart:loading", {
        detail: { cartProductId, productId, operation: "update", quantity }
      })
    );

    // Call the system's API function
    if (typeof window.updateProductQuantityApiCall === "function") {
      window.updateProductQuantityApiCall(cartProductId, productId, quantity, "template_for_cart_products_list");
    } else {
      // Fallback: use Zid SDK directly
      zid.cart
        .updateProduct({ product_id: cartProductId, quantity: quantity }, { showErrorNotification: true })
        .then(function () {
          refreshCartPage();
        })
        .catch(function (error) {
          console.error("Error updating cart quantity:", error);
          window.dispatchEvent(
            new CustomEvent("zidcart:error", {
              detail: { cartProductId, productId, operation: "update", error: error.message || error }
            })
          );
        });
    }
  }

  function handleCartProductRemove(cartProductId, productId) {
    // Call the system's remove function
    if (typeof window.removeProductApiCall === "function") {
      window.removeProductApiCall(cartProductId, productId, "template_for_cart_products_list");
    } else {
      // Fallback: use Zid SDK directly
      window.dispatchEvent(
        new CustomEvent("zidcart:loading", {
          detail: { cartProductId, productId, operation: "remove" }
        })
      );

      zid.cart
        .removeProduct({ product_id: cartProductId }, { showErrorNotification: true })
        .then(function () {
          refreshCartPage();
        })
        .catch(function (error) {
          console.error("Error removing product:", error);
          window.dispatchEvent(
            new CustomEvent("zidcart:error", {
              detail: { cartProductId, productId, operation: "remove", error: error.message || error }
            })
          );
        });
    }
  }

  // ===== ZidCart Event Listeners =====

  function setupZidCartEventListeners() {
    // Loading state - show spinner/overlay
    window.addEventListener("zidcart:loading", handleCartLoading);

    // Cart updated - refresh the page content via AJAX
    window.addEventListener("zidcart:updated", handleCartUpdated);

    // Error state - hide loading and show error
    window.addEventListener("zidcart:error", handleCartError);
  }

  function handleCartLoading(e) {
    const detail = e.detail || {};
    setCartLoadingState(true, detail.cartProductId);
  }

  function handleCartUpdated(e) {
    // Refresh the cart page content via AJAX
    refreshCartPage();
  }

  function handleCartError(e) {
    const detail = e.detail || {};
    console.error("Cart error:", detail.error);
    setCartLoadingState(false);
  }

  // ===== AJAX Cart Refresh =====

  function setCartLoadingState(isLoading, targetProductId) {
    const productsList = document.querySelector(selectors.productsList);

    if (isLoading) {
      // Add loading class to products list
      if (productsList) {
        productsList.classList.add("opacity-50");
        productsList.style.pointerEvents = "none";
        productsList.setAttribute("aria-busy", "true");
      }

      // Show spinner on specific product if provided
      if (targetProductId) {
        const productCard = document.querySelector('[data-cart-product-id="' + targetProductId + '"]');
        if (productCard) {
          productCard.classList.add("opacity-50");
        }
      }
    } else {
      // Remove loading state
      if (productsList) {
        productsList.classList.remove("opacity-50");
        productsList.style.pointerEvents = "";
        productsList.setAttribute("aria-busy", "false");
      }
    }
  }

  async function refreshCartPage() {
    if (state.isRefreshing) return;
    state.isRefreshing = true;

    try {
      const response = await fetch(window.location.href, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      if (!response.ok) {
        throw new Error("HTTP " + response.status);
      }

      const html = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");

      // Check if cart is now empty
      const newCartContainer = doc.querySelector(selectors.cartContainer);
      const currentCartContainer = document.querySelector(selectors.cartContainer);

      if (!newCartContainer && currentCartContainer) {
        // Cart is now empty - reload to show empty state
        window.location.reload();
        return;
      }

      // Swap products list
      swapElement(selectors.productsList, doc);

      // Swap order summary
      swapElement(selectors.orderSummary, doc);

      // Swap shipping progress
      swapElement(selectors.shippingProgress, doc);

      // Swap payment widgets
      swapElement(selectors.paymentWidgets, doc);

      // Re-initialize quantity inputs
      if (window.initQtyInputs) {
        window.initQtyInputs();
      }

      // Update cart badge in header
      if (window.cartManager && window.cartManager.refreshBadge) {
        window.cartManager.refreshBadge();
      }

      // Update payment widgets (Tamara, Tabby) and loyalty calculations
      updatePaymentWidgets();
      updateLoyaltyDisplay();

      // Dispatch event for other components
      window.dispatchEvent(new CustomEvent("cart-updated"));
    } catch (error) {
      console.error("Error refreshing cart:", error);
      // Fallback to page reload on error
      window.location.reload();
    } finally {
      state.isRefreshing = false;
      setCartLoadingState(false);
    }
  }

  function swapElement(selector, newDoc) {
    const currentEl = document.querySelector(selector);
    const newEl = newDoc.querySelector(selector);

    if (currentEl && newEl) {
      currentEl.innerHTML = newEl.innerHTML;
    }
  }

  /**
   * Update payment widgets (Tamara, Tabby) after cart changes
   */
  function updatePaymentWidgets() {
    const cartObj = window.cartObj;
    if (!cartObj || !cartObj.totals) return;

    const totalAmount = cartObj.totals.find(function (t) {
      return t.code === "total";
    });
    if (!totalAmount) return;

    // Update Tamara widget
    try {
      const tamaraWidget = document.querySelector("tamara-widget");
      if (tamaraWidget && window.TamaraWidgetV2) {
        tamaraWidget.setAttribute("amount", totalAmount.value);
        window.TamaraWidgetV2.refresh();
      }
    } catch (err) {
      console.error("Tamara update error:", err);
    }

    // Update Tabby widget
    try {
      const tabbyElm = document.querySelector(".tabby-cart-widget");
      if (tabbyElm && window.TabbyPromo) {
        window.TabbyPromo = new TabbyPromo.constructor({
          selector: ".tabby-cart-widget",
          currency: tabbyElm.getAttribute("data-currency"),
          lang: tabbyElm.getAttribute("data-lang"),
          price: totalAmount.value,
          installmentsCount: 4,
          source: "cart"
        });
      }
    } catch (err) {
      console.error("Tabby update error:", err);
    }
  }

  /**
   * Update loyalty points display after cart changes
   */
  function updateLoyaltyDisplay() {
    const cartObj = window.cartObj;
    if (!cartObj || !cartObj.totals) return;

    const totalAmount = cartObj.totals.find(function (t) {
      return t.code === "total";
    });
    if (!totalAmount) return;

    // Call system's loyalty calculation if available
    if (window.loyaltyCalculations) {
      window.loyaltyCalculations(totalAmount.value);
    }

    // Also recalculate using our method
    if (config.loyaltyEnabled) {
      calculateLoyaltyPoints(totalAmount.value);
    }
  }

  function applyCoupon() {
    const btn = document.querySelector("[data-coupon-submit-btn]");
    const text = document.querySelector("[data-coupon-submit-text]");
    const spinner = document.querySelector("[data-coupon-submit-spinner]");
    const input = document.querySelector("[data-coupon-input]");

    if (!input) return;
    if (btn && btn.disabled) return;

    // Show loading state
    if (btn) btn.disabled = true;
    if (text) text.classList.add("hidden");
    if (spinner) spinner.classList.remove("hidden");

    zid.cart
      .applyCoupon({ coupon_code: input.value.trim() }, { showErrorNotification: true })
      .then(function () {
        refreshCartPage();
      })
      .catch(function () {
        // Reset button state on error
        if (btn) btn.disabled = false;
        if (text) text.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");
        // Focus back on input for retry
        if (input) input.focus();
      });
  }

  function removeCoupon() {
    const btn = document.querySelector("[data-coupon-delete-btn]");
    const icon = document.querySelector("[data-coupon-delete-icon]");
    const spinner = document.querySelector("[data-coupon-delete-spinner]");

    if (btn && btn.disabled) return;

    if (btn) btn.disabled = true;
    if (icon) icon.classList.add("hidden");
    if (spinner) spinner.classList.remove("hidden");

    zid.cart
      .removeCoupons({ showErrorNotification: true })
      .then(function () {
        refreshCartPage();
      })
      .catch(function () {
        if (btn) btn.disabled = false;
        if (icon) icon.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");
      });
  }

  // ===== Gift Card Functions =====

  function handleGiftCardClick() {
    // Check if user is authenticated
    if (!window.customerAuthState || !window.customerAuthState.isAuthenticated) {
      handleLoginAction("", false);
      return;
    }

    // Open gift dialog
    if (window.gift_dialog && window.gift_dialog.open && typeof window.gift_dialog.open === "function") {
      window.gift_dialog.open();
    }
  }

  function editGiftCard() {
    handleGiftCardClick();
  }

  function deleteGiftCard() {
    const btn = document.querySelector("[data-gift-delete-btn]");
    const icon = document.querySelector("[data-gift-delete-icon]");
    const spinner = document.querySelector("[data-gift-delete-spinner]");

    // Show loading state
    if (icon) icon.classList.add("hidden");
    if (spinner) spinner.classList.remove("hidden");

    zid.cart
      .removeGiftCard({ showErrorNotification: true })
      .then(function () {
        // Hide gift card display in products list
        const giftCardDisplays = document.querySelectorAll("[data-gift-card-display]");
        giftCardDisplays.forEach(function (el) {
          el.classList.add("hidden");
        });

        // Toggle Add/Edit details links on gift button
        const addLink = document.querySelector("[data-gift-add-link]");
        const editLink = document.querySelector("[data-gift-edit-link]");
        if (addLink) addLink.classList.remove("hidden");
        if (editLink) editLink.classList.add("hidden");

        // Reset loading state
        if (icon) icon.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");
      })
      .catch(function (err) {
        console.error("Failed to remove gift card:", err);
        // Reset loading state
        if (icon) icon.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");
      });
  }

  function updateGiftCardDisplay(giftData) {
    if (!giftData) return;

    // Show gift card display in products list
    const giftCardDisplays = document.querySelectorAll("[data-gift-card-display]");
    giftCardDisplays.forEach(function (el) {
      el.classList.remove("hidden");
    });

    // Toggle Add/Edit details links on gift button
    const addLink = document.querySelector("[data-gift-add-link]");
    const editLink = document.querySelector("[data-gift-edit-link]");
    if (addLink) addLink.classList.add("hidden");
    if (editLink) editLink.classList.remove("hidden");

    // Update sender/receiver
    const senders = document.querySelectorAll("[data-gift-sender]");
    const receivers = document.querySelectorAll("[data-gift-receiver]");
    senders.forEach(function (el) {
      el.textContent = giftData.sender_name || "";
    });
    receivers.forEach(function (el) {
      el.textContent = giftData.receiver_name || "";
    });

    // Update gift message
    const messageEls = document.querySelectorAll("[data-gift-message]");
    messageEls.forEach(function (el) {
      if (giftData.gift_message) {
        el.textContent = giftData.gift_message;
        el.classList.remove("hidden");
      } else {
        el.classList.add("hidden");
      }
    });

    // Update media link
    const mediaLinkEls = document.querySelectorAll("[data-gift-media-link]");
    mediaLinkEls.forEach(function (el) {
      if (giftData.media_link) {
        el.textContent = giftData.media_link;
        el.classList.remove("hidden");
      } else {
        el.classList.add("hidden");
      }
    });

    // Update card design image
    const giftIcons = document.querySelectorAll("[data-gift-icon]");
    const giftImages = document.querySelectorAll("[data-gift-image]");
    if (giftData.card_design) {
      giftIcons.forEach(function (el) {
        el.classList.add("hidden");
      });
      giftImages.forEach(function (el) {
        el.src = giftData.card_design;
        el.classList.remove("hidden");
      });
    } else {
      giftIcons.forEach(function (el) {
        el.classList.remove("hidden");
      });
      giftImages.forEach(function (el) {
        el.classList.add("hidden");
      });
    }
  }

  // ===== Cart Updates (Platform Integration) =====

  /**
   * Called by Vitrin platform when cart products HTML changes
   * This is the callback for client-side cart updates
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
    updateCartTotals(cart);

    // Update free shipping progress
    updateFreeShippingProgress(cart);

    // Update cart badge
    if (window.cartManager) {
      window.cartManager.refreshBadge();
    }
  }

  function updateCartTotals(cart) {
    if (!cart || !cart.totals) return;

    const totalsContainer = document.querySelector("[data-cart-totals]");
    if (!totalsContainer) return;

    let totalsHtml = "";
    let totalRow = "";
    const itemsCountText = config.translations.itemsCount.replace("%(count)s", cart.products_count);
    const couponCode = cart.coupon?.code || "";
    const giftCardDetails = cart.gift_card_details;
    const loyaltyRedemption = cart.loyalty_applied_redemption_method;

    // Icons for discount section
    const couponIcon =
      '<svg class="text-muted size-4 shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M13.333 7.333V4.667A.667.667 0 0012.667 4h-10A.667.667 0 002 4.667v2.666a1.333 1.333 0 010 2.667v2.667c0 .368.299.666.667.666h10a.667.667 0 00.666-.666V9.333a1.333 1.333 0 010-2.667z" /></svg>';
    const giftCardIcon =
      '<svg class="text-muted size-4 shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M14 5.333h-1.82a2 2 0 00.153-.767 2 2 0 00-2-2c-.78 0-1.467.433-1.82 1.1L8 4.487l-.513-.82A2.005 2.005 0 005.667 2.566a2 2 0 00-2 2c0 .273.06.533.153.767H2a1.333 1.333 0 00-1.333 1.333V8c0 .367.3.667.666.667h.334v4c0 .733.6 1.333 1.333 1.333h10c.733 0 1.333-.6 1.333-1.333v-4h.334c.366 0 .666-.3.666-.667V6.667A1.333 1.333 0 0014 5.333zm-3.667-1.767a.667.667 0 01.667.667.667.667 0 01-.667.667H8.867l.666-1.067a.664.664 0 01.8-.267zm-4.666 0a.664.664 0 01.8.267l.666 1.067H5.667A.667.667 0 015 4.233a.667.667 0 01.667-.667z" /></svg>';
    const loyaltyIcon =
      '<svg class="text-muted size-4 shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1.333l1.987 4.027 4.446.647-3.217 3.133.76 4.427L8 11.387l-3.976 2.18.76-4.427-3.217-3.133 4.446-.647L8 1.333z" /></svg>';

    for (let i = 0; i < cart.totals.length; i++) {
      const total = cart.totals[i];

      if (total.code === "sub_totals") {
        totalsHtml +=
          '<div class="flex items-center justify-between gap-2">' +
          '<span class="text-foreground text-body2">' +
          total.title +
          ' <span class="text-muted" data-cart-items-count>. ' +
          itemsCountText +
          "</span></span>" +
          '<span class="text-foreground text-body2 shrink-0 text-end">' +
          total.value_string +
          "</span></div>";
      } else if (total.code === "shipping") {
        totalsHtml +=
          '<div class="flex items-center justify-between gap-2">' +
          '<span class="text-foreground text-body2">' +
          total.title +
          "</span>" +
          '<span class="text-foreground text-body2 shrink-0 text-end">' +
          total.value_string +
          "</span></div>";
      } else if (total.code === "discount" || total.code === "coupon_discount" || total.code === "products_discount") {
        let discountHtml =
          '<div class="flex flex-col gap-2">' +
          '<span class="text-foreground text-body2">' +
          config.translations.discount +
          "</span>";

        if (couponCode) {
          discountHtml +=
            '<div class="flex items-center gap-1">' +
            couponIcon +
            '<span class="text-muted text-body2 flex-1">' +
            couponCode +
            "</span>" +
            '<span class="text-success text-body2 shrink-0 text-end">-' +
            total.value_string +
            "</span></div>";
        } else {
          discountHtml +=
            '<div class="flex items-center justify-between gap-2">' +
            '<span class="text-muted text-body2">' +
            total.title +
            "</span>" +
            '<span class="text-success text-body2 shrink-0 text-end">-' +
            total.value_string +
            "</span></div>";
        }

        if (giftCardDetails && giftCardDetails.code) {
          discountHtml +=
            '<div class="flex items-center gap-1">' +
            giftCardIcon +
            '<span class="text-muted text-body2 flex-1">' +
            giftCardDetails.code +
            "</span>" +
            '<span class="text-success text-body2 shrink-0 text-end">-' +
            (giftCardDetails.amount_string || "") +
            "</span></div>";
        }

        if (loyaltyRedemption) {
          discountHtml +=
            '<div class="flex items-center gap-1">' +
            loyaltyIcon +
            '<span class="text-muted text-body2 flex-1">' +
            config.translations.loyalty +
            " " +
            loyaltyRedemption.points_to_redeem +
            "</span>" +
            '<span class="text-success text-body2 shrink-0 text-end">-' +
            loyaltyRedemption.reward.discount_amount +
            " " +
            (cart.currency?.cart_currency?.code || "") +
            "</span></div>";
        }

        discountHtml += "</div>";
        totalsHtml += discountHtml;
      } else if (total.code === "tax" || total.code === "vat") {
        totalsHtml +=
          '<div class="flex items-center justify-between gap-2">' +
          '<span class="text-foreground text-body2">' +
          total.title +
          "</span>" +
          '<span class="text-foreground text-body2 shrink-0 text-end">' +
          total.value_string +
          "</span></div>";
      } else if (total.code === "total") {
        totalRow =
          '<div class="flex items-center justify-between gap-2">' +
          '<span class="text-foreground text-subtitle1">' +
          total.title +
          "</span>" +
          '<span class="text-foreground text-subtitle1 shrink-0 text-end">' +
          total.value_string +
          "</span></div>";
      } else {
        totalsHtml +=
          '<div class="flex items-center justify-between gap-2">' +
          '<span class="text-foreground text-body2">' +
          total.title +
          "</span>" +
          '<span class="text-foreground text-body2 shrink-0 text-end">' +
          total.value_string +
          "</span></div>";
      }
    }

    totalsContainer.innerHTML = totalsHtml + totalRow;
  }

  function updateFreeShippingProgress(cart) {
    const freeShippingSection = document.querySelector("[data-free-shipping-bar]");
    if (!freeShippingSection) return;

    if (cart.free_shipping_rule) {
      freeShippingSection.classList.remove("hidden");
      const status = cart.free_shipping_rule.subtotal_condition?.status || "";
      const percentage = cart.free_shipping_rule.subtotal_condition?.products_subtotal_percentage_from_min || 0;

      // Update message
      const message = document.querySelector("[data-free-shipping-message]");
      if (message) {
        if (status === "applied") {
          message.textContent = config.translations.freeShippingApplied;
        } else if (status === "min_not_reached") {
          message.textContent = config.translations.addMoreForFreeShipping.replace(
            "%(total)s",
            cart.free_shipping_rule.subtotal_condition?.remaining || "0"
          );
        }
      }

      // Update progress bar
      const progressWrapper = document.querySelector("[data-free-shipping-progress-wrapper]");
      const progressBar = document.querySelector("[data-free-shipping-progress-bar]");
      const percentageText = document.querySelector("[data-free-shipping-percentage]");
      const successIndicator = document.querySelector("[data-free-shipping-success]");

      if (status === "applied") {
        if (progressWrapper) progressWrapper.classList.add("hidden");
        if (successIndicator) successIndicator.classList.remove("hidden");
      } else {
        if (progressWrapper) progressWrapper.classList.remove("hidden");
        if (successIndicator) successIndicator.classList.add("hidden");
        if (progressBar) progressBar.style.width = percentage + "%";
        if (percentageText) percentageText.textContent = percentage + "%";
      }
    } else {
      freeShippingSection.classList.add("hidden");
    }
  }

  // ===== Gift Card Event Listener =====
  window.addEventListener("vitrin:gift:submitted", function (event) {
    const giftData = event?.detail?.data?.gift_card_details;
    if (giftData) {
      updateGiftCardDisplay(giftData);
    }
  });

  // ===== Public API =====
  return {
    init: init,
    state: state,

    // Auth
    handleLoginAction: handleLoginAction,

    // Product operations
    toggleBundleItems: toggleBundleItems,
    updateQuantity: updateQuantity,

    // Loyalty
    applyLoyaltyRedemption: applyLoyaltyRedemption,
    removeLoyaltyRedemption: removeLoyaltyRedemption,

    // Coupon
    applyCoupon: applyCoupon,
    removeCoupon: removeCoupon,

    // Gift card
    editGiftCard: editGiftCard,
    deleteGiftCard: deleteGiftCard,
    handleGiftCardClick: handleGiftCardClick,

    // Platform integration
    cartProductsHtmlChanged: cartProductsHtmlChanged,

    // AJAX refresh
    refreshCartPage: refreshCartPage
  };
})();

// Global aliases for backward compatibility with existing onclick handlers
// These will be removed once all components use data-action attributes
window.toggleBundleItems = CartPage.toggleBundleItems;
window.updateCartQuantity = CartPage.updateQuantity;
window.handleLoginAction = CartPage.handleLoginAction;
window.applyLoyaltyRedemption = CartPage.applyLoyaltyRedemption;
window.removeLoyaltyRedemption = CartPage.removeLoyaltyRedemption;
window.sendCoupon = CartPage.applyCoupon;
window.deleteCoupon = CartPage.removeCoupon;
window.editGiftCard = CartPage.editGiftCard;
window.deleteGiftCard = CartPage.deleteGiftCard;
window.handleGiftCardClick = CartPage.handleGiftCardClick;
window.cartProductsHtmlChanged = CartPage.cartProductsHtmlChanged;
window.refreshCartPage = CartPage.refreshCartPage;
