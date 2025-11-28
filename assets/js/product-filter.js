/**
 * Product Filter Manager
 *
 * Handles AJAX-based filtering without page reloads.
 * Uses native fetch() and History API
 *
 */

class ProductFilter {
  constructor(options = {}) {
    this.contentSelector = options.contentSelector || "#products-content";
    this.loadingClass = options.loadingClass || "opacity-50";
    this.isLoading = false;

    this.init();
  }

  /**
   * Initialize event listeners
   */
  init() {
    window.addEventListener("popstate", () => this.fetchProducts());
  }

  /**
   * Apply filters and fetch new products
   * @param {Object} params - Filter parameters { key: value, key2: null (to remove) }
   * @param {Object} options - Options { resetPage: true }
   */
  async applyFilter(params = {}, options = {}) {
    const { resetPage = true } = options;
    const url = new URL(window.location.href);

    Object.entries(params).forEach(([key, value]) => {
      if (value === null || value === undefined || value === "") {
        url.searchParams.delete(key);
      } else if (Array.isArray(value)) {
        url.searchParams.delete(key);
        value.forEach((v) => url.searchParams.append(key, v));
      } else {
        url.searchParams.set(key, String(value));
      }
    });

    if (resetPage) {
      url.searchParams.delete("page");
    }

    const cleanUrl = this.buildCleanUrl(url);
    history.pushState({}, "", cleanUrl);

    await this.fetchProducts();
  }

  /**
   * Build URL string with unencoded brackets for cleaner URLs
   * @param {URL} url - URL object
   * @returns {string} Clean URL string
   */
  buildCleanUrl(url) {
    const params = [];

    url.searchParams.forEach((value, key) => {
      params.push(`${key}=${encodeURIComponent(value)}`);
    });

    const queryString = params.length > 0 ? "?" + params.join("&") : "";
    return url.pathname + queryString;
  }

