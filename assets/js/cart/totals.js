/**
 * Cart Totals Module
 *
 * Handles rendering of cart totals and free shipping progress bar.
 */

// SVG icons for discount section
const ICONS = {
  coupon: `<svg class="text-muted size-4 shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M13.333 7.333V4.667A.667.667 0 0012.667 4h-10A.667.667 0 002 4.667v2.666a1.333 1.333 0 010 2.667v2.667c0 .368.299.666.667.666h10a.667.667 0 00.666-.666V9.333a1.333 1.333 0 010-2.667z" /></svg>`,
  giftCard: `<svg class="text-muted size-4 shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M14 5.333h-1.82a2 2 0 00.153-.767 2 2 0 00-2-2c-.78 0-1.467.433-1.82 1.1L8 4.487l-.513-.82A2.005 2.005 0 005.667 2.566a2 2 0 00-2 2c0 .273.06.533.153.767H2a1.333 1.333 0 00-1.333 1.333V8c0 .367.3.667.666.667h.334v4c0 .733.6 1.333 1.333 1.333h10c.733 0 1.333-.6 1.333-1.333v-4h.334c.366 0 .666-.3.666-.667V6.667A1.333 1.333 0 0014 5.333zm-3.667-1.767a.667.667 0 01.667.667.667.667 0 01-.667.667H8.867l.666-1.067a.664.664 0 01.8-.267zm-4.666 0a.664.664 0 01.8.267l.666 1.067H5.667A.667.667 0 015 4.233a.667.667 0 01.667-.667z" /></svg>`,
  loyalty: `<svg class="text-muted size-4 shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1.333l1.987 4.027 4.446.647-3.217 3.133.76 4.427L8 11.387l-3.976 2.18.76-4.427-3.217-3.133 4.446-.647L8 1.333z" /></svg>`
};

/**
 * Update cart totals display
 * @param {Object} cart - Cart object from API
 * @param {Object} config - Configuration object with translations
 */
export function updateCartTotals(cart, config) {
  if (!cart || !cart.totals) return;

  const totalsContainer = document.querySelector("[data-cart-totals]");
  if (!totalsContainer) return;

  const translations = config?.translations || {};
  const itemsCountText = (translations.itemsCount || "%(count)s items").replace("%(count)s", cart.products_count);
  const couponCode = cart.coupon?.code || "";
  const giftCardDetails = cart.gift_card_details;
  const loyaltyRedemption = cart.loyalty_applied_redemption_method;

  let totalsHtml = "";
  let totalRow = "";

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
        (translations.discount || "Discount") +
        "</span>";

      if (couponCode) {
        discountHtml +=
          '<div class="flex items-center gap-1">' +
          ICONS.coupon +
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
          ICONS.giftCard +
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
          ICONS.loyalty +
          '<span class="text-muted text-body2 flex-1">' +
          (translations.loyalty || "Loyalty") +
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

/**
 * Update free shipping progress bar
 * @param {Object} cart - Cart object from API
 * @param {Object} config - Configuration object with translations
 */
export function updateFreeShippingProgress(cart, config) {
  const freeShippingSection = document.querySelector("[data-free-shipping-bar]");
  if (!freeShippingSection) return;

  const translations = config?.translations || {};

  if (cart.free_shipping_rule) {
    freeShippingSection.classList.remove("hidden");
    const status = cart.free_shipping_rule.subtotal_condition?.status || "";
    const percentage = cart.free_shipping_rule.subtotal_condition?.products_subtotal_percentage_from_min || 0;

    // Update message
    const message = document.querySelector("[data-free-shipping-message]");
    if (message) {
      if (status === "applied") {
        message.textContent = translations.freeShippingApplied || "Free shipping applied!";
      } else if (status === "min_not_reached") {
        const template = translations.addMoreForFreeShipping || "Add %(total)s more to get free shipping";
        message.textContent = template.replace(
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

/**
 * Update payment widgets (Tamara, Tabby) after cart changes
 */
export function updatePaymentWidgets() {
  const cartObj = window.cartObj;
  if (!cartObj || !cartObj.totals) return;

  const totalAmount = cartObj.totals.find((t) => t.code === "total");
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
 * @param {Object} config - Configuration object
 */
export function updateLoyaltyDisplay(config) {
  const cartObj = window.cartObj;
  if (!cartObj || !cartObj.totals) return;

  const totalAmount = cartObj.totals.find((t) => t.code === "total");
  if (!totalAmount) return;

  // Call system's loyalty calculation if available
  if (window.loyaltyCalculations) {
    window.loyaltyCalculations(totalAmount.value);
  }
}
