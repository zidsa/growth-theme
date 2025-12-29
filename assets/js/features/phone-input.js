/**
 * Phone Input Component
 *
 * Handles phone number input with searchable country selector.
 * Uses simple el-popover with custom filtering.
 */

// Import countries data (also sets window.CountriesData)
import "../data/countries.js";

// Track initialized components
const initializedInputs = new WeakSet();

// Get current language
const currentLang = document.documentElement.lang || "en";

/**
 * Format phone number with spaces based on digit count
 * Common patterns: 8→4-4, 9→3-3-3, 10→3-3-4, 11→3-4-4
 */
function formatPhone(digits) {
  if (!digits) return "";
  const len = digits.length;

  if (len <= 3) return digits;
  if (len <= 6) return digits.slice(0, 3) + " " + digits.slice(3);
  if (len <= 9) return digits.slice(0, 3) + " " + digits.slice(3, 6) + " " + digits.slice(6);
  if (len <= 12)
    return digits.slice(0, 3) + " " + digits.slice(3, 6) + " " + digits.slice(6, 10) + " " + digits.slice(10);
  return digits.slice(0, 3) + " " + digits.slice(3, 6) + " " + digits.slice(6, 10) + " " + digits.slice(10, 14);
}

/**
 * Create country option HTML
 */
function createCountryOptionHTML(country, isSelected) {
  const displayName = currentLang === "ar" && country.nameAr ? country.nameAr : country.name;
  return `
    <button
      type="button"
      class="phone-country-option"
      tabindex="-1"
      data-country-code="${country.code}"
      data-dial-code="${country.dialCode}"
      data-country-name="${country.name}"
      data-country-name-ar="${country.nameAr || ""}"
      ${isSelected ? 'aria-selected="true"' : ""}
    >
      <span data-slot="flag">
        <img
          src="https://flagcdn.com/w40/${country.code.toLowerCase()}.png"
          srcset="https://flagcdn.com/w80/${country.code.toLowerCase()}.png 2x"
          alt="${country.name}"
          loading="lazy"
        />
      </span>
      <span data-slot="name">${displayName}</span>
      <span data-slot="code">${country.dialCode}</span>
      <span data-slot="check">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>
    </button>
  `;
}

/**
 * Initialize a single phone input component
 */
