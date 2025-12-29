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

  if (typeof zid !== "undefined" && zid.customer && zid.customer.login) {
    zid.customer.login.open({
      redirectTo: addToUrl ? window.location.pathname + redirectTo : redirectTo
    });
  } else {
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

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  initAnnouncementBar();
  initLocaleForms();
  initLoginRedirectButtons();
  initCustomerGreeting();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
