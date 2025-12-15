/**
 * Cart Manager
 *
 * Usage:
 *
 * 1. Simple add-to-cart (product cards without options):
 *    <button data-add-to-cart="product-uuid">Add to cart</button>
 *
 * 2. Quick view (product cards with options):
 *    <button data-open-quick-view="true" data-product-id="uuid">Select options</button>
 *
 * 3. Form-based add-to-cart (product page with custom fields):
 *    <button data-add-to-cart-form="product-form">Add to cart</button>
 *
 * 4. Buy Now (form-based):
 *    <button data-buy-now-form="product-form">Buy now</button>
 *
 * 5. Quantity controls:
 *    <div data-quantity-input data-product-id="uuid" data-quantity="1">...</div>
 *
 * Events:
 * - cart:updated - dispatched after cart changes
 * - products:updated - listen to re-init buttons after AJAX
 */

const SPINNER = `<svg class="size-5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`;

class CartManager {
  constructor() {
    this.init();
  }

  async init() {
    await this.waitForZid();
    this.initButtons();
    this.initCart();

    // Re-init buttons when products are updated (AJAX filtering)
    window.addEventListener("products:updated", () => this.initButtons());

    // Re-init buttons when quick view modal loads content
    window.addEventListener("quick-view-content-loaded", () => this.initButtons());
  }

  // Fetch cart on load and update UI
  async initCart() {
    try {
      const cart = await window.zid.cart.get();
      if (!cart) return;

      // Update badge
      const count = cart.cart_items_quantity ?? cart.products_count ?? 0;
      document.querySelectorAll("[data-cart-badge]").forEach((el) => {
        el.textContent = count;
        el.hidden = count === 0;
      });

      // Show quantity inputs for products already in cart
      if (cart.products?.length) {
        const normalize = (id) =>
          String(id || "")
            .replace(/-/g, "")
            .toLowerCase();

        cart.products.forEach((item) => {
          const productId = item.product?.id || item.product_id;
          const qty = item.quantity || 1;

          // Find product card by normalized ID
          document.querySelectorAll("[data-product-card]").forEach((card) => {
            if (normalize(card.dataset.productCard) === normalize(productId)) {
              this.showQuantityInput(card.dataset.productCard, qty);
            }
          });
        });
      }
    } catch (err) {
      console.error("Init cart failed:", err);
    }
  }

  async waitForZid(maxAttempts = 20) {
    for (let i = 0; i < maxAttempts; i++) {
      if (window.zid) return true;
      await new Promise((r) => setTimeout(r, 100 * Math.min(i + 1, 10)));
    }
    console.error("Zid SDK not available");
    return false;
  }

