/**
 * Notify Me Module
 *
 * Handles stock alert notifications for out-of-stock products.
 * Submits customer info to API for back-in-stock notifications.
 */
(function () {
  "use strict";

  // Track initialized forms to avoid double-init
  const initializedForms = new WeakSet();

  // Form elements (will be set during init)
  let form,
    productIdInput,
    nameInput,
    emailInput,
    countryCodeSelect,
    phoneInput,
    submitBtn,
    submitText,
    submitSpinner,
    dialog;

  // Show loading state
  function setLoading(loading) {
    if (submitBtn) submitBtn.disabled = loading;
    if (submitText) submitText.classList.toggle("hidden", loading);
    if (submitSpinner) submitSpinner.classList.toggle("hidden", !loading);
  }

  // Reset form
  function resetForm() {
    if (form) form.reset();
  }

  // Close dialog
  function closeDialog() {
    if (dialog && dialog.close) {
      dialog.close();
    }
  }

  // Show toast notification
  function showToast(message, type = "success") {
    // Use Zid's toast if available
    if (window.zid && window.zid.store && window.zid.store.showMessage) {
      window.zid.store.showMessage(message, type);
      return;
    }

    // Fallback: dispatch custom event for toast
    window.dispatchEvent(
      new CustomEvent("toast:show", {
        detail: { message, type }
      })
    );
  }

  // Submit stock alert
  async function submitStockAlert(e) {
    e.preventDefault();

    const productId = productIdInput?.value;
    const name = nameInput?.value?.trim();
    const email = emailInput?.value?.trim();
    const countryCode = countryCodeSelect?.value || "+966";
    const phone = phoneInput?.value?.trim();

    // Validation
    if (!name || !email) {
      showToast("Please fill in all required fields", "error");
      return;
    }

    // Build phone number
    const fullPhone = phone ? countryCode + phone : "";

    setLoading(true);

    try {
      // Get store permalink
      const storePermalink = window.location.origin + "/";

      // API request
      const response = await fetch(`${storePermalink}api/v1/products/${productId}/stock-alerts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json"
        },
        body: JSON.stringify({
          customer_name: name,
          customer_email: email,
          customer_phone_number: fullPhone || undefined
        })
      });

      if (response.ok) {
        showToast(window.notifyMeTranslations?.success || "You will be notified when this product is back in stock!");
        resetForm();
        closeDialog();
      } else {
        const data = await response.json().catch(() => ({}));
        const errorMsg = data.message || window.notifyMeTranslations?.error || "Failed to submit. Please try again.";
        showToast(errorMsg, "error");
      }
    } catch (error) {
      console.error("[NotifyMe] Error:", error);
      showToast(window.notifyMeTranslations?.error || "Failed to submit. Please try again.", "error");
    } finally {
      setLoading(false);
    }
  }

  // Auto-fill form with customer data if logged in
  function autoFillCustomerData(customer) {
    if (!customer) return;

    if (nameInput && customer.name) {
      nameInput.value = customer.name;
    }
    if (emailInput && customer.email) {
      emailInput.value = customer.email;
    }
    if (customer.mobile && customer.mobile.length > 3) {
      const countryCode = customer.mobile.substring(0, 4); // e.g., +966
      const phone = customer.mobile.substring(4);

      if (countryCodeSelect) {
        // Try to select matching country code
        const option = Array.from(countryCodeSelect.options).find((opt) => opt.value === countryCode);
        if (option) {
          countryCodeSelect.value = countryCode;
        }
      }
      if (phoneInput) {
        phoneInput.value = phone;
      }
    }
  }

  // Update product ID when variant changes
  function handleVariantChange(event) {
    const selectedProduct = event.detail?.selectedProduct;
    if (selectedProduct && productIdInput) {
      productIdInput.value = selectedProduct.id;
    }
  }

  // Initialize
  function init() {
    // Find form (may be dynamically loaded)
    form = document.querySelector("[data-notify-me-form]");
    if (!form || initializedForms.has(form)) return;

    // Mark as initialized
    initializedForms.add(form);

    // Query form elements
    productIdInput = document.querySelector("[data-notify-product-id]");
    nameInput = document.querySelector("[data-notify-name]");
    emailInput = document.querySelector("[data-notify-email]");
    countryCodeSelect = document.querySelector("[data-notify-country-code]");
    phoneInput = document.querySelector("[data-notify-phone]");
    submitBtn = document.querySelector("[data-notify-submit-btn]");
    submitText = document.querySelector("[data-notify-submit-text]");
    submitSpinner = document.querySelector("[data-notify-submit-spinner]");
    dialog = document.getElementById("notify-me-dialog");

    // Form submission
    form.addEventListener("submit", submitStockAlert);

    // Listen for variant changes to update product ID
    window.addEventListener("product:variant-changed", handleVariantChange);
  }

  // Listen for customer data (if user is logged in) - only once
  document.addEventListener("zid-customer-fetched", function (event) {
    const customer = event.detail?.customer;
    autoFillCustomerData(customer);
  });

  // Re-init when quick view content loads
  window.addEventListener("quick-view-content-loaded", init);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
