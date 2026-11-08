/**
 * Product Variants Module
 *
 * Handles variant selection UI updates:
 * - Price updates
 * - Product info (SKU, weight, badges)
 * - Stock status
 * - Gallery image updates
 *
 * Platform Callback (MUST KEEP):
 * - window.productOptionsChanged - Called by platform after variant API
 */

import { escapeAttr, imageUrl } from "../utils/image-url.js";

const GALLERY_ID = "product-gallery";

// ─────────────────────────────────────────────────────────────
// Utility Functions
// ─────────────────────────────────────────────────────────────

function show(selector) {
  const el = document.querySelector(selector);
  if (el) {
    el.classList.remove("hidden", "d-none");
    el.style.display = "";
  }
}

function hide(selector) {
  const el = document.querySelector(selector);
  if (el) {
    el.classList.add("hidden");
    el.style.display = "none";
  }
}

// ─────────────────────────────────────────────────────────────
// Price Updates
// ─────────────────────────────────────────────────────────────

export function updatePrice(selectedProduct) {
  if (!selectedProduct) return;

  const priceEl = document.querySelector("[data-product-price]");
  const priceOldEl = document.querySelector("[data-product-price-old]");
  const discountEl = document.querySelector("[data-product-discount]");

  const hasDiscount = !!selectedProduct.formatted_sale_price;

  if (priceEl) {
    priceEl.textContent = hasDiscount ? selectedProduct.formatted_sale_price : selectedProduct.formatted_price;
  }

  if (priceOldEl) {
    if (hasDiscount) {
      priceOldEl.textContent = selectedProduct.formatted_price;
      priceOldEl.classList.remove("hidden");
    } else {
      priceOldEl.textContent = "";
      priceOldEl.classList.add("hidden");
    }
  }

  if (discountEl) {
    if (hasDiscount && selectedProduct.discount_percentage) {
      const discountText = window.productTranslations?.discount || "Discount";
      discountEl.textContent = `${discountText} ${selectedProduct.discount_percentage}%`;
      discountEl.classList.remove("hidden");
    } else {
      discountEl.textContent = "";
      discountEl.classList.add("hidden");
    }
  }
}

// ─────────────────────────────────────────────────────────────
// Product Info Updates
// ─────────────────────────────────────────────────────────────

export function updateProductInfo(selectedProduct) {
  if (!selectedProduct) return;

  // Update SKU
  const skuEl = document.querySelector("[data-product-sku]");
  const skuWrapper = document.querySelector("[data-product-sku-wrapper]");
  if (skuEl && skuWrapper) {
    if (selectedProduct.sku) {
      skuEl.textContent = selectedProduct.sku;
      show("[data-product-sku-wrapper]");
    } else {
      hide("[data-product-sku-wrapper]");
    }
  }

  // Update Weight
  const weightEl = document.querySelector("[data-product-weight]");
  const weightWrapper = document.querySelector("[data-product-weight-wrapper]");
  if (weightEl && weightWrapper) {
    if (selectedProduct.weight?.value) {
      weightEl.textContent = `${selectedProduct.weight.value} ${selectedProduct.weight.unit || ""}`;
      show("[data-product-weight-wrapper]");
    } else {
      hide("[data-product-weight-wrapper]");
    }
  }

  // Update Low Stock Badge
  const lowStockBadge = document.querySelector("[data-low-stock-badge]");
  if (lowStockBadge) {
    const threshold = window.storeLowStockThreshold || 10;
    if (window.storeLowStockEnabled && !selectedProduct.is_infinite && selectedProduct.quantity < threshold) {
      const template = window.productTranslations?.remaining || "Remaining %s only";
      lowStockBadge.querySelector("[data-low-stock-text]")?.textContent ||
        (lowStockBadge.textContent = template.replace("%s", selectedProduct.quantity));
      show("[data-low-stock-badge]");
    } else {
      hide("[data-low-stock-badge]");
    }
  }

  // Update Sold Count Badge
  const soldBadge = document.querySelector("[data-sold-count-badge]");
  if (soldBadge && selectedProduct.sold_products_count) {
    const template = window.productTranslations?.sold || "Sold more than %s times";
    const textEl = soldBadge.querySelector("[data-sold-count-text]");
    if (textEl) {
      textEl.textContent = template.replace("%s", selectedProduct.sold_products_count);
    }
    show("[data-sold-count-badge]");
  } else if (soldBadge) {
    hide("[data-sold-count-badge]");
  }
}

