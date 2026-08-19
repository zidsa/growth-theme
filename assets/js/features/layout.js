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

// Both theme and cart bundles include this module. Share state so layout
// listeners initialize once and either bundle can complete an auth redirect.
const layoutStateKey = Symbol.for("growth-theme.layout-state");
const layoutState = window[layoutStateKey] || {
  initialized: false,
  pendingAuthRedirect: null,
  authEndpointsComplete: false,
  authEndpointsPromise: null
};
window[layoutStateKey] = layoutState;

function normalizeAuthRedirect(redirectTo) {
  try {
    const redirectUrl = new URL(redirectTo, window.location.origin);
    if (redirectUrl.origin !== window.location.origin) return "";
    return redirectUrl.pathname + redirectUrl.search + redirectUrl.hash;
  } catch {
    return "";
  }
}

function getProfileRedirect() {
  return normalizeAuthRedirect(window.layoutConfig?.profileUrl || "/account-profile") || "/account-profile";
}

function markCustomerAuthenticated() {
  window.customerAuthState = window.customerAuthState || {};
  window.customerAuthState.isAuthenticated = true;
  window.customerAuthState.isGuest = false;
}

/**
 * Setup listener for auth success event
 * Handles redirect after successful OTP verification
 */
function setupAuthSuccessListener() {
  window.addEventListener("vitrin:auth:success", function () {
    markCustomerAuthenticated();
    initAuthVisibility();

    // Handle pending redirect
    if (layoutState.pendingAuthRedirect) {
      const redirectUrl = layoutState.pendingAuthRedirect;
      layoutState.pendingAuthRedirect = null;
      window.location.href = redirectUrl;
    }
  });
}

/**
 * Login action handler - opens login dialog with optional redirect
 */
export function handleLoginAction(redirectTo, addToUrl) {
  if (redirectTo === undefined) redirectTo = "";
  if (addToUrl === undefined) addToUrl = true;

  // Calculate and normalize the redirect before checking auth so an explicit
  // action target is preserved for shoppers who are already signed in.
  const finalRedirect = addToUrl ? window.location.pathname + redirectTo : redirectTo;
  const normalizedRedirect = finalRedirect ? normalizeAuthRedirect(finalRedirect) : "";
  const profileRedirect = getProfileRedirect();
  const authRedirect = normalizedRedirect || profileRedirect;

  if (window.customerAuthState && window.customerAuthState.isAuthenticated) {
    window.location.href = redirectTo && normalizedRedirect ? normalizedRedirect : profileRedirect;
    return;
  }

  // Store redirect for post-login navigation
  layoutState.pendingAuthRedirect = authRedirect;

  // Use auth_dialog if available (preferred per Zid docs)
  if (window.auth_dialog?.open && typeof window.auth_dialog.open === "function") {
    window.auth_dialog.open();
  } else if (typeof zid !== "undefined" && zid.customer && zid.customer.login) {
    // Fallback to Zid SDK login
    zid.customer.login.open({
      redirectTo: authRedirect
    });
  } else {
    // Final fallback to page redirect
    window.location.href = "/auth/login?redirect_to=" + encodeURIComponent(authRedirect);
  }
}

window.handleLoginAction = handleLoginAction;

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
    const customer = event.detail?.customer;
    if (customer?.id) {
      markCustomerAuthenticated();
    }

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

    // Mark auth endpoints as complete after customer fetch
    layoutState.authEndpointsComplete = true;
    initAuthVisibility();
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

// ─────────────────────────────────────────────────────────────
// Auth-Based Visibility (Cache-Safe)
// ─────────────────────────────────────────────────────────────

/**
 * Initialize auth-based element visibility
 * Elements with [data-auth-guest] are shown only to guests
 * Elements with [data-auth-user] are shown only to authenticated users
 * This allows templates to be cached while still showing correct content
 */
export function initAuthVisibility() {
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

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  if (layoutState.initialized) return;
  layoutState.initialized = true;

  initAnnouncementBar();
  initLocaleForms();
  initLoginRedirectButtons();
  initCustomerGreeting();
  setupAuthSuccessListener();
  
  // Don't call initAuthVisibility() here - wait for zid-customer-fetched event
  // which will call it after auth endpoints complete
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
