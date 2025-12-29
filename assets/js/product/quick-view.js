/**
 * Quick View Module
 *
 * Fetches product page content and displays in a modal with caching and prefetching.
 * Uses in-memory LRU cache for optimal performance.
 *
 * Usage:
 * - Include in main bundle via import
 * - Add quick-view-modal component to your page
 * - Call window.quickViewManager.open(productSlug, productUrl)
 */

// ─────────────────────────────────────────────────────────────
// Configuration
// ─────────────────────────────────────────────────────────────

const CONFIG = {
  maxCacheSize: 15,
  hoverDelay: 200,
  productSectionId: "product-main-section"
};

const ELEMENTS = {
  dialog: "quick-view-dialog",
  modal: "product-quick-view-modal",
  skeleton: "quick-view-skeleton",
  content: "quick-view-content",
  footer: "quick-view-footer",
  productLink: "quick-view-product-link"
};

// ─────────────────────────────────────────────────────────────
// Quick View Manager Class
// ─────────────────────────────────────────────────────────────

class QuickViewManager {
  constructor() {
    // LRU Cache using Map (maintains insertion order)
    this.cache = new Map();

    // Prefetch state
    this.prefetchController = null;
    this.hoverTimeout = null;
    this.currentHoveredCard = null;
    this.currentPrefetchUrl = null;

    // SDK script state
    this.sdkScriptLoaded = false;
    this.sdkScriptUrl = null;

    // Bound methods for event listeners
    this.handleMouseOver = this.handleMouseOver.bind(this);
    this.handleMouseOut = this.handleMouseOut.bind(this);
    this.handleCartUpdated = this.handleCartUpdated.bind(this);
  }

  // ─────────────────────────────────────────────────────────────
  // Cache Methods (LRU using Map)
  // ─────────────────────────────────────────────────────────────

  cacheGet(url) {
    const data = this.cache.get(url);
    if (!data) return null;

    // Move to end for LRU ordering
    this.cache.delete(url);
    this.cache.set(url, data);
    return data;
  }

  cacheSet(url, html, productObj) {
    this.cache.delete(url);

    if (this.cache.size >= CONFIG.maxCacheSize) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }

