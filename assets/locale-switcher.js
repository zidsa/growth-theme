/**
 * Locale Switcher for Zid Themes
 * Handles language and country changes by redirecting to the proper URL
 */

(function () {
  "use strict";
  // Remove leading /ar, /en, /ar-sa, /en-us (case-insensitive), only if it's the FIRST segment
  function stripLeadingLocale(path) {
    // Matches: "/ar", "/ar/", "/ar-sa", "/ar-sa/", but not "/cart/ar"
    return path.replace(/^\/(?:[a-z]{2}-[a-z]{2}|[a-z]{2})(?=\/|$)/i, "");
  }
  // Get current locale from URL or default
  function getCurrentLocale() {
    const path = window.location.pathname;

    // Try to match lang-country format (e.g., /ar-sa/)
    const localeMatch = path.match(/^\/([a-z]{2}-[a-z]{2})\//);
    if (localeMatch) {
      const [lang, country] = localeMatch[1].split("-");
      return { lang, country, hasLocale: true, localeFormat: "full" };
    }

    // Try to match single language code (e.g., /ar or /en)
    const langOnlyMatch = path.match(/^\/([a-z]{2})(?:\/|$)/);
    if (langOnlyMatch) {
      return { lang: langOnlyMatch[1], country: "sa", hasLocale: true, localeFormat: "lang-only" };
    }

    return { lang: "ar", country: "sa", hasLocale: false, localeFormat: "none" };
  }

  // Build new URL with locale

  function buildLocaleUrl(lang, country) {
    const { pathname, search, hash } = window.location;

    // 1) Strip any existing locale at the start
    let rest = stripLeadingLocale(pathname);

    // 2) Normalize the remaining path
    if (rest === "" || rest === "/") rest = "/";
    else if (!rest.startsWith("/")) rest = "/" + rest;

    // 3) Build the new path (always prefix with the new full locale)
    const newPath = `/${lang.toLowerCase()}-${country.toLowerCase()}${rest}`;

    return newPath + search + hash;
  }

  // Change locale and redirect
  function changeLocale(lang, country) {
    const newUrl = buildLocaleUrl(lang, country);
    window.location.href = newUrl;
  }

  // Initialize locale switcher forms
  function initLocaleSwitcher() {
    // Handle form submissions
    document.querySelectorAll("[data-locale-form]").forEach((form) => {
      form.addEventListener("submit", (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const lang = formData.get("language") || getCurrentLocale().lang;
        const country = formData.get("country") || getCurrentLocale().country;

        changeLocale(lang, country);
      });
    });

    // Handle direct language/country changes
    document.querySelectorAll("[data-locale-change]").forEach((element) => {
      element.addEventListener("click", (e) => {
        e.preventDefault();

        const lang = element.dataset.lang || getCurrentLocale().lang;
        const country = element.dataset.country || getCurrentLocale().country;

        changeLocale(lang, country);
      });
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initLocaleSwitcher);
  } else {
    initLocaleSwitcher();
  }

  // Expose to window for manual usage
  window.changeLocale = changeLocale;
})();
