/**
 * Loading State Utilities
 */

const SPINNER_SVG = `<svg class="animate-spin size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`;

// Store original content for restoration
const originalContent = new WeakMap();

/**
 * Show spinner inside element (replaces content)
 * @param {HTMLElement} element - Button or element to show spinner in
 * @param {Object} options - { text: optional loading text }
 */
export function showSpinner(element, options = {}) {
  if (!element) return;

  // Store original content if not already stored
  if (!originalContent.has(element)) {
    originalContent.set(element, element.innerHTML);
  }

  element.disabled = true;
  element.innerHTML = options.text ? `${SPINNER_SVG} <span>${options.text}</span>` : SPINNER_SVG;
}

/**
 * Hide spinner and restore original content
 * @param {HTMLElement} element - Element to restore
 */
export function hideSpinner(element) {
  if (!element) return;

  element.disabled = false;
  const original = originalContent.get(element);
  if (original) {
    element.innerHTML = original;
    originalContent.delete(element);
  }
}

/**
 * Add loading opacity to element
 * @param {HTMLElement} element - Element to dim
 */
export function showLoading(element) {
  if (!element) return;
  element.classList.add("opacity-50", "pointer-events-none");
}

/**
 * Remove loading opacity from element
 * @param {HTMLElement} element - Element to restore
 */
export function hideLoading(element) {
  if (!element) return;
  element.classList.remove("opacity-50", "pointer-events-none");
}
