/**
 * Add to Cart Module
 *
 * Handles add-to-cart functionality for:
 * - Product cards (simple add with data-add-to-cart)
 * - Product page forms (data-add-to-cart-form)
 * - Variant add (data-add-variant-to-cart)
 * - Buy now (data-buy-now-form)
 *
 * Events:
 * - cart:updated - dispatched after cart changes
 */

import { showSpinner, hideSpinner } from "../utils/loading.js";
import { dispatch } from "../utils/events.js";
import { refreshBadge } from "./badge.js";

// Track initialized buttons
const initialized = new WeakSet();

/**
 * Wait for Zid SDK to be available
 */
async function waitForZid(maxAttempts = 20) {
  for (let i = 0; i < maxAttempts; i++) {
    if (window.zid) return true;
    await new Promise((r) => setTimeout(r, 100 * Math.min(i + 1, 10)));
  }
  console.error("[Cart] Zid SDK not available");
  return false;
}

/**
 * Simple add to cart (product cards without options)
 */
async function addToCart(btn) {
  const productId = btn.dataset.addToCart;
  if (!productId || btn.disabled) return;

  showSpinner(btn);

  try {
    await window.zid.cart.addProduct({ product_id: productId, quantity: 1 }, { showErrorNotification: true });

    dispatch("cart:updated", { productId, action: "add" });
    refreshBadge();
    showQuantityInput(productId, 1);
  } catch (err) {
    console.error("[Cart] Add to cart failed:", err);
  } finally {
    hideSpinner(btn);
  }
}

/**
 * Form-based add to cart (product page with variants/custom fields)
 * Supports bundle products via window.bundleCartPayload
 */
async function addToCartFromForm(btn) {
  const formId = btn.dataset.addToCartForm;
  if (!formId || btn.disabled) return;

  const originalContent = btn.innerHTML;
  showSpinner(btn, { replaceContent: true });

  try {
    // Check for bundle payload (set by vitrin:bundle-selections:updated event)
    const bundlePayload = window.bundleCartPayload;
    const addProductOptions = bundlePayload ? { ...bundlePayload, form_id: formId } : { form_id: formId };

    await window.zid.cart.addProduct(addProductOptions, { showErrorNotification: true });

    // Show success feedback
    const successIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    const successText = btn.dataset.successText || "Added!";
    btn.innerHTML = `${successIcon} ${successText}`;

    dispatch("cart:updated", { formId, action: "add" });
    refreshBadge();

    setTimeout(() => {
      btn.innerHTML = originalContent;
      btn.disabled = false;
    }, 1500);
  } catch (err) {
    console.error("[Cart] Add to cart failed:", err);
    btn.innerHTML = originalContent;
    btn.disabled = false;
  }
}

/**
 * Buy now - adds to cart and triggers checkout
 * Supports bundle products via window.bundleCartPayload
 */
async function buyNowFromForm(btn) {
  const formId = btn.dataset.buyNowForm;
  if (!formId || btn.disabled) return;

  showSpinner(btn, { replaceContent: true });

  try {
    // Check for bundle payload (set by vitrin:bundle-selections:updated event)
    const bundlePayload = window.bundleCartPayload;
    const buyNowOptions = bundlePayload ? { ...bundlePayload, form_id: formId } : { form_id: formId };

    await window.zid.cart.buyNow(buyNowOptions, { showErrorNotification: true });
    // buyNow handles redirect
  } catch (err) {
    console.error("[Cart] Buy now failed:", err);
    hideSpinner(btn);
  }
}

/**
 * Add variant to cart (product page variant list)
 */
async function addVariantToCart(btn) {
  const variantId = btn.dataset.addVariantToCart;
  if (!variantId || btn.disabled) return;

  const originalContent = btn.innerHTML;
  showSpinner(btn, { replaceContent: true });

  try {
    await window.zid.cart.addProduct({ product_id: variantId, quantity: 1 }, { showErrorNotification: true });

    // Show success feedback
    const successIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    const successText = btn.dataset.successText || "Added!";
    btn.innerHTML = `${successIcon} ${successText}`;

    dispatch("cart:updated", { variantId, action: "add" });
    refreshBadge();

    setTimeout(() => {
      btn.innerHTML = originalContent;
      btn.disabled = false;
    }, 1500);
  } catch (err) {
    console.error("[Cart] Add variant to cart failed:", err);
    btn.innerHTML = originalContent;
    btn.disabled = false;
  }
}