  /**
   * Fetch products and update the DOM
   */
  async fetchProducts() {
    if (this.isLoading) return;

    const content = document.querySelector(this.contentSelector);
    if (!content) {
      console.warn(`ProductFilter: Element "${this.contentSelector}" not found`);
      return;
    }

    this.isLoading = true;
    this.setLoadingState(content, true);

    try {
      const response = await fetch(window.location.href, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const html = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      const newContent = doc.querySelector(this.contentSelector);

      if (newContent) {
        content.innerHTML = newContent.innerHTML;
        this.reinitializeComponents(content);
      } else {
        console.warn("ProductFilter: Could not find new content in response");
      }
    } catch (error) {
      console.error("ProductFilter: Fetch error", error);
      window.location.reload();
    } finally {
      this.isLoading = false;
      this.setLoadingState(content, false);
    }
  }

  /**
   * Set loading state on content
   * @param {HTMLElement} element - Content element
   * @param {boolean} isLoading - Loading state
   */
  setLoadingState(element, isLoading) {
    if (isLoading) {
      element.classList.add(this.loadingClass);
      element.style.pointerEvents = "none";
      element.setAttribute("aria-busy", "true");
    } else {
      element.classList.remove(this.loadingClass);
      element.style.pointerEvents = "";
      element.setAttribute("aria-busy", "false");
    }
  }

  /**
   * Re-initialize components after content swap
   * @param {HTMLElement} container - Content container
   */
  reinitializeComponents(container) {
    window.dispatchEvent(new CustomEvent("products-updated", { detail: { container } }));
  }

  /**
   * Get current filter value from URL
   * @param {string} key - Parameter key
   * @returns {string|null} Parameter value
   */
  getFilter(key) {
    const url = new URL(window.location.href);
    return url.searchParams.get(key);
  }

  /**
   * Get all values for a filter (for multi-select filters)
   * @param {string} key - Parameter key
   * @returns {string[]} Array of values
   */
  getFilterAll(key) {
    const url = new URL(window.location.href);
    return url.searchParams.getAll(key);
  }

  /**
   * Clear all filters except specified keys
   * @param {string[]} keepKeys - Keys to preserve
   */
  async clearFilters(keepKeys = ["sort_by", "order", "page_size", "q"]) {
    const url = new URL(window.location.href);
    const keysToRemove = [];

    url.searchParams.forEach((_, key) => {
      if (!keepKeys.includes(key)) {
        keysToRemove.push(key);
      }
    });

    keysToRemove.forEach((key) => url.searchParams.delete(key));

    const cleanUrl = this.buildCleanUrl(url);
    history.pushState({}, "", cleanUrl);

    await this.fetchProducts();
  }

  /**
   * Remove a single filter value
   * @param {string} type - Filter type (sort, attribute, availability, price)
   * @param {string} slug - Attribute slug (for attribute type)
   * @param {string} value - Value to remove
   */
  removeFilter(type, slug, value) {
    const url = new URL(window.location.href);

    if (type === "sort") {
      url.searchParams.delete("sort_by");
      url.searchParams.delete("order");
    } else if (type === "attribute") {
      const key = `attributes[${slug}][]`;
      const values = url.searchParams.getAll(key);
      url.searchParams.delete(key);
      values.forEach((v) => {
        if (v !== value) url.searchParams.append(key, v);
      });
    } else if (type === "availability") {
      const values = url.searchParams.getAll("availability");
      url.searchParams.delete("availability");
      values.forEach((v) => {
        if (v !== value) url.searchParams.append("availability", v);
      });
    } else if (type === "price") {
      url.searchParams.delete("from_price");
      url.searchParams.delete("to_price");
    }

    url.searchParams.delete("page");
    const cleanUrl = this.buildCleanUrl(url);
    history.pushState({}, "", cleanUrl);

    this.fetchProducts();
  }

  /**
   * Handle sort select change
   * @param {string} value - Combined value (e.g., "price-asc")
   */
  handleSortChange(value) {
    const [sortBy, order] = value.split("-");
    this.applyFilter({ sort_by: sortBy, order });
  }

  /**
   * Handle availability checkbox change
   */
  handleAvailability() {
    const checked = document.querySelectorAll('input[name="availability"]:checked');
    const values = Array.from(checked).map((box) => box.value);

    const popover = document.getElementById("availability-popover");
    if (popover) popover.hidePopover();

    this.applyFilter({ availability: values.length > 0 ? values : null });
  }

  /**
   * Handle price filter form submit
   * @param {Event} event - Submit event
   * @param {string} minId - Min input element ID
   * @param {string} maxId - Max input element ID
   * @returns {boolean} False to prevent form submission
   */
  handlePriceSubmit(event, minId, maxId) {
    event.preventDefault();

    const minInput = document.getElementById(minId);
    const maxInput = document.getElementById(maxId);
    if (!minInput || !maxInput) return false;

    const fromPrice = minInput.value.replace(/,/g, "") || null;
    const toPrice = maxInput.value.replace(/,/g, "") || null;

    const popover = document.getElementById("price-popover");
    if (popover) popover.hidePopover();

    this.applyFilter({ from_price: fromPrice, to_price: toPrice });
    return false;
  }

  /**
   * Set sort params in drawer form
   * @param {HTMLElement} radio - Radio input element
   * @param {string} sortBy - Sort field
   * @param {string} order - Sort order
   */
  setSortParams(radio, sortBy, order) {
    const form = radio.closest("form");
    if (!form) return;

    let sortByInput = form.querySelector('input[name="sort_by"]');
    let orderInput = form.querySelector('input[name="order"]');

    if (!sortByInput) {
      sortByInput = document.createElement("input");
      sortByInput.type = "hidden";
      sortByInput.name = "sort_by";
      form.appendChild(sortByInput);
    }

    if (!orderInput) {
      orderInput = document.createElement("input");
      orderInput.type = "hidden";
      orderInput.name = "order";
      form.appendChild(orderInput);
    }

    sortByInput.value = sortBy;
    orderInput.value = order;
  }

  /**
   * Clear filters from drawer
   */
  clearDrawerFilters() {
    const dialog = document.getElementById("filters-drawer");
    if (dialog) dialog.close();

    this.clearFilters(["sort_by", "order", "page_size", "q"]);
  }

  /**
   * Submit filters form from drawer
   * @param {Event} event - Submit event
   * @returns {boolean} False to prevent form submission
   */
  submitDrawerForm(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    const dialog = document.getElementById("filters-drawer");
    if (dialog) dialog.close();

    const params = {};
    const arrayParams = {};

    for (let [key, value] of formData.entries()) {
      if (value === "" || value === null || key === "sort_option") continue;

      if (key === "from_price" || key === "to_price") {
        value = value.replace(/,/g, "");
      }

      if (key.endsWith("[]")) {
        if (!arrayParams[key]) arrayParams[key] = [];
        arrayParams[key].push(value);
      } else {
        params[key] = value;
      }
    }

    Object.assign(params, arrayParams);
    this.applyFilter(params);
    return false;
  }

  /**
   * Handle per-page select change
   * @param {string|number} perPage - Products per page
   */
  handlePerPageChange(perPage) {
    this.applyFilter({ page_size: perPage, page: null }, { resetPage: false });
  }
}

// Initialize global instance
window.productFilter = new ProductFilter();

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = ProductFilter;
}