// ─────────────────────────────────────────────────────────────
// Stock & Quantity Updates
// ─────────────────────────────────────────────────────────────

export function updateStockStatus(selectedProduct) {
  var canPreorder = document.querySelector("[data-can-preorder]")?.getAttribute("data-can-preorder") === "true";
  if (!selectedProduct) return;

  // Update hidden product ID
  const productIdInput = document.querySelector("#product-id");
  if (productIdInput) {
    productIdInput.value = selectedProduct.id;
  }

  const inStockSection = document.querySelector("[data-in-stock]");
  const outOfStockSection = document.querySelector("[data-out-of-stock]");
  const quantityWrapper = document.querySelector("[data-quantity-wrapper]");

  if (selectedProduct.in_stock) {
    // Show in-stock elements
    if (inStockSection) show("[data-in-stock]");
    if (outOfStockSection) hide("[data-out-of-stock]");

    // Update quantity selector
    updateQuantitySelector(selectedProduct);
    if (quantityWrapper) show("[data-quantity-wrapper]");
  } else if (canPreorder || selectedProduct.can_be_preordered) {
    if (outOfStockSection) hide("[data-out-of-stock]");
    if (quantityWrapper) hide("[data-quantity-wrapper]");

  } else {
    // Show out-of-stock elements
    if (inStockSection) hide("[data-in-stock]");
    if (outOfStockSection) show("[data-out-of-stock]");
    if (quantityWrapper) hide("[data-quantity-wrapper]");
  }
}

function updateQuantitySelector(selectedProduct) {
  const quantityEl = document.querySelector("#product-quantity");
  if (!quantityEl) return;

  let maxQuantity = selectedProduct.is_infinite ? 100 : selectedProduct.quantity;
  maxQuantity = Math.min(maxQuantity, 100);

  if (quantityEl.tagName === "SELECT") {
    // Rebuild select options
    let options = "";
    for (let i = 1; i <= maxQuantity; i++) {
      options += `<option value="${i}"${i === 1 ? " selected" : ""}>${i}</option>`;
    }
    quantityEl.innerHTML = options;
  } else if (quantityEl.tagName === "INPUT" && window.updateQtyMax) {
    // Delegate to qty-input.js
    window.updateQtyMax("product-quantity", maxQuantity);
  }
}

// ─────────────────────────────────────────────────────────────
// Gallery Updates
// ─────────────────────────────────────────────────────────────

// Same responsive widths/quality as components/products/product-gallery.jinja
const MAIN_IMAGE_WIDTHS = [400, 640, 750, 960, 1200];
const MAIN_IMAGE_SIZES = "(max-width: 640px) 100vw, 50vw";

function mainImageSrc(item) {
  return item.image?.large || item.image?.full_size || "";
}

function mediaAlt(item, productName, index) {
  return item.alt_text || `${productName || ""} - Image ${index + 1}`;
}

/**
 * True when the gallery already shows exactly this media list (same order).
 * The platform calls productOptionsChanged on load with the server-rendered
 * variant, so rebuilding here would only re-download the same images.
 */
function galleryShowsMedia(galleryContainer, media) {
  const current = Array.from(galleryContainer.querySelectorAll("img[data-media-src]")).map(
    (img) => img.dataset.mediaSrc
  );
  const next = media.map(mainImageSrc);
  return current.length === next.length && current.every((src, i) => src === next[i]);
}

function mainImageMarkup(item, index, alt, isVideo, lightboxIndex) {
  const src = mainImageSrc(item);
  const srcset = MAIN_IMAGE_WIDTHS.map((w) => `${imageUrl(src, { w, q: 90, f: "auto" })} ${w}w`).join(", ");

  return `
    <img
      data-media-src="${escapeAttr(src)}"
      width="1000"
      height="1000"
      src="${escapeAttr(imageUrl(src, { w: 750, q: 90, f: "auto" }))}"
      srcset="${escapeAttr(srcset)}"
      sizes="${MAIN_IMAGE_SIZES}"
      alt="${escapeAttr(alt)}"
      class="${isVideo ? "" : "cursor-zoom-in"} h-[500px] w-full md:h-[650px] rounded object-contain"
      ${isVideo ? "" : `data-lightbox-trigger="${lightboxIndex}"`}
      ${index > 0 ? 'loading="lazy"' : ""}
    />
  `;
}