/**
 * Open quick view modal for products with options
 */
function openQuickView(btn) {
  const card = btn.closest("[data-product-card]");
  const link = card?.querySelector("a[href]");
  const productUrl = link?.getAttribute("href");

  if (!productUrl) {
    console.error("[Cart] Quick view: Could not find product URL");
    return;
  }

  const slug = productUrl.split("/p/")[1]?.split("?")[0] || "";

  if (window.quickViewManager) {
    window.quickViewManager.open(slug, productUrl);
  } else {
    window.location.href = productUrl;
  }
}

/**
 * Show quantity input and hide add button
 */
function showQuantityInput(productId, qty) {
  const card = document.querySelector(`[data-product-card="${productId}"]`);
  if (!card) return;

  const addBtn = card.querySelector("[data-add-to-cart]");
  const quickViewBtn = card.querySelector("[data-open-quick-view]");
  const qtySection = card.querySelector("[data-quantity-section]");

  if (addBtn) addBtn.hidden = true;
  if (quickViewBtn) quickViewBtn.hidden = true;

  if (qtySection) {
    qtySection.hidden = false;
    const wrapper = qtySection.querySelector("[data-qty-input]");
    if (wrapper) {
      const input = wrapper.querySelector("[data-qty-value]");
      if (input) input.value = qty;
    }

    // Re-init qty-input handlers
    if (window.initQtyInputs) window.initQtyInputs();
    initButtons(); // Re-init cart event listeners
  }
}

/**
 * Show add button and hide quantity input
 */
function showAddButton(productId) {
  const card = document.querySelector(`[data-product-card="${productId}"]`);
  if (!card) return;

  const addBtn = card.querySelector("[data-add-to-cart]");
  const quickViewBtn = card.querySelector("[data-open-quick-view]");
  const qtySection = card.querySelector("[data-quantity-section]");

  if (addBtn) addBtn.hidden = false;
  if (quickViewBtn) quickViewBtn.hidden = false;
  if (qtySection) qtySection.hidden = true;
}

/**
 * Find cart item by product ID
 */