function initPhoneInput(wrapper) {
  if (initializedInputs.has(wrapper)) return;
  initializedInputs.add(wrapper);

  // Query elements
  const fullValueInput = wrapper.querySelector("[data-phone-full-value]");
  const countryCodeInput = wrapper.querySelector("[data-phone-country-code]");
  const countryDisplay = wrapper.querySelector("[data-phone-country-display]");
  const phoneNumberInput = wrapper.querySelector("[data-phone-number-input]");
  const countryTrigger = wrapper.querySelector("[data-slot='country-trigger']");
  const popoverId = countryTrigger?.getAttribute("popovertarget");
  const popover = popoverId ? document.getElementById(popoverId) : null;
  const searchInput = popover?.querySelector("[data-phone-country-search]");
  const countryList = popover?.querySelector("[data-phone-country-list]");
  const noResults = popover?.querySelector("[data-phone-no-results]");

  // Check if we should load all countries
  const useAllCountries = wrapper.dataset.allCountries === "true";

  // Populate all countries if requested
  if (useAllCountries && window.CountriesData && countryList) {
    const currentDialCode = countryCodeInput?.value || "+966";
    countryList.innerHTML = window.CountriesData.map((country) =>
      createCountryOptionHTML(country, country.dialCode === currentDialCode)
    ).join("");
  }

  // Get country options (after potential population)
  let countryOptions = popover?.querySelectorAll(".phone-country-option") || [];

  if (!phoneNumberInput || !countryCodeInput) {
    console.warn("[PhoneInput] Missing required elements");
    return;
  }

  // Remove country options from tab order (navigate via arrows only)
  countryOptions.forEach((opt) => opt.setAttribute("tabindex", "-1"));

  // Current state
  let currentDialCode = countryCodeInput.value || "+966";
  let highlightedIndex = -1;

  /**
   * Update the full phone value
   */
  function updateFullValue() {
    const phoneNumber = phoneNumberInput.value.replace(/\D/g, "");
    if (fullValueInput) {
      fullValueInput.value = phoneNumber ? currentDialCode + phoneNumber : "";
    }

    wrapper.dispatchEvent(
      new CustomEvent("phone:change", {
        detail: {
          dialCode: currentDialCode,
          phoneNumber: phoneNumber,
          fullValue: fullValueInput?.value || ""
        },
        bubbles: true
      })
    );
  }

  /**
   * Get visible (non-hidden) options
   */
  function getVisibleOptions() {
    return Array.from(countryOptions).filter((opt) => !opt.hidden);
  }

  /**
   * Set highlighted option by index
   */
  function setHighlighted(index) {
    const visibleOptions = getVisibleOptions();

    // Remove highlight from all
    countryOptions.forEach((opt) => opt.removeAttribute("data-highlighted"));

    // Set new highlight
    if (index >= 0 && index < visibleOptions.length) {
      highlightedIndex = index;
      const option = visibleOptions[index];
      option.setAttribute("data-highlighted", "true");

      // Scroll into view
      option.scrollIntoView({ block: "nearest", behavior: "smooth" });
    } else {
      highlightedIndex = -1;
    }
  }

  /**
   * Get the index of the currently selected option in visible options
   */
  function getSelectedIndex() {
    const visibleOptions = getVisibleOptions();
    return visibleOptions.findIndex((opt) => opt.dataset.dialCode === currentDialCode);
  }

  /**
   * Filter countries based on search query
   */
  function filterCountries(query, highlightSelected = false) {
    const normalizedQuery = query.toLowerCase().trim();
    let visibleCount = 0;

    countryOptions.forEach((option) => {
      const name = (option.dataset.countryName || "").toLowerCase();
      const nameAr = (option.dataset.countryNameAr || "").toLowerCase();
      const dialCode = (option.dataset.dialCode || "").toLowerCase();
      const code = (option.dataset.countryCode || "").toLowerCase();

      const matches =
        !normalizedQuery ||
        name.includes(normalizedQuery) ||
        nameAr.includes(normalizedQuery) ||
        dialCode.includes(normalizedQuery) ||
        code.includes(normalizedQuery);

      option.hidden = !matches;
      if (matches) visibleCount++;
    });

    // Show/hide no results message
    if (noResults) {
      noResults.hidden = visibleCount > 0;
    }

    // Highlight: selected item when opening, first match when searching
    if (highlightSelected) {
      const selectedIndex = getSelectedIndex();
      setHighlighted(selectedIndex >= 0 ? selectedIndex : 0);
    } else if (normalizedQuery) {
      // When searching, highlight first match
      setHighlighted(visibleCount > 0 ? 0 : -1);
    } else {
      // No search query and not initial open - clear highlight
      setHighlighted(-1);
    }
  }

  /**
   * Select a country
   */
  function selectCountry(option) {
    const dialCode = option.dataset.dialCode;
    const countryCode = option.dataset.countryCode;

    // Update state
    currentDialCode = dialCode;

    // Update hidden inputs
    if (countryCodeInput) countryCodeInput.value = dialCode;

    // Update display
    if (countryDisplay) countryDisplay.textContent = dialCode;

    // Update aria-selected on all options
    countryOptions.forEach((opt) => {
      opt.setAttribute("aria-selected", opt.dataset.dialCode === dialCode ? "true" : "false");
    });

    // Update full value
    updateFullValue();

    // Close popover
    if (popover && popover.hidePopover) {
      popover.hidePopover();
    }

    // Dispatch country change event
    wrapper.dispatchEvent(
      new CustomEvent("phone:country-change", {
        detail: {
          dialCode: dialCode,
          countryCode: countryCode,
          countryName: option.dataset.countryName
        },
        bubbles: true
      })
    );

    // Focus phone input
    phoneNumberInput?.focus();
  }

  /**
   * Handle phone number input - format as you type
   */
  function handlePhoneInput(e) {
    const input = e.target;
    const cursorPos = input.selectionStart;
    const oldValue = input.value;

    // Extract digits only
    const digits = oldValue.replace(/\D/g, "");

    // Format with spaces
    const formatted = formatPhone(digits);

    // Only update if changed
    if (oldValue !== formatted) {
      input.value = formatted;

      // Restore cursor position (adjust for added/removed spaces)
      const oldDigitsBeforeCursor = oldValue.slice(0, cursorPos).replace(/\D/g, "").length;
      let newCursorPos = 0;
      let digitCount = 0;

      for (let i = 0; i < formatted.length && digitCount < oldDigitsBeforeCursor; i++) {
        newCursorPos = i + 1;
        if (/\d/.test(formatted[i])) digitCount++;
      }

      input.setSelectionRange(newCursorPos, newCursorPos);
    }

    updateFullValue();
  }

  /**
   * Handle search input
   */
  function handleSearchInput(e) {
    filterCountries(e.target.value);
  }

  /**
   * Handle country option click
   */
  function handleCountryClick(e) {
    const option = e.target.closest(".phone-country-option");
    if (option) {
      selectCountry(option);
    }
  }

  /**
   * Handle popover toggle - focus search and reset filter
   */
  function handlePopoverToggle(e) {
    if (e.newState === "open") {
      // Reset search and show all, highlight currently selected
      if (searchInput) {
        searchInput.value = "";
        filterCountries("", true); // true = highlight selected item

        // Focus search input - use requestAnimationFrame for reliable timing
        requestAnimationFrame(() => {
          searchInput.focus();
        });
      }
    } else {
      // Clear highlights when closing
      countryOptions.forEach((opt) => opt.removeAttribute("data-highlighted"));
      highlightedIndex = -1;
    }
  }

  /**
   * Handle keyboard navigation - keeps focus on search input
   */
  function handleKeydown(e) {
    const visibleOptions = getVisibleOptions();

    if (e.key === "Enter") {
      // Select highlighted option
      if (highlightedIndex >= 0 && highlightedIndex < visibleOptions.length) {
        e.preventDefault();
        selectCountry(visibleOptions[highlightedIndex]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (visibleOptions.length === 0) return;

      const nextIndex = highlightedIndex < visibleOptions.length - 1 ? highlightedIndex + 1 : 0;
      setHighlighted(nextIndex);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (visibleOptions.length === 0) return;

      const nextIndex = highlightedIndex > 0 ? highlightedIndex - 1 : visibleOptions.length - 1;
      setHighlighted(nextIndex);
    } else if (e.key === "Escape") {
      popover?.hidePopover();
      countryTrigger?.focus();
    }
  }

  // Event listeners
  phoneNumberInput.addEventListener("input", handlePhoneInput);

  if (searchInput) {
    searchInput.addEventListener("input", handleSearchInput);
    searchInput.addEventListener("keydown", handleKeydown);
  }

  if (countryList) {
    countryList.addEventListener("click", handleCountryClick);
  }

  if (popover) {
    popover.addEventListener("toggle", handlePopoverToggle);
  }

  // Initial value update
  updateFullValue();

  // Store reference for external access
  wrapper._phoneInput = {
    getValue: () => fullValueInput?.value || "",
    getDialCode: () => currentDialCode,
    getPhoneNumber: () => phoneNumberInput.value.replace(/\D/g, ""),
    setDialCode: (dialCode) => {
      const option = Array.from(countryOptions).find((opt) => opt.dataset.dialCode === dialCode);
      if (option) selectCountry(option);
    },
    setPhoneNumber: (number) => {
      const digits = (number || "").replace(/\D/g, "");
      phoneNumberInput.value = formatPhone(digits);
      updateFullValue();
    },
    reset: () => {
      phoneNumberInput.value = "";
      updateFullValue();
    },
    /**
     * Validate phone number length
     * @returns {undefined|'TOO_SHORT'|'TOO_LONG'|'INVALID_LENGTH'|'INVALID_COUNTRY'|'EMPTY'} - undefined if valid
     */
    validate: () => {
      const phoneNumber = phoneNumberInput.value.replace(/\D/g, "");
      if (!phoneNumber) return "EMPTY";
      if (window.CountriesData && window.CountriesData.validatePhoneLength) {
        return window.CountriesData.validatePhoneLength(phoneNumber, currentDialCode);
      }
      // Fallback: basic length check (7-15 digits per ITU-T E.164)
      if (phoneNumber.length < 7) return "TOO_SHORT";
      if (phoneNumber.length > 15) return "TOO_LONG";
      return undefined;
    },
    /**
     * Check if phone number is valid
     * @returns {boolean}
     */
    isValid: () => {
      const phoneNumber = phoneNumberInput.value.replace(/\D/g, "");
      if (!phoneNumber) return false;
      if (window.CountriesData && window.CountriesData.isPossiblePhoneNumber) {
        return window.CountriesData.isPossiblePhoneNumber(phoneNumber, currentDialCode);
      }
      // Fallback: basic length check
      return phoneNumber.length >= 7 && phoneNumber.length <= 15;
    }
  };
}

/**
 * Initialize all phone inputs on the page
 */
function initAll() {
  document.querySelectorAll("[data-phone-input]").forEach(initPhoneInput);
}

/**
 * Public API
 */
const PhoneInput = {
  init: initAll,
  initElement: initPhoneInput,
  get: (idOrElement) => {
    const wrapper =
      typeof idOrElement === "string" ? document.querySelector(`[data-phone-input-id="${idOrElement}"]`) : idOrElement;
    return wrapper?._phoneInput || null;
  }
};

// Expose globally for backward compatibility
window.PhoneInput = PhoneInput;

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  initAll();
  window.addEventListener("phone-input:init", initAll);
  window.addEventListener("content:loaded", initAll);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

export { PhoneInput, initPhoneInput };
export default PhoneInput;
