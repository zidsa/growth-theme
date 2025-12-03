/**
 * Quick View Modal Manager
 *
 * Fetches product page content and displays in a modal with caching and prefetching.
 * Uses in-memory LRU cache for optimal performance.
 *
 * Usage:
 * 1. Include this script in your layout
 * 2. Add the quick-view-modal component to your page
 * 3. Call window.quickViewManager.open(productSlug, productUrl) to open
 */

class QuickViewManager {
  // Configuration
  static CONFIG = {
    maxCacheSize: 15,
    hoverDelay: 200,
    productSectionId: "product-main-section"
  };

  // Element IDs
  static ELEMENTS = {
    dialog: "quick-view-dialog",
    modal: "product-quick-view-modal",
    skeleton: "quick-view-skeleton",
    content: "quick-view-content",
    footer: "quick-view-footer",
    productLink: "quick-view-product-link"
  };

  // Custom events
  static EVENTS = {
    contentLoaded: "quick-view-content-loaded",
    cartUpdated: "cart-updated"
  };

  constructor() {
    // LRU Cache using Map (maintains insertion order)
    this.cache = new Map();

    // Prefetch state
    this.prefetchController = null;
    this.hoverTimeout = null;
    this.currentHoveredCard = null;
    this.currentPrefetchUrl = null;

    // Bound methods for event listeners
    this.handleMouseOver = this.handleMouseOver.bind(this);
    this.handleMouseOut = this.handleMouseOut.bind(this);
    this.handleCartUpdated = this.handleCartUpdated.bind(this);

    // Initialize when DOM is ready
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => this.init());
    } else {
      this.init();
    }
  }

  /**
   * Initialize the manager
   */
  init() {
    this.setupPrefetchListeners();
    this.setupCartListener();
  }

  // ============================================
  // Cache Methods (LRU using Map)
  // ============================================

  /**
   * Get item from cache (moves to end for LRU)
   * @param {string} url - Cache key
   * @returns {string|null} Cached HTML or null
   */
  cacheGet(url) {
    const html = this.cache.get(url);
    if (!html) return null;

    // Move to end for LRU ordering
    this.cache.delete(url);
    this.cache.set(url, html);
    return html;
  }

  /**
   * Set item in cache with LRU eviction
   * @param {string} url - Cache key
   * @param {string} html - HTML content to cache
   */
  cacheSet(url, html) {
    // Remove if exists (to update position)
    this.cache.delete(url);

    // Evict oldest (first item) if at max capacity
    if (this.cache.size >= QuickViewManager.CONFIG.maxCacheSize) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }

    this.cache.set(url, html);
  }

  /**
   * Check if URL is cached
   * @param {string} url - Cache key
   * @returns {boolean}
   */
  cacheHas(url) {
    return this.cache.has(url);
  }

  /**
   * Clear the cache
   */
  cacheClear() {
    this.cache.clear();
  }

  // ============================================
  // URL Helpers
  // ============================================

  /**
   * Build fetch URL with theme parameter if present
   * @param {string} productUrl - Base product URL
   * @returns {string} URL with theme param appended
   */
  buildFetchUrl(productUrl) {
    const urlParams = new URLSearchParams(window.location.search);
    const themeParam = urlParams.get("theme");

    if (!themeParam) return productUrl;

    const separator = productUrl.includes("?") ? "&" : "?";
    return `${productUrl}${separator}theme=${encodeURIComponent(themeParam)}`;
  }

  /**
   * Extract product section HTML from full page
   * @param {string} html - Full page HTML
   * @returns {string|null} Product section HTML or null
   */
  extractProductSection(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const section = doc.getElementById(QuickViewManager.CONFIG.productSectionId);
    return section ? section.outerHTML : null;
  }

  // ============================================
  // Prefetch Methods
  // ============================================

  /**
   * Prefetch product page content
   * @param {string} productUrl - URL to prefetch
   */
  async prefetch(productUrl) {
    if (!productUrl || this.cacheHas(productUrl)) return;

    // Cancel any existing prefetch
    this.cancelPrefetch();

    this.prefetchController = new AbortController();

    try {
      const fetchUrl = this.buildFetchUrl(productUrl);
      const response = await fetch(fetchUrl, {
        signal: this.prefetchController.signal,
        priority: "low"
      });

      if (!response.ok) return;

      const html = await response.text();
      const sectionHtml = this.extractProductSection(html);

      if (sectionHtml) {
        this.cacheSet(productUrl, sectionHtml);
      }
    } catch (err) {
      // Ignore abort errors, warn on others
      if (err.name !== "AbortError") {
        console.warn("[QuickView] Prefetch failed:", err);
      }
    } finally {
      this.prefetchController = null;
    }
  }

  /**
   * Cancel current prefetch operation
   */
  cancelPrefetch() {
    if (this.hoverTimeout) {
      clearTimeout(this.hoverTimeout);
      this.hoverTimeout = null;
    }

    if (this.prefetchController) {
      this.prefetchController.abort();
      this.prefetchController = null;
    }

    this.currentPrefetchUrl = null;
  }

  /**
   * Setup hover-based prefetch listeners
   * Uses mouseover/mouseout which bubble (unlike mouseenter/mouseleave)
   */
  setupPrefetchListeners() {
    document.addEventListener("mouseover", this.handleMouseOver);
    document.addEventListener("mouseout", this.handleMouseOut);
  }

  /**
   * Handle mouse over on product card
   * @param {MouseEvent} event
   */
  handleMouseOver(event) {
    // Ensure target is an Element (not text node, etc.)
    if (!(event.target instanceof Element)) return;

    const card = event.target.closest("[data-product-card]");

    // Not over a product card
    if (!card) return;

    // Still on the same card - ignore (prevents re-triggering on child elements)
    if (card === this.currentHoveredCard) return;

    // New card - cancel any existing prefetch first
    this.cancelPrefetch();
    this.currentHoveredCard = card;

    const link = card.querySelector("a[href]");
    const productUrl = link?.getAttribute("href");

    // No URL or already cached - skip
    if (!productUrl || this.cacheHas(productUrl)) return;

    // Already prefetching this URL - skip
    if (productUrl === this.currentPrefetchUrl) return;

    this.currentPrefetchUrl = productUrl;

    this.hoverTimeout = setTimeout(() => {
      this.prefetch(productUrl);
    }, QuickViewManager.CONFIG.hoverDelay);
  }

  /**
   * Handle mouse out from product card
   * @param {MouseEvent} event
   */
  handleMouseOut(event) {
    // Ensure target is an Element
    if (!(event.target instanceof Element)) return;

    const card = event.target.closest("[data-product-card]");

    // Not leaving from a product card
    if (!card) return;

    // Check if we're moving to another element still within the same card
    const relatedTarget = event.relatedTarget;
    if (relatedTarget instanceof Element) {
      const toCard = relatedTarget.closest("[data-product-card]");
      // Still within the same card - ignore
      if (toCard === card) return;
    }

    // Actually leaving the card - cancel prefetch
    this.cancelPrefetch();
    this.currentHoveredCard = null;
  }

  // ============================================
  // Modal Methods
  // ============================================

  /**
   * Get modal DOM elements
   * @returns {Object|null} Element references or null if not found
   */
  getElements() {
    const elements = {};

    for (const [key, id] of Object.entries(QuickViewManager.ELEMENTS)) {
      elements[key] = document.getElementById(id);
      if (!elements[key]) {
        console.error(`[QuickView] Element not found: #${id}`);
        return null;
      }
    }

    return elements;
  }

  /**
   * Get localized messages from modal data attributes
   * @param {HTMLElement} modal - Modal element
   * @returns {Object} Localized messages
   */
  getMessages(modal) {
    return {
      errorMessage: modal?.dataset.errorMessage || "Failed to load product. Please try again.",
      goToProduct: modal?.dataset.goToProduct || "Go to product page"
    };
  }

  /**
   * Set modal state (loading, content, error)
   * @param {Object} elements - DOM elements
   * @param {string} state - State: "loading" | "content" | "error"
   */
  setModalState(elements, state) {
    const { skeleton, content, footer } = elements;

    skeleton.classList.toggle("hidden", state !== "loading");
    content.classList.toggle("hidden", state === "loading");
    footer.classList.toggle("hidden", state !== "content");
  }

  /**
   * Render error state in modal
   * @param {HTMLElement} content - Content container
   * @param {string} message - Error message
   * @param {string} linkText - Link text
   * @param {string} url - Product URL
   */
  renderError(content, message, linkText, url) {
    // Clear existing content
    content.innerHTML = "";

    // Build error UI safely (no XSS)
    const container = document.createElement("div");
    container.className = "py-8 text-center";

    const text = document.createElement("p");
    text.className = "text-secondary";
    text.textContent = message;

    const link = document.createElement("a");
    link.href = url;
    link.className = "text-primary mt-2 inline-block underline";
    link.textContent = linkText;

    container.append(text, link);
    content.appendChild(container);
  }

  /**
   * Dispatch content loaded event for gallery initialization
   */
  dispatchContentLoaded() {
    window.dispatchEvent(new CustomEvent(QuickViewManager.EVENTS.contentLoaded));
  }

  /**
   * Open quick view modal for a product
   * @param {string} productSlug - Product slug (used to build URL if productUrl not provided)
   * @param {string} [productUrl] - Direct product URL
   */
  async open(productSlug, productUrl) {
    const elements = this.getElements();
    if (!elements) return;

    const { dialog, modal, skeleton, content, footer, productLink } = elements;
    const baseUrl = productUrl || `/p/${productSlug}`;
    const messages = this.getMessages(modal);

    // Check cache first
    const cachedHtml = this.cacheGet(baseUrl);

    if (cachedHtml) {
      // Instant render from cache
      content.innerHTML = cachedHtml;
      productLink.href = baseUrl;
      this.setModalState(elements, "content");
      dialog.show();

      requestAnimationFrame(() => this.dispatchContentLoaded());
      return;
    }

    // Not cached - show skeleton and fetch
    content.innerHTML = "";
    this.setModalState(elements, "loading");
    dialog.show();

    try {
      const fetchUrl = this.buildFetchUrl(baseUrl);
      const response = await fetch(fetchUrl);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const html = await response.text();
      const sectionHtml = this.extractProductSection(html);

      if (!sectionHtml) {
        throw new Error("Product section not found");
      }

      // Cache for next time
      this.cacheSet(baseUrl, sectionHtml);

      // Render content
      content.innerHTML = sectionHtml;
      productLink.href = baseUrl;
      this.setModalState(elements, "content");

      requestAnimationFrame(() => this.dispatchContentLoaded());
    } catch (err) {
      console.error("[QuickView] Failed to load product:", err);
      this.setModalState(elements, "error");
      this.renderError(content, messages.errorMessage, messages.goToProduct, baseUrl);
    }
  }

  /**
   * Close the quick view modal
   */
  close() {
    const dialog = document.getElementById(QuickViewManager.ELEMENTS.dialog);
    if (dialog?.hasAttribute("open")) {
      dialog.hide();
    }
  }

  // ============================================
  // Event Handlers
  // ============================================

  /**
   * Setup cart update listener to close modal
   */
  setupCartListener() {
    window.addEventListener(QuickViewManager.EVENTS.cartUpdated, this.handleCartUpdated);
  }

  /**
   * Handle cart updated event
   */
  handleCartUpdated() {
    this.close();
  }

  // ============================================
  // Cleanup
  // ============================================

  /**
   * Destroy the manager and cleanup
   */
  destroy() {
    // Remove event listeners
    document.removeEventListener("mouseover", this.handleMouseOver);
    document.removeEventListener("mouseout", this.handleMouseOut);
    window.removeEventListener(QuickViewManager.EVENTS.cartUpdated, this.handleCartUpdated);

    // Cancel any pending operations
    this.cancelPrefetch();

    // Clear cache
    this.cacheClear();

    // Reset state
    this.currentHoveredCard = null;
  }
}

// ============================================
// Initialize Global Instance
// ============================================

window.quickViewManager = new QuickViewManager();

// Legacy support - expose open function directly
window.openQuickViewModal = function (productId, productSlug, productUrl) {
  window.quickViewManager.open(productSlug, productUrl);
};
