/**
 * Theme Entry Point
 *
 * Initializes all theme features based on page context.
 * Uses event-based architecture for dynamic content.
 *
 * Events:
 * - content:loaded - Dispatch when new content is added (e.g., AJAX, quick view)
 *                    All modules will re-init their elements
 */

// TEMP DEBUG: identifies which theme.js build the store is actually serving
console.log("[GALLERY-DEBUG] theme.js build: v1.0.1 mobile-thumbnails (2026-08-19)");

// TEMP DEBUG: after full load, report the gallery's real state and whether the
// slide-width CSS class exists in the loaded stylesheet
window.addEventListener("load", () => {
  setTimeout(() => {
    const slide = document.querySelector(".product-gallery__slide");
    const img = slide?.querySelector("img");

    // Probe: does the currently loaded CSS define our flex-basis class?
    const probe = document.createElement("div");
    probe.className = "flex-[0_0_calc(100%-8px)]";
    document.body.appendChild(probe);
    const probeBasis = getComputedStyle(probe).flexBasis;
    probe.className = "flex-[0_0_75%]";
    const probeOldBasis = getComputedStyle(probe).flexBasis;
    probe.remove();

    console.log("[GALLERY-DEBUG] state after page load:", {
      slideClass: slide?.className,
      slideWidth: slide?.getBoundingClientRect().width,
      imgSrc: img?.getAttribute("src")?.slice(0, 100),
      imgVisibleHeight: img?.getBoundingClientRect().height,
      cssHasNewClass: probeBasis !== "auto" ? probeBasis : "MISSING",
      cssHasOldClass: probeOldBasis !== "auto" ? probeOldBasis : "MISSING",
      themeJsUrl: document.querySelector('script[src*="theme.js"]')?.src
    });
  }, 1000);
});

import { createCarousel, createConditionalCarousel } from "./lib/carousel.js";
import { initAllProductGalleries } from "./product/gallery.js";
import { initCart, initButtons as initCartButtons } from "./cart/add-to-cart.js";

// Product modules (self-initializing, register global callbacks)
import "./product/variants.js";
import "./product/quick-view.js";
import "./product/lightbox.js";
import "./product/sticky-bar.js";

// Feature modules (self-initializing)
import "./features/layout.js";
import "./features/wishlist.js";
import "./features/search.js";
import "./features/qty-input.js";
import "./features/phone-input.js";
import "./features/product-filter.js";
import "./features/price-slider.js";
import "./features/bundle-offers.js";
import "./features/notify-me.js";
// Note: loyalty-rewards is loaded as standalone script AFTER vitrin_body in layout.jinja

// Store for initialized carousel instances (for cleanup)
const carouselInstances = new WeakMap();

/**
 * Initialize all carousels with data-carousel attribute
 */
function initCarousels() {
  document.querySelectorAll("[data-carousel]").forEach((container) => {
    // Skip if already initialized
    if (carouselInstances.has(container)) return;

    const options = {
      loop: container.dataset.carouselLoop === "true",
      fade: container.dataset.carouselFade === "true",
      autoplay: container.dataset.carouselAutoplay ? parseInt(container.dataset.carouselAutoplay) : false,
      autoScroll: container.dataset.carouselAutoscroll ? parseFloat(container.dataset.carouselAutoscroll) : false,
      align: container.dataset.carouselAlign || "start",
      dragFree: container.dataset.carouselDragfree === "true"
    };

    // Conditional carousel (only init when content overflows)
    if (container.dataset.carouselConditional === "true") {
      const controlsEl = container.parentElement?.querySelector("[data-carousel-controls]");
      const instance = createConditionalCarousel(container, options, controlsEl);
      if (instance) {
        carouselInstances.set(container, instance);
      }
    } else {
      // Regular carousel
      const instance = createCarousel(container, options);
      if (instance) {
        carouselInstances.set(container, instance);
      }
    }
  });
}

/**
 * Initialize theme
 */
function init() {
  const page = document.body.dataset.template;
  console.log("[Theme] Initializing for page:", page);

  // Initialize carousels
  initCarousels();

  // Initialize product galleries (product page, quick view)
  initAllProductGalleries();

  // Initialize cart (add-to-cart buttons, badge)
  initCart();
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
  if (window.checkout_dialog) {
    document.getElementsByClassName('btn-buy-now')[0].classList.remove('hidden');
  }
} else {
  init();
}

// Re-init when new content is loaded (AJAX, quick view, etc.)
window.addEventListener("content:loaded", () => {
  initCarousels();
  initAllProductGalleries();
  initCartButtons();
});

// Re-init cart buttons when products are filtered/updated
window.addEventListener("products:updated", () => {
  initCartButtons();
});
