/**
 * Cart Coupon Module
 *
 * Handles coupon apply/remove operations on the cart page.
 */

/**
 * Setup coupon input - enable/disable button based on input value
 */
export function setupCouponInput() {
  const couponInput = document.querySelector("[data-coupon-input]");
  const couponBtn = document.querySelector("[data-coupon-submit-btn]");

  if (couponInput && couponBtn) {
    couponInput.addEventListener("input", (e) => {
      couponBtn.disabled = !e.target.value.trim();
    });
  }
}

/**
 * Apply coupon code
 * @param {Function} onSuccess - Callback after successful apply (typically refreshCartPage)
 */
export function applyCoupon(onSuccess) {
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

  window.zid.cart
    .applyCoupon({ coupon_code: input.value.trim() }, { showErrorNotification: true })
    .then(() => {
      if (onSuccess) onSuccess();
    })
    .catch(() => {
      // Reset button state on error
      if (btn) btn.disabled = false;
      if (text) text.classList.remove("hidden");
      if (spinner) spinner.classList.add("hidden");
      // Focus back on input for retry
      if (input) input.focus();
    });
}

/**
 * Remove applied coupon
 * @param {Function} onSuccess - Callback after successful remove (typically refreshCartPage)
 */
export function removeCoupon(onSuccess) {
  const btn = document.querySelector("[data-coupon-delete-btn]");
  const icon = document.querySelector("[data-coupon-delete-icon]");
  const spinner = document.querySelector("[data-coupon-delete-spinner]");

  if (btn && btn.disabled) return;

  if (btn) btn.disabled = true;
  if (icon) icon.classList.add("hidden");
  if (spinner) spinner.classList.remove("hidden");

  window.zid.cart
    .removeCoupons({ showErrorNotification: true })
    .then(() => {
      if (onSuccess) onSuccess();
    })
    .catch(() => {
      if (btn) btn.disabled = false;
      if (icon) icon.classList.remove("hidden");
      if (spinner) spinner.classList.add("hidden");
    });
}