/**
 * Update product gallery when variant changes
 * Rebuilds DOM and re-initializes EmblaCarousel
 */
export function updateProductImages(selectedProduct) {
  if (!selectedProduct) return;

  const media = selectedProduct.media || [];
  const galleryContainer = document.querySelector(
    `.product-gallery[data-gallery-id="${GALLERY_ID}"] .product-gallery__container`
  );
  const thumbsContainer = document.querySelector(
    `.product-gallery-thumbs[data-gallery-id="${GALLERY_ID}"] .product-gallery-thumbs__container`
  );
  const thumbsWrapper = document.querySelector(`.product-gallery-thumbs[data-gallery-id="${GALLERY_ID}"]`);
  const lightboxGallery = document.getElementById("product-gallery-lightbox");

  if (!galleryContainer || media.length === 0) return;

  // Same media already rendered (e.g. initial call with the server-rendered variant):
  // keep the existing responsive images and the currently selected slide.
  if (galleryShowsMedia(galleryContainer, media)) return;

  // Destroy existing carousel instance
  if (typeof window.destroyProductGallery === "function") {
    window.destroyProductGallery(GALLERY_ID);
  }

  const productName = selectedProduct.name || "";
  let lightboxIndex = 0;

  // Build main gallery slides (with video support)
  galleryContainer.innerHTML = media
    .map((item, index) => {
      const isVideo = Boolean(item.provider && item.link);
      const alt = mediaAlt(item, productName, index);
      const img = mainImageMarkup(item, index, alt, isVideo, isVideo ? null : lightboxIndex++);

      if (isVideo) {
        return `
        <div class="product-gallery__slide relative min-w-0 flex-[0_0_100%]">
          ${img}
          <button
            type="button"
            class="absolute inset-0 flex cursor-pointer items-center justify-center bg-black/20 transition-colors hover:bg-black/30"
            data-video-play
            data-video-src="${escapeAttr(item.link)}"
            aria-label="Play video"
          >
            <span class="bg-background/90 flex size-16 items-center justify-center rounded-full shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="text-foreground size-8 rtl:rotate-180">
                <path d="M8 5.14v14l11-7-11-7z" />
              </svg>
            </span>
          </button>
          <div class="absolute inset-0 hidden rounded bg-black" data-video-container>
            <button
              type="button"
              class="bg-background/80 text-foreground absolute end-2 top-2 z-10 flex size-8 items-center justify-center rounded-full"
              data-video-close
              aria-label="Close video"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="size-5">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
            <iframe class="size-full rounded" src="" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
          </div>
        </div>
      `;
      }

      return `
      <div class="product-gallery__slide relative min-w-0 flex-[0_0_100%]">
        ${img}
      </div>
    `;
    })
    .join("");

  // Rebuild hidden lightbox data for PhotoSwipe (images only, no videos).
  // Data attributes only (no <img>) so zoom images load only when the lightbox opens.
  if (lightboxGallery) {
    lightboxGallery.innerHTML = media
      .map((item, index) => ({ item, index }))
      .filter(({ item }) => !(item.provider && item.link))
      .map(
        ({ item, index }) => `
        <a
          href="${escapeAttr(imageUrl(item.image?.full_size || item.image?.large || "", { w: 1600, q: 90, f: "auto" }))}"
          data-pswp-width="1600"
          data-pswp-height="2133"
          data-thumb-src="${escapeAttr(imageUrl(item.image?.thumbnail || item.image?.medium || "", { w: 160, q: 85, f: "auto" }))}"
          data-alt="${escapeAttr(mediaAlt(item, productName, index))}"
        ></a>
      `
      )
      .join("");
  }

  // Build thumbnails (if more than 1 image, with video indicator)
  if (thumbsContainer) {
    if (media.length > 1) {
      thumbsContainer.innerHTML = media
        .map((item, index) => {
          const isVideo = item.provider && item.link;
          const thumbSrc = imageUrl(item.image?.thumbnail || item.image?.medium || "", { w: 256, q: 85, f: "auto" });

          return `
          <button
            class="product-gallery-thumbs__slide hover:border-primary relative min-w-0 flex-[0_0_calc(25%-8px)] overflow-hidden rounded border-1 border-transparent transition-colors"
            data-gallery-id="${GALLERY_ID}"
            type="button"
          >
            <img
              src="${escapeAttr(thumbSrc)}"
              width="256"
              height="256"
              alt="Thumbnail ${index + 1}"
              class="aspect-square w-full object-cover"
              loading="lazy"
            />
            ${
              isVideo
                ? `<span class="bg-background/80 absolute inset-0 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="text-foreground size-6 rtl:rotate-180">
                  <path d="M8 5.14v14l11-7-11-7z" />
                </svg>
              </span>`
                : ""
            }
          </button>
        `;
        })
        .join("");

      if (thumbsWrapper) thumbsWrapper.classList.remove("hidden");
    } else {
      if (thumbsWrapper) thumbsWrapper.classList.add("hidden");
    }
  }

  // Re-initialize carousel after DOM update
  requestAnimationFrame(() => {
    if (typeof window.initProductGallery === "function") {
      window.initProductGallery(GALLERY_ID);
    }
  });
}

