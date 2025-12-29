/**
 * Quantity Input Module
 *
 * Handles all quantity inputs with +/- buttons.
 * Supports syncing between multiple inputs.
 *
 * Data attributes:
 *   - data-qty-input="<id>"     : Wrapper element with input ID
 *   - data-qty-sync="<id>"      : ID of another input to sync with
 *   - data-qty-action="increase|decrease|remove" : Button actions
 *   - data-qty-value            : The input element
 *
 * Events:
 *   - qty:change : Dispatched on input when value changes
 *   - qty:remove : Dispatched on wrapper when remove is clicked
 */

// Track initialized wrappers to avoid double-init
const initializedWrappers = new WeakSet();

function updateQuantity(wrapper, delta) {
  const input = wrapper.querySelector("[data-qty-value]");
  if (!input) return;

  const current = parseInt(input.value) || 1;
  const min = parseInt(input.min) || 1;
  const max = input.max ? parseInt(input.max) : Infinity;

  const newValue = Math.max(min, Math.min(max, current + delta));

  if (newValue !== current) {
    input.value = newValue;
    input.dispatchEvent(new Event("change", { bubbles: true }));
    dispatchQtyChange(wrapper, newValue);
  }
}

function dispatchQtyChange(wrapper, value) {
  const id = wrapper.dataset.qtyInput;
  wrapper.dispatchEvent(
    new CustomEvent("qty:change", {
      bubbles: true,
      detail: { id, value }
    })
  );
}

function syncWithTarget(wrapper, value) {
  const targetId = wrapper.dataset.qtySync;
  if (!targetId) return;

  const targetWrapper = document.querySelector(`[data-qty-input="${targetId}"]`);
  if (!targetWrapper) return;

  const targetInput = targetWrapper.querySelector("[data-qty-value]");
  if (targetInput && parseInt(targetInput.value) !== value) {
    targetInput.value = value;
  }
}

function updateButtonVisibility(wrapper, value) {
  const deleteBtn = wrapper.querySelector('[data-qty-action="remove"]');
  const decreaseBtn = wrapper.querySelector('[data-qty-action="decrease"]');

  if (deleteBtn && decreaseBtn) {
    deleteBtn.hidden = value > 1;
    decreaseBtn.hidden = value <= 1;
  }
}

function handleInputChange(wrapper, input) {
  const value = parseInt(input.value) || 1;
  const min = parseInt(input.min) || 1;
  const max = input.max ? parseInt(input.max) : Infinity;

  const clampedValue = Math.max(min, Math.min(max, value));
  if (clampedValue !== value) {
    input.value = clampedValue;
  }

  updateButtonVisibility(wrapper, clampedValue);
  syncWithTarget(wrapper, clampedValue);
  dispatchQtyChange(wrapper, clampedValue);
}

function initWrapper(wrapper) {
  if (initializedWrappers.has(wrapper)) return;
  initializedWrappers.add(wrapper);

  const input = wrapper.querySelector("[data-qty-value]");
  const buttons = wrapper.querySelectorAll("[data-qty-action]");

  if (input) {
    const initialValue = parseInt(input.value) || 1;
    updateButtonVisibility(wrapper, initialValue);
  }

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.qtyAction;

      if (action === "increase") {
        updateQuantity(wrapper, 1);
      } else if (action === "decrease") {
        updateQuantity(wrapper, -1);
      } else if (action === "remove") {
        wrapper.dispatchEvent(new CustomEvent("qty:remove", { bubbles: true }));
      }
    });
  });

  if (input) {
    input.addEventListener("change", () => handleInputChange(wrapper, input));
    input.addEventListener("input", () => handleInputChange(wrapper, input));
  }
}

function initAll() {
  document.querySelectorAll("[data-qty-input]").forEach(initWrapper);
}

// ─────────────────────────────────────────────────────────────
// Global Functions
// ─────────────────────────────────────────────────────────────

window.updateQtyMax = function (inputId, maxValue) {
  const wrapper = document.querySelector(`[data-qty-input="${inputId}"]`);
  if (!wrapper) return;

  const input = wrapper.querySelector("[data-qty-value]");
  if (!input) return;

  input.max = maxValue;

  const current = parseInt(input.value) || 1;
  if (current > maxValue) {
    input.value = maxValue;
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }
};

window.initQtyInputs = initAll;

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  initAll();

  window.addEventListener("products-updated", initAll);
  window.addEventListener("content:loaded", initAll);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

export { initAll };
