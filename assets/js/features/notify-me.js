/**
 * Notify Me Module
 *
 * Handles stock alert notifications for out-of-stock products.
 * Submits customer info to API for back-in-stock notifications.
 */

// Track initialized forms to avoid double-init
const initializedForms = new WeakSet();

// Form elements (will be set during init)
let form, productIdInput, nameInput, emailInput, phoneInputWrapper, submitBtn, submitText, submitSpinner, dialog;

function setLoading(loading) {
  if (submitBtn) submitBtn.disabled = loading;
  if (submitText) submitText.classList.toggle("hidden", loading);
  if (submitSpinner) submitSpinner.classList.toggle("hidden", !loading);
}

function resetForm() {
  if (form) form.reset();
}

function closeDialog() {
  if (dialog && dialog.close) {
    dialog.close();
  }
}

function showToast(message, type = "success") {
  if (window.zid && window.zid.store && window.zid.store.showMessage) {
    window.zid.store.showMessage(message, type);
    return;
  }

  window.dispatchEvent(
    new CustomEvent("toast:show", {
      detail: { message, type }
    })
  );
}

function getPhoneValidationMessage(errorCode) {
  const messages = window.notifyMeTranslations || {};
  switch (errorCode) {
    case "EMPTY":
      return messages.phoneRequired || "Phone number is required";
    case "TOO_SHORT":
      return messages.phoneTooShort || "Phone number is too short";
    case "TOO_LONG":
      return messages.phoneTooLong || "Phone number is too long";
    case "INVALID_LENGTH":
      return messages.phoneInvalid || "Invalid phone number length";
    case "INVALID_COUNTRY":
      return messages.phoneInvalidCountry || "Invalid country code";
    default:
      return messages.phoneInvalid || "Invalid phone number";
  }
}

function setPhoneError(hasError) {
  if (phoneInputWrapper) {
    if (hasError) {
      phoneInputWrapper.setAttribute("data-error", "true");
    } else {
      phoneInputWrapper.removeAttribute("data-error");
    }
  }
}

async function submitStockAlert(e) {
  e.preventDefault();

  const productId = productIdInput?.value;
  const name = nameInput?.value?.trim();
  const email = emailInput?.value?.trim();

  let fullPhone = "";
  let phoneApi = null;
  if (phoneInputWrapper) {
    phoneApi = phoneInputWrapper._phoneInput;
    if (phoneApi) {
      fullPhone = phoneApi.getValue();
    } else {
      const fullValueInput = phoneInputWrapper.querySelector("[data-phone-full-value]");
      fullPhone = fullValueInput?.value || "";
    }
  }

  if (!name || !email) {
    showToast(window.notifyMeTranslations?.required || "Please fill in all required fields", "error");
    return;
  }

  if (phoneApi) {
    const phoneNumber = phoneApi.getPhoneNumber();
    if (phoneNumber) {
      const validationError = phoneApi.validate();
      if (validationError && validationError !== "EMPTY") {
        setPhoneError(true);
        showToast(getPhoneValidationMessage(validationError), "error");
        return;
      }
      setPhoneError(false);
    }
  }

  setLoading(true);

  try {
    const storePermalink = window.location.origin + "/";

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

function autoFillCustomerData(customer) {
  if (!customer) return;

  if (nameInput && customer.name) {
    nameInput.value = customer.name;
  }
  if (emailInput && customer.email) {
    emailInput.value = customer.email;
  }
  if (customer.mobile && customer.mobile.length > 3 && phoneInputWrapper) {
    let countryCode = "";
    let phone = customer.mobile;

    const match = customer.mobile.match(/^(\+\d{1,4})/);
    if (match) {
      countryCode = match[1];
      phone = customer.mobile.substring(countryCode.length);
    }

    const phoneApi = phoneInputWrapper._phoneInput;
    if (phoneApi) {
      if (countryCode) phoneApi.setDialCode(countryCode);
      phoneApi.setPhoneNumber(phone);
    }
  }
}

function handleVariantChange(event) {
  const selectedProduct = event.detail?.selectedProduct;
  if (selectedProduct && productIdInput) {
    productIdInput.value = selectedProduct.id;
  }
}

function initNotifyMe() {
  form = document.querySelector("[data-notify-me-form]");
  if (!form || initializedForms.has(form)) return;

  initializedForms.add(form);

  productIdInput = document.querySelector("[data-notify-product-id]");
  nameInput = document.querySelector("[data-notify-name]");
  emailInput = document.querySelector("[data-notify-email]");
  phoneInputWrapper = document.querySelector("[data-phone-input]");
  submitBtn = document.querySelector("[data-notify-submit-btn]");
  submitText = document.querySelector("[data-notify-submit-text]");
  submitSpinner = document.querySelector("[data-notify-submit-spinner]");
  dialog = document.getElementById("notify-me-dialog");

  if (phoneInputWrapper && window.PhoneInput) {
    window.PhoneInput.initElement(phoneInputWrapper);

    phoneInputWrapper.addEventListener("phone:change", function () {
      setPhoneError(false);
    });
  }

  form.addEventListener("submit", submitStockAlert);
  window.addEventListener("product:variant-changed", handleVariantChange);
}

// Listen for customer data
document.addEventListener("zid-customer-fetched", function (event) {
  const customer = event.detail?.customer;
  autoFillCustomerData(customer);
});

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  initNotifyMe();
  window.addEventListener("content:loaded", initNotifyMe);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

export { initNotifyMe };