// Expose for external use
window.updateProductImages = updateProductImages;

// ─────────────────────────────────────────────────────────────
// Selected Option Labels
// ─────────────────────────────────────────────────────────────

export function updateSelectedOptionLabels() {
  document.querySelectorAll(".product-options__group").forEach((group) => {
    const label = group.querySelector(".product-options__label");
    if (!label) return;

    const activeOption = group.querySelector(".product-options__item.active[value]");
    const selectedValue = activeOption?.getAttribute("value");
    let selectedValueElement = label.querySelector("[data-selected-option-value]");

    if (!selectedValue) {
      selectedValueElement?.remove();
      return;
    }

    if (!selectedValueElement) {
      selectedValueElement = document.createElement("span");
      selectedValueElement.setAttribute("data-selected-option-value", "");
      label.append(selectedValueElement);
    }

    selectedValueElement.textContent = `: ${selectedValue}`;
  });
}

// ─────────────────────────────────────────────────────────────
// Main Callback (Called by platform's product.js)
// ─────────────────────────────────────────────────────────────

/**
 * Called by platform's product.js after variant selection changes
 * @param {Object} selectedProduct - The selected variant data from API
 */
window.productOptionsChanged = function (selectedProduct) {
  updateSelectedOptionLabels();

  var hasPreorder = document.querySelector("[data-has-preorder]")?.getAttribute("data-has-preorder") === "true";;
  var canPreorder = document.querySelector("[data-can-preorder]")?.getAttribute("data-can-preorder") === "true";
  var stockBehavior = document.querySelector("[data-stock-behavior]")?.getAttribute("data-stock-behavior") || '';

  if (!selectedProduct) {
    // Variant doesn't exist - show out of stock
    hide("[data-in-stock]");
    show("[data-out-of-stock]");
    hide("[data-quantity-wrapper]");
    return;
  }

  // Update all UI sections
  updatePrice(selectedProduct);
  updateProductInfo(selectedProduct);
  updateStockStatus(selectedProduct);
  updateProductImages(selectedProduct);

  // Dispatch custom event for other scripts
  window.dispatchEvent(
    new CustomEvent("product:variant-changed", {
      detail: { selectedProduct }
    })
  );
};

// ─────────────────────────────────────────────────────────────
// Quantity Sync with productObj
// ─────────────────────────────────────────────────────────────

function initProductObjSync() {
  // Update productObj.selected_quantity when quantity changes
  // Button handlers are managed by qty-input.js
  document.addEventListener("qty:change", (e) => {
    if (e.detail?.id === "product-quantity" && window.productObj?.selected_product) {
      window.productObj.selected_product.selected_quantity = Number(e.detail.value) || 1;
    }
  });
}

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  initProductObjSync();
  updateSelectedOptionLabels();
  window.addEventListener("content:loaded", updateSelectedOptionLabels);
}

if (document.readyState === "loading") {
  if (window.checkout_dialog) {
    document.getElementsByClassName('btn-buy-now')[0].classList.remove('hidden');
  }
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
