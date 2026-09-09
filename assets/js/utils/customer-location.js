const CUSTOMER_LOCATION_STORAGE_KEY = "zid_kit_select_branch";
const CUSTOMER_LOCATION_SELECTION_FAIL_OPEN_KEY = "zid_customer_location_selection_fail_open";

function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getConfirmedSelection(value) {
  if (!isRecord(value)) return undefined;

  if (
    typeof value.cityId !== "string" ||
    typeof value.expiresAt !== "number" ||
    !Number.isFinite(value.expiresAt) ||
    (value.latitude !== undefined && typeof value.latitude !== "number") ||
    (value.longitude !== undefined && typeof value.longitude !== "number")
  ) {
    return undefined;
  }

  return {
    cityId: value.cityId,
    expiresAt: value.expiresAt,
    latitude: value.latitude,
    longitude: value.longitude
  };
}

function getStoredCustomerLocation() {
  try {
    const storedValue = localStorage.getItem(CUSTOMER_LOCATION_STORAGE_KEY);
    if (!storedValue) return {};

    const parsedValue = JSON.parse(storedValue);
    if (!isRecord(parsedValue)) return {};

    return {
      confirmedSelection: getConfirmedSelection(parsedValue.confirmedSelection)
    };
  } catch {
    return {};
  }
}

export function hasStoredCustomerLocation(now = Date.now()) {
  const selection = getStoredCustomerLocation().confirmedSelection;

  return Boolean(selection?.cityId && selection.expiresAt > now);
}

function hasCustomerLocationSelectionFailedOpen() {
  try {
    return sessionStorage.getItem(CUSTOMER_LOCATION_SELECTION_FAIL_OPEN_KEY) === "true";
  } catch {
    return false;
  }
}

/**
 * Opens the shared location selector before quick view when the store requires
 * a customer location to add products to the cart.
 *
 * @returns {boolean} Whether quick view should be deferred.
 */
export function requestRequiredCustomerLocation() {
  const quickViewModal = document.getElementById("product-quick-view-modal");
  const settings = quickViewModal?.dataset;

  if (
    settings?.locationSelectionEnabled !== "true" ||
    settings.locationSelectionMode !== "required_on_add_to_cart" ||
    hasStoredCustomerLocation() ||
    hasCustomerLocationSelectionFailedOpen()
  ) {
    return false;
  }

  if (typeof window.region_settings_dialog?.open !== "function") return false;

  window.region_settings_dialog.open();
  return true;
}
