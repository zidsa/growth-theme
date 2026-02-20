/**
 * Layout Module
 *
 * Handles global layout functionality:
 * - Announcement bar height tracking
 * - Login/logout state management
 * - Customer greeting updates
 * - Locale/region navigation
 */

// ─────────────────────────────────────────────────────────────
// Announcement Bar
// ─────────────────────────────────────────────────────────────

function initAnnouncementBar() {
  const bar = document.querySelector("[data-announcement-bar]");
  if (bar) {
    const updateHeight = () => {
      document.body.style.setProperty("--announcement-bar-h", bar.offsetHeight + "px");
    };
    updateHeight();
    window.addEventListener("resize", updateHeight);
  }
}

// ─────────────────────────────────────────────────────────────
// Login/Account Management
// ─────────────────────────────────────────────────────────────

// Store pending redirect for post-login navigation
let pendingAuthRedirect = null;

/**
 * Setup listener for auth success event
 * Handles redirect after successful OTP verification
 */
function setupAuthSuccessListener() {
  window.addEventListener("vitrin:auth:success", function () {
    // Update auth state
    if (window.customerAuthState) {
      window.customerAuthState.isAuthenticated = true;
      window.customerAuthState.isGuest = false;
    }

    // Handle pending redirect
    if (pendingAuthRedirect) {
      const redirectUrl = pendingAuthRedirect;
      pendingAuthRedirect = null;
      window.location.href = redirectUrl;
    }
  });
}

/**
 * Login action handler - opens login dialog with optional redirect
 */
window.handleLoginAction = function (redirectTo, addToUrl) {
  if (redirectTo === undefined) redirectTo = "";
  if (addToUrl === undefined) addToUrl = true;

  if (window.customerAuthState && window.customerAuthState.isAuthenticated) {
    window.location.href = window.layoutConfig?.profileUrl || "/account-profile";
    return;
  }

  // Calculate final redirect URL and store for post-login navigation
  const finalRedirect = addToUrl ? window.location.pathname + redirectTo : redirectTo;
  if (finalRedirect) {
    pendingAuthRedirect = finalRedirect;
  }

  // Use auth_dialog if available (preferred per Zid docs)
  if (window.auth_dialog?.open && typeof window.auth_dialog.open === "function") {
    window.auth_dialog.open();
  } else if (typeof zid !== "undefined" && zid.customer && zid.customer.login) {
    // Fallback to Zid SDK login
    zid.customer.login.open({
      redirectTo: finalRedirect
    });
  } else {
    // Final fallback to page redirect
    window.location.href = window.layoutConfig?.profileUrl || "/account-profile";
  }
};

function initLoginRedirectButtons() {
  document.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-login-redirect]");
    if (btn) {
      e.preventDefault();
      const redirectUrl = btn.dataset.loginRedirect || "";
      window.handleLoginAction(redirectUrl, false);
    }
  });
}

function initCustomerGreeting() {
  document.addEventListener("zid-customer-fetched", function (event) {
    const customer = event.detail.customer;
    if (customer && customer.name) {
      const headerLoginBtn = document.getElementById("header-login-btn");
      const headerProfileBtn = document.getElementById("header-profile-btn");
      if (headerLoginBtn) headerLoginBtn.style.display = "none";
      if (headerProfileBtn) {
        headerProfileBtn.classList.remove("hidden");
        headerProfileBtn.classList.add("flex");
      }

      const mobileLoginBtn = document.getElementById("mobile-login-btn");
      const mobileLoggedInLinks = document.getElementById("mobile-logged-in-links");
      if (mobileLoginBtn) mobileLoginBtn.style.display = "none";
      if (mobileLoggedInLinks) {
        mobileLoggedInLinks.classList.remove("hidden");
        mobileLoggedInLinks.classList.add("flex");
      }
    }
  });
}

// ─────────────────────────────────────────────────────────────
// Locale/Region Navigation
// ─────────────────────────────────────────────────────────────

