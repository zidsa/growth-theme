/**
 * Image Lightbox Module
 *
 * Initializes PhotoSwipe lightbox for product gallery images.
 * Supports keyboard navigation, touch gestures, pinch-zoom.
 */

// ─────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────

let lightbox = null;
let imageData = [];

// ─────────────────────────────────────────────────────────────
// Image Data Collection
// ─────────────────────────────────────────────────────────────

function collectImageData() {
  const gallery = document.getElementById("product-gallery-lightbox");
  if (!gallery) return [];

  const links = gallery.querySelectorAll("a");
  return Array.from(links).map((link) => {
    const img = link.querySelector("img");
    return {
      src: link.href,
      width: parseInt(link.dataset.pswpWidth) || 1600,
      height: parseInt(link.dataset.pswpHeight) || 2133,
      thumbSrc: img ? img.src : link.href,
      alt: img ? img.alt : ""
    };
  });
}

// ─────────────────────────────────────────────────────────────
// PhotoSwipe Initialization
// ─────────────────────────────────────────────────────────────

async function initLightbox() {
  const galleryEl = document.getElementById("product-gallery-lightbox");
  if (!galleryEl) return;

  imageData = collectImageData();
  if (imageData.length === 0) return;

  // Dynamically import PhotoSwipe
  const { default: PhotoSwipeLightbox } = await import(
    "https://cdn.jsdelivr.net/npm/photoswipe@5.4.4/dist/photoswipe-lightbox.esm.min.js"
  );

  // Destroy existing instance if any
  if (lightbox) {
    lightbox.destroy();
    lightbox = null;
  }

  lightbox = new PhotoSwipeLightbox({
    dataSource: imageData,
    pswpModule: () => import("https://cdn.jsdelivr.net/npm/photoswipe@5.4.4/dist/photoswipe.esm.min.js"),

    // UI options
    bgOpacity: 1,
    showHideAnimationType: "fade",
    zoom: true,
    close: true,
    counter: false,
    arrowPrev: true,
    arrowNext: true,

    // Padding around image
    paddingFn: () => ({ top: 80, bottom: 140, left: 16, right: 16 }),

    // Custom SVGs
    arrowPrevSVG:
      '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    arrowNextSVG:
      '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    closeSVG:
      '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  });

  // Add custom thumbnails
  lightbox.on("uiRegister", function () {
    lightbox.pswp.ui.registerElement({
      name: "custom-thumbs",
      appendTo: "wrapper",
      onInit: (el, pswp) => {
        el.className = "pswp-custom-thumbs";

        el.innerHTML = imageData
          .map((item, i) => {
            return `
              <button class="pswp-custom-thumb${i === 0 ? " pswp-custom-thumb--active" : ""}" data-index="${i}" type="button">
                <img src="${item.thumbSrc}" alt="${item.alt}" />
              </button>
            `;
          })
          .join("");

        // Thumbnail click handler
        el.addEventListener("click", (e) => {
          const thumb = e.target.closest(".pswp-custom-thumb");
          if (thumb) {
            const index = parseInt(thumb.dataset.index);
            pswp.goTo(index);
          }
        });

        // Update active thumbnail on slide change
        pswp.on("change", () => {
          el.querySelectorAll(".pswp-custom-thumb").forEach((thumb, i) => {
            thumb.classList.toggle("pswp-custom-thumb--active", i === pswp.currIndex);
          });
        });
      }
    });
  });

  lightbox.init();
}

// ─────────────────────────────────────────────────────────────
// Open Lightbox
// ─────────────────────────────────────────────────────────────

function openAtIndex(index) {
  // Don't open lightbox if inside a dialog (e.g., quick view modal)
  if (document.querySelector("dialog[open]")) return;

  if (lightbox && imageData.length > 0) {
    lightbox.loadAndOpen(index);
  }
}

// ─────────────────────────────────────────────────────────────
// Click Handlers
// ─────────────────────────────────────────────────────────────

function handleGalleryClick(e) {
  const trigger = e.target.closest("[data-lightbox-trigger]");
  if (trigger) {
    e.preventDefault();
    const index = parseInt(trigger.dataset.lightboxTrigger) || 0;
    openAtIndex(index);
  }
}

function handleThumbClick(e) {
  const thumb = e.target.closest(".product-gallery-thumbs__slide");
  if (thumb && e.detail === 2) {
    // Double-click on thumbnail opens lightbox
    const thumbs = Array.from(document.querySelectorAll(".product-gallery-thumbs__slide"));
    const index = thumbs.indexOf(thumb);
    if (index >= 0) {
      openAtIndex(index);
    }
  }
}

// ─────────────────────────────────────────────────────────────
// Global Exposure
// ─────────────────────────────────────────────────────────────

window.openImageLightbox = openAtIndex;

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  initLightbox();

  // Click handlers for gallery images
  document.addEventListener("click", handleGalleryClick);
  document.addEventListener("dblclick", handleThumbClick);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

// Re-initialize when variant changes (gallery might be rebuilt)
window.addEventListener("product:variant-changed", () => {
  setTimeout(initLightbox, 100);
});

export { initLightbox, openAtIndex };