async function findCartItem(productId) {
  const cart = await window.zid.cart.get();
  if (!cart?.products) return null;

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

/**
 * Handle qty:remove event from qty-input
 */
async function handleQtyRemove(wrapper) {
  const productId = wrapper.dataset.productId;
  if (!productId) return;

  const buttons = wrapper.querySelectorAll("button");
  const input = wrapper.querySelector("[data-qty-value]");

  buttons.forEach((b) => (b.disabled = true));
  if (input) input.disabled = true;

  try {
    const cartItem = await findCartItem(productId);
    if (!cartItem) throw new Error("Item not in cart");

    await window.zid.cart.removeProduct({ product_id: cartItem.id }, { showErrorNotification: true });

    dispatch("cart:updated", { productId, action: "remove" });
    showAddButton(productId);
    refreshBadge();
  } catch (err) {
    console.error("[Cart] Remove from cart failed:", err);
  } finally {
    buttons.forEach((b) => (b.disabled = false));
    if (input) input.disabled = false;
  }
}

/**
 * Handle qty:change event from qty-input
 */
async function handleQtyChange(wrapper, newQty) {
  const productId = wrapper.dataset.productId;
  if (!productId) return;

  const buttons = wrapper.querySelectorAll("button");
  const input = wrapper.querySelector("[data-qty-value]");

  buttons.forEach((b) => (b.disabled = true));
  if (input) input.disabled = true;

  try {
    const cartItem = await findCartItem(productId);
    if (!cartItem) throw new Error("Item not in cart");

    await window.zid.cart.updateProduct({ product_id: cartItem.id, quantity: newQty }, { showErrorNotification: true });

    dispatch("cart:updated", { productId, action: "update", quantity: newQty });
    refreshBadge();
  } catch (err) {
    console.error("[Cart] Update quantity failed:", err);
  } finally {
    buttons.forEach((b) => (b.disabled = false));
    if (input) input.disabled = false;
  }
}

/**
 * Initialize all cart buttons
 */
export function initButtons() {
  // Simple add to cart buttons
  document.querySelectorAll("[data-add-to-cart]").forEach((btn) => {
    if (initialized.has(btn)) return;
    initialized.add(btn);
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      addToCart(btn);
    });
  });

  // Quick view buttons
  document.querySelectorAll("[data-open-quick-view]").forEach((btn) => {
    if (initialized.has(btn)) return;
    initialized.add(btn);
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      openQuickView(btn);
    });
  });

  // Form-based add to cart
  document.querySelectorAll("[data-add-to-cart-form]").forEach((btn) => {
    if (initialized.has(btn)) return;
    initialized.add(btn);
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      addToCartFromForm(btn);
    });
  });

  // Buy now buttons
  document.querySelectorAll("[data-buy-now-form]").forEach((btn) => {
    if (initialized.has(btn)) return;
    initialized.add(btn);
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      buyNowFromForm(btn);
    });
  });

  // Variant add to cart
  document.querySelectorAll("[data-add-variant-to-cart]").forEach((btn) => {
    if (initialized.has(btn)) return;
    initialized.add(btn);
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      addVariantToCart(btn);
    });
  });

  // Qty input events (for product cards)
  document.querySelectorAll("[data-qty-input]").forEach((wrapper) => {
    if (initialized.has(wrapper)) return;
    initialized.add(wrapper);

    wrapper.addEventListener("qty:remove", () => handleQtyRemove(wrapper));
    wrapper.addEventListener("qty:change", (e) => handleQtyChange(wrapper, e.detail.value));
  });
}

/**
 * Sync cart state with UI on load
 */
async function syncCartState() {
  try {
    const cart = await window.zid.cart.get();
    if (!cart?.products?.length) return;

    const normalize = (id) =>
      String(id || "")
        .replace(/-/g, "")
        .toLowerCase();

    cart.products.forEach((item) => {
      const productId = item.product?.id || item.product_id;
      const qty = item.quantity || 1;

      document.querySelectorAll("[data-product-card]").forEach((card) => {
        if (normalize(card.dataset.productCard) === normalize(productId)) {
          showQuantityInput(card.dataset.productCard, qty);
        }
      });
    });
  } catch (err) {
    console.error("[Cart] Sync cart state failed:", err);
  }
}

/**
 * Initialize bundle selection listener
 * Handles dynamic bundle products from vitrin:products/bundle-products.jinja
 */
function initBundleSelectionListener() {
  window.addEventListener("vitrin:bundle-selections:updated", (event) => {
    const cartData = event?.detail?.data;
    const bundlePayload = cartData?.cartPayload;
    const isValid = cartData?.isSelectionsValid;

    // Store bundle payload globally for add-to-cart
    window.bundleCartPayload = bundlePayload;

    // Enable/disable add-to-cart buttons based on bundle validity
    const addToCartBtns = document.querySelectorAll("[data-add-to-cart-form]");
    const buyNowBtns = document.querySelectorAll("[data-buy-now-form]");

    addToCartBtns.forEach((btn) => {
      btn.disabled = !isValid;
      if (!isValid) {
        btn.classList.add("opacity-50", "cursor-not-allowed");
      } else {
        btn.classList.remove("opacity-50", "cursor-not-allowed");
      }
    });

    buyNowBtns.forEach((btn) => {
      btn.disabled = !isValid;
      if (!isValid) {
        btn.classList.add("opacity-50", "cursor-not-allowed");
      } else {
        btn.classList.remove("opacity-50", "cursor-not-allowed");
      }
    });
  });
}

/**
 * Initialize cart module
 */
export async function initCart() {
  const ready = await waitForZid();
  if (!ready) return;

  initButtons();
  initBundleSelectionListener();
  refreshBadge();
  syncCartState();
}