    this.cache.set(url, { html, productObj });
  }

  cacheHas(url) {
    return this.cache.has(url);
  }

  cacheClear() {
    this.cache.clear();
  }

  // ─────────────────────────────────────────────────────────────
  // URL Helpers
  // ─────────────────────────────────────────────────────────────

  buildFetchUrl(productUrl) {
    const urlParams = new URLSearchParams(window.location.search);
    const themeParam = urlParams.get("theme");

    if (!themeParam) return productUrl;

    const separator = productUrl.includes("?") ? "&" : "?";
    return `${productUrl}${separator}theme=${encodeURIComponent(themeParam)}`;
  }

  extractProductSection(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const section = doc.getElementById(CONFIG.productSectionId);
    return section ? section.outerHTML : null;
  }

  extractProductObj(html) {
    const match = html.match(/window\.productObj\s*=\s*(\{[\s\S]*?\});?\s*<\/script>/);
    if (match && match[1]) {
      try {
        return JSON.parse(match[1]);
      } catch (e) {
        console.warn("[QuickView] Failed to parse productObj:", e);
      }
    }
    return null;
  }

  extractSdkScriptUrl(html) {
    const match = html.match(/<script[^>]+src="([^"]*theme-statics\/product\.js[^"]*)"/);
    return match ? match[1] : null;
  }

  loadSdkScript() {
    if (this.sdkScriptLoaded || !this.sdkScriptUrl) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = this.sdkScriptUrl;
      script.onload = () => {
        this.sdkScriptLoaded = true;
        resolve();
      };
      script.onerror = () => reject(new Error("[QuickView] Failed to load SDK script"));
      document.head.appendChild(script);
    });
  }

  // ─────────────────────────────────────────────────────────────
  // Prefetch Methods
  // ─────────────────────────────────────────────────────────────

  async prefetch(productUrl) {
    if (!productUrl || this.cacheHas(productUrl)) return;

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
      const productObj = this.extractProductObj(html);

      if (!this.sdkScriptUrl) {
        this.sdkScriptUrl = this.extractSdkScriptUrl(html);
      }

      if (sectionHtml) {
        this.cacheSet(productUrl, sectionHtml, productObj);
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        console.warn("[QuickView] Prefetch failed:", err);
      }
    } finally {
      this.prefetchController = null;
    }
  }

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

  setupPrefetchListeners() {
    document.addEventListener("mouseover", this.handleMouseOver);
    document.addEventListener("mouseout", this.handleMouseOut);
  }

  handleMouseOver(event) {
    if (!(event.target instanceof Element)) return;

    const card = event.target.closest("[data-product-card]");
    if (!card) return;
    if (card === this.currentHoveredCard) return;

    this.cancelPrefetch();
    this.currentHoveredCard = card;

    const link = card.querySelector("a[href]");
    const productUrl = link?.getAttribute("href");

    if (!productUrl || this.cacheHas(productUrl)) return;
    if (productUrl === this.currentPrefetchUrl) return;

    this.currentPrefetchUrl = productUrl;

    this.hoverTimeout = setTimeout(() => {
      this.prefetch(productUrl);
    }, CONFIG.hoverDelay);
  }

  handleMouseOut(event) {
    if (!(event.target instanceof Element)) return;

    const card = event.target.closest("[data-product-card]");
    if (!card) return;

    const relatedTarget = event.relatedTarget;
    if (relatedTarget instanceof Element) {
      const toCard = relatedTarget.closest("[data-product-card]");
      if (toCard === card) return;
    }

    this.cancelPrefetch();
    this.currentHoveredCard = null;
  }

  // ─────────────────────────────────────────────────────────────
  // Modal Methods
  // ─────────────────────────────────────────────────────────────

  getElements() {
    const elements = {};

    for (const [key, id] of Object.entries(ELEMENTS)) {
      elements[key] = document.getElementById(id);
      if (!elements[key]) {
        console.error(`[QuickView] Element not found: #${id}`);
        return null;
      }
    }

    return elements;
  }

  getMessages(modal) {
    return {
      errorMessage: modal?.dataset.errorMessage || "Failed to load product. Please try again.",
      goToProduct: modal?.dataset.goToProduct || "Go to product page"
    };
  }

  setModalState(elements, state) {
    const { skeleton, content, footer } = elements;

    skeleton.classList.toggle("hidden", state !== "loading");
    content.classList.toggle("hidden", state === "loading");
    footer.classList.toggle("hidden", state !== "content");
  }

  renderError(content, message, linkText, url) {
    content.innerHTML = "";

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

  dispatchContentLoaded() {
    window.dispatchEvent(new CustomEvent("content:loaded"));
  }

  async open(productSlug, productUrl) {
    const elements = this.getElements();
    if (!elements) return;

    const { dialog, modal, content, productLink } = elements;
    const baseUrl = productUrl || `/p/${productSlug}`;
    const messages = this.getMessages(modal);

    const cachedData = this.cacheGet(baseUrl);

    if (cachedData) {
      if (cachedData.productObj) window.productObj = cachedData.productObj;
      await this.loadSdkScript();

      content.innerHTML = cachedData.html;
      productLink.href = baseUrl;
      this.setModalState(elements, "content");
      dialog.show();

      requestAnimationFrame(() => this.dispatchContentLoaded());
      return;
    }

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
      const productObj = this.extractProductObj(html);

      if (!sectionHtml) {
        throw new Error("Product section not found");
      }

      if (!this.sdkScriptUrl) {
        this.sdkScriptUrl = this.extractSdkScriptUrl(html);
      }

      if (productObj) window.productObj = productObj;

      await this.loadSdkScript();

      this.cacheSet(baseUrl, sectionHtml, productObj);

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

  close() {
    const dialog = document.getElementById(ELEMENTS.dialog);
    if (dialog?.hasAttribute("open")) {
      dialog.hide();
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Event Handlers
  // ─────────────────────────────────────────────────────────────

  setupCartListener() {
    window.addEventListener("cart-updated", this.handleCartUpdated);
  }

  handleCartUpdated() {
    this.close();
  }

  // ─────────────────────────────────────────────────────────────
  // Lifecycle
  // ─────────────────────────────────────────────────────────────

  init() {
    this.setupPrefetchListeners();
    this.setupCartListener();
  }

  destroy() {
    document.removeEventListener("mouseover", this.handleMouseOver);
    document.removeEventListener("mouseout", this.handleMouseOut);
    window.removeEventListener("cart-updated", this.handleCartUpdated);

    this.cancelPrefetch();
    this.cacheClear();
    this.currentHoveredCard = null;
  }
}

// ─────────────────────────────────────────────────────────────
// Global Instance & Legacy Support
// ─────────────────────────────────────────────────────────────

const quickViewManager = new QuickViewManager();

// Expose globally
window.quickViewManager = quickViewManager;

// Legacy support
window.openQuickViewModal = function (productId, productSlug, productUrl) {
  quickViewManager.open(productSlug, productUrl);
};

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  quickViewManager.init();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

export { quickViewManager };
export default QuickViewManager;