  initButtons() {
    // Simple add to cart buttons (product cards)
    document.querySelectorAll("[data-add-to-cart]").forEach((btn) => {
      if (btn.dataset.cartInit) return;
      btn.dataset.cartInit = "true";

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        this.addToCart(btn);
      });
    });

    // Quick view buttons (products with options)
    document.querySelectorAll("[data-open-quick-view]").forEach((btn) => {
      if (btn.dataset.cartInit) return;
      btn.dataset.cartInit = "true";

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        this.openQuickView(btn);
      });
    });

    // Form-based add to cart buttons (product page)
    document.querySelectorAll("[data-add-to-cart-form]").forEach((btn) => {
      if (btn.dataset.cartInit) return;
      btn.dataset.cartInit = "true";

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        this.addToCartFromForm(btn);
      });
    });

    // Buy now buttons (form-based)
    document.querySelectorAll("[data-buy-now-form]").forEach((btn) => {
      if (btn.dataset.cartInit) return;
      btn.dataset.cartInit = "true";

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        this.buyNowFromForm(btn);
      });
    });

    // Quantity action buttons (increase, decrease, remove)
    document.querySelectorAll("[data-quantity-action]").forEach((btn) => {
      if (btn.dataset.cartInit) return;
      btn.dataset.cartInit = "true";

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        this.handleQuantityAction(btn);
      });
    });

    // Variant add to cart buttons (product page variant list)
    document.querySelectorAll("[data-add-variant-to-cart]").forEach((btn) => {
      if (btn.dataset.cartInit) return;
      btn.dataset.cartInit = "true";

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        this.addVariantToCart(btn);
      });
    });
  }

  // ─────────────────────────────────────────────────────────────
  // Add to Cart
  // ─────────────────────────────────────────────────────────────

  /**
   * Simple add to cart (product cards)
   */
  async addToCart(btn) {
    const productId = btn.dataset.addToCart;
    if (!productId || btn.disabled) return;

    const originalContent = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = SPINNER;

    try {
      await window.zid.cart.addProduct({ product_id: productId, quantity: 1 }, { showErrorNotification: true });

      window.dispatchEvent(new CustomEvent("cart:updated", { detail: { productId, action: "add" } }));
      this.refreshBadge();
      this.showQuantityInput(productId, 1);
    } catch (err) {
      console.error("Add to cart failed:", err);
    } finally {
      btn.innerHTML = originalContent;
      btn.disabled = false;
    }
  }

  /**
   * Form-based add to cart (product page with variants/custom fields)
   */
  async addToCartFromForm(btn) {
    const formId = btn.dataset.addToCartForm;
    if (!formId || btn.disabled) return;

    const originalContent = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = SPINNER;

    try {
      await window.zid.cart.addProduct({ form_id: formId }, { showErrorNotification: true });

      // Show success feedback briefly
      const successIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
      const successText = btn.dataset.successText || "Added!";
      btn.innerHTML = `${successIcon} ${successText}`;

      window.dispatchEvent(new CustomEvent("cart:updated", { detail: { formId, action: "add" } }));
      this.refreshBadge();

      setTimeout(() => {
        btn.innerHTML = originalContent;
        btn.disabled = false;
      }, 1500);
    } catch (err) {
      console.error("Add to cart failed:", err);
      btn.innerHTML = originalContent;
      btn.disabled = false;
    }
  }

  /**
   * Buy now - adds to cart and triggers checkout
   */
  async buyNowFromForm(btn) {
    const formId = btn.dataset.buyNowForm;
    if (!formId || btn.disabled) return;

    const originalContent = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = SPINNER;

    try {
      await window.zid.cart.buyNow({ form_id: formId }, { showErrorNotification: true });
      // buyNow handles the redirect, so we don't need to restore button
    } catch (err) {
      console.error("Buy now failed:", err);
      btn.innerHTML = originalContent;
      btn.disabled = false;
    }
  }

  /**
   * Add variant to cart (product page variant list)
   */
  async addVariantToCart(btn) {
    const variantId = btn.dataset.addVariantToCart;
    if (!variantId || btn.disabled) return;

    const originalContent = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = SPINNER;

    try {
      await window.zid.cart.addProduct({ product_id: variantId, quantity: 1 }, { showErrorNotification: true });

      // Show success feedback briefly
      const successIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
      const successText = btn.dataset.successText || "Added!";
      btn.innerHTML = `${successIcon} ${successText}`;

      window.dispatchEvent(new CustomEvent("cart:updated", { detail: { variantId, action: "add" } }));
      this.refreshBadge();

      setTimeout(() => {
        btn.innerHTML = originalContent;
        btn.disabled = false;
      }, 1500);
    } catch (err) {
      console.error("Add variant to cart failed:", err);
      btn.innerHTML = originalContent;
      btn.disabled = false;
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Quick View
  // ─────────────────────────────────────────────────────────────

  /**
   * Open quick view modal for products with options
   */
  openQuickView(btn) {
    // Get product URL from the card's link
    const card = btn.closest("[data-product-card]");
    const link = card?.querySelector("a[href]");
    const productUrl = link?.getAttribute("href");

    if (!productUrl) {
      console.error("Quick view: Could not find product URL");
      return;
    }

    // Extract slug from URL (e.g., /p/product-slug -> product-slug)
    const slug = productUrl.split("/p/")[1]?.split("?")[0] || "";

    // Open the quick view modal
    if (window.quickViewManager) {
      window.quickViewManager.open(slug, productUrl);
    } else {
      // Fallback: navigate to product page
      window.location.href = productUrl;
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Quantity Actions
  // ─────────────────────────────────────────────────────────────
  async handleQuantityAction(btn) {
    const wrapper = btn.closest("[data-quantity-input]");
    if (!wrapper) return;

    const action = btn.dataset.quantityAction;
    if (!["increase", "decrease", "remove"].includes(action)) return;

    const productId = wrapper.dataset.productId;
    const currentQty = parseInt(wrapper.dataset.quantity) || 1;

    // Disable buttons and show spinner
    const buttons = wrapper.querySelectorAll("button");
    const display = wrapper.querySelector("[data-quantity-display]");
    const originalDisplay = display?.innerHTML;

    buttons.forEach((b) => (b.disabled = true));
    if (display) display.innerHTML = SPINNER;

    try {
      if (action === "increase") {
        await this.updateQuantity(productId, currentQty + 1);
        this.updateQuantityUI(wrapper, currentQty + 1);
      } else if (action === "decrease" && currentQty > 1) {
        await this.updateQuantity(productId, currentQty - 1);
        this.updateQuantityUI(wrapper, currentQty - 1);
      } else if (action === "remove") {
        await this.removeFromCart(productId);
        this.showAddButton(productId);
      }

      this.refreshBadge();
    } catch (err) {
      console.error("Quantity action failed:", err);
      // Restore original display on error
      if (display) display.innerHTML = originalDisplay;
    } finally {
      buttons.forEach((b) => (b.disabled = false));
    }
  }

  async updateQuantity(productId, quantity) {
    const cartItem = await this.findCartItem(productId);
    if (!cartItem) throw new Error("Item not in cart");

    await window.zid.cart.updateProduct({ product_id: cartItem.id, quantity }, { showErrorNotification: true });
    window.dispatchEvent(new CustomEvent("cart:updated", { detail: { productId, action: "update", quantity } }));
  }

  async removeFromCart(productId) {
    const cartItem = await this.findCartItem(productId);
    if (!cartItem) throw new Error("Item not in cart");

    await window.zid.cart.removeProduct({ product_id: cartItem.id }, { showErrorNotification: true });
    window.dispatchEvent(new CustomEvent("cart:updated", { detail: { productId, action: "remove" } }));
  }

  async findCartItem(productId) {
    const cart = await window.zid.cart.get();
    if (!cart?.products) return null;

    // Normalize UUIDs (remove dashes, lowercase) for comparison
    const normalize = (id) =>
      String(id || "")
        .replace(/-/g, "")
        .toLowerCase();
    const targetId = normalize(productId);

    return cart.products.find((item) => {
      const id = item.product?.id || item.product_id;
      return normalize(id) === targetId;
    });
  }

  // ─────────────────────────────────────────────────────────────
  // UI Updates
  // ─────────────────────────────────────────────────────────────
  updateQuantityUI(wrapper, qty) {
    wrapper.dataset.quantity = qty;

    const display = wrapper.querySelector("[data-quantity-display]");
    if (display) display.textContent = qty;

    // Toggle delete/minus visibility
    const removeBtn = wrapper.querySelector('[data-quantity-action="remove"]');
    const decreaseBtn = wrapper.querySelector('[data-quantity-action="decrease"]');

    if (removeBtn) removeBtn.hidden = qty > 1;
    if (decreaseBtn) decreaseBtn.hidden = qty === 1;
  }

  showQuantityInput(productId, qty) {
    const card = document.querySelector(`[data-product-card="${productId}"]`);
    if (!card) return;

    const addBtn = card.querySelector("[data-add-to-cart]");
    const quickViewBtn = card.querySelector("[data-open-quick-view]");
    const qtySection = card.querySelector("[data-quantity-section]");

    if (addBtn) addBtn.hidden = true;
    if (quickViewBtn) quickViewBtn.hidden = true;
    if (qtySection) {
      qtySection.hidden = false;
      const wrapper = qtySection.querySelector("[data-quantity-input]");
      if (wrapper) this.updateQuantityUI(wrapper, qty);
      this.initButtons(); // Init new quantity buttons
    }
  }

  showAddButton(productId) {
    const card = document.querySelector(`[data-product-card="${productId}"]`);
    if (!card) return;

    const addBtn = card.querySelector("[data-add-to-cart]");
    const quickViewBtn = card.querySelector("[data-open-quick-view]");
    const qtySection = card.querySelector("[data-quantity-section]");

    if (addBtn) addBtn.hidden = false;
    if (quickViewBtn) quickViewBtn.hidden = false;
    if (qtySection) qtySection.hidden = true;
  }

  async refreshBadge() {
    try {
      const cart = await window.zid.cart.get();
      const count = cart?.cart_items_quantity ?? cart?.products_count ?? 0;

      document.querySelectorAll("[data-cart-badge]").forEach((el) => {
        el.textContent = count;
        el.hidden = count === 0;
      });
    } catch (err) {
      console.error("Refresh badge failed:", err);
    }
  }
}

window.cartManager = new CartManager();