function navigateToLocale(countryCode, languageCode) {
  const config = window.layoutConfig || {};
  const defaultCountryCode = config.defaultCountryCode || "";
  const currentLanguage = config.currentLanguage || "ar";
  const currentCountry = config.currentCountry || "";

  const newLocale =
    languageCode.toLowerCase() +
    (countryCode.toLowerCase() === defaultCountryCode ? "" : "-" + countryCode.toLowerCase());

  const currentLocale = currentLanguage.toLowerCase() + "-" + currentCountry.toLowerCase();
  const pathParts = window.location.pathname.split("/");

  if (
    pathParts.length > 1 &&
    (pathParts[1].toLowerCase() === currentLanguage.toLowerCase() || pathParts[1].toLowerCase() === currentLocale)
  ) {
    pathParts[1] = newLocale;
  } else {
    pathParts.splice(1, 0, newLocale);
  }

  window.location.href = "/locales/" + newLocale + "?redirect_to=" + encodeURI(pathParts.join("/"));
}

function initLocaleForms() {
  document.querySelectorAll("[data-locale-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      const countrySelect = form.querySelector('[name="country"]');
      const languageSelect = form.querySelector('[name="language"]');

      const config = window.layoutConfig || {};
      const selectedCountry = countrySelect ? countrySelect.value : config.currentCountry;
      const selectedLanguage = languageSelect ? languageSelect.value : config.currentLanguage;

      navigateToLocale(selectedCountry, selectedLanguage);
    });
  });
}

window.selectMobileCountry = function (countryCode) {
  const config = window.layoutConfig || {};
  navigateToLocale(countryCode, config.currentLanguage);
};

window.selectMobileLanguage = function (languageCode) {
  const config = window.layoutConfig || {};
  navigateToLocale(config.currentCountry, languageCode);
};

window.onProductClick = function(event, el) {
  event.preventDefault();
  const product = JSON.parse(el.dataset.product);
  const listName = el.dataset.listName;
  const listId = el.dataset.listId;
  const index = Number(el.dataset.index);

  window.zidTracking?.sendGaSelectItemEvent({
    product: product,
    listName: listName,
    listId: listId,
    index: index
  });
  // Navigate to product page
  window.location.href = "/products/" + product.slug;
};
// ─────────────────────────────────────────────────────────────
// Auth-Based Visibility (Cache-Safe)
// ─────────────────────────────────────────────────────────────

/**
 * Initialize auth-based element visibility
 * Elements with [data-auth-guest] are shown only to guests
 * Elements with [data-auth-user] are shown only to authenticated users
 * This allows templates to be cached while still showing correct content
 */
function initAuthVisibility() {
  const isGuest = !window.customerAuthState || window.customerAuthState.isGuest;
  const isAuthenticated = window.customerAuthState && window.customerAuthState.isAuthenticated;

  // Show/hide guest-only elements
  document.querySelectorAll("[data-auth-guest]").forEach((el) => {
    el.classList.toggle("hidden", !isGuest);
  });

  // Show/hide authenticated-only elements
  document.querySelectorAll("[data-auth-user]").forEach((el) => {
    el.classList.toggle("hidden", !isAuthenticated);
  });

  // Update any auth-dependent hrefs
  document.querySelectorAll("[data-auth-href-guest]").forEach((el) => {
    if (isGuest) {
      el.href = el.dataset.authHrefGuest;
    }
  });

  document.querySelectorAll("[data-auth-href-user]").forEach((el) => {
    if (isAuthenticated) {
      el.href = el.dataset.authHrefUser;
    }
  });
}

// Re-run visibility check after auth changes
window.addEventListener("vitrin:auth:success", initAuthVisibility);

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  initAnnouncementBar();
  initLocaleForms();
  initLoginRedirectButtons();
  initCustomerGreeting();
  setupAuthSuccessListener();
  initAuthVisibility();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
