import { expect, test } from "@playwright/test";

import { hasStoredCustomerLocation, requestRequiredCustomerLocation } from "../assets/js/utils/customer-location.js";

const storage = new Map();

test.beforeEach(() => {
  storage.clear();
  globalThis.localStorage = {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, String(value))
  };
  globalThis.sessionStorage = {
    getItem: (key) => storage.get(`session:${key}`) ?? null,
    setItem: (key, value) => storage.set(`session:${key}`, String(value))
  };
});

function storeLocation(value) {
  localStorage.setItem("zid_kit_select_branch", JSON.stringify(value));
}

test("raw legacy branch data does not confirm a modern customer location", () => {
  storeLocation({ branchData: { type: "delivery" }, cityId: "42" });

  expect(hasStoredCustomerLocation()).toBe(false);
});

test("a current confirmed city satisfies modern customer location selection", () => {
  const now = Date.now();
  storeLocation({
    confirmedSelection: {
      cityId: "42",
      expiresAt: now + 60_000
    }
  });

  expect(hasStoredCustomerLocation(now)).toBe(true);
});

test("coordinates remain optional metadata on a confirmed city", () => {
  const now = Date.now();
  storeLocation({
    confirmedSelection: {
      cityId: "42",
      latitude: 24.7136,
      longitude: 46.6753,
      expiresAt: now + 60_000
    }
  });

  expect(hasStoredCustomerLocation(now)).toBe(true);
});

test("expired or malformed confirmed selections are rejected", () => {
  const now = Date.now();
  storeLocation({
    confirmedSelection: {
      cityId: 42,
      expiresAt: now + 60_000
    }
  });
  expect(hasStoredCustomerLocation(now)).toBe(false);

  storeLocation({
    confirmedSelection: {
      cityId: "42",
      expiresAt: now
    }
  });
  expect(hasStoredCustomerLocation(now)).toBe(false);
});

test("the quick-view gate fails open when the SDK dialog is unavailable", () => {
  globalThis.document = {
    getElementById: () => ({
      dataset: {
        locationSelectionEnabled: "true",
        locationSelectionMode: "required_on_add_to_cart"
      }
    })
  };
  globalThis.window = {};

  expect(requestRequiredCustomerLocation()).toBe(false);
});

test("the quick-view gate opens the mounted SDK dialog", () => {
  let openCount = 0;
  globalThis.document = {
    getElementById: () => ({
      dataset: {
        locationSelectionEnabled: "true",
        locationSelectionMode: "required_on_add_to_cart"
      }
    })
  };
  globalThis.window = {
    region_settings_dialog: {
      open: () => {
        openCount += 1;
      }
    }
  };

  expect(requestRequiredCustomerLocation()).toBe(true);
  expect(openCount).toBe(1);
});

test("the quick-view gate fails open after the SDK records a selection failure", () => {
  globalThis.document = {
    getElementById: () => ({
      dataset: {
        locationSelectionEnabled: "true",
        locationSelectionMode: "required_on_add_to_cart"
      }
    })
  };
  globalThis.window = {
    region_settings_dialog: {
      open: () => {
        throw new Error("the dialog must not reopen");
      }
    }
  };
  sessionStorage.setItem("zid_customer_location_selection_fail_open", "true");

  expect(requestRequiredCustomerLocation()).toBe(false);
});
