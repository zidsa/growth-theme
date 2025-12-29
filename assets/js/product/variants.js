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
    const threshold = window.storeLowStockThreshold || 5;
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

  if (!galleryContainer) return;

  // Destroy existing carousel instance
  if (typeof window.destroyProductGallery === "function") {
    window.destroyProductGallery(GALLERY_ID);
  }

  if (media.length > 0) {
    // Build main gallery slides (with video support)
    galleryContainer.innerHTML = media
      .map((item, index) => {
        const isVideo = item.provider && item.link;
        const imgSrc = item.image?.medium || item.image?.full_size || "";

        console.log("item", item);
        console.log("isVideo", isVideo);
        if (isVideo) {
          return `
          <div class="product-gallery__slide relative min-w-0 flex-[0_0_75%] md:flex-[0_0_calc(100%-8px)]">
            <img
              src="${imgSrc}"
              alt="${selectedProduct.name || ""} - Image ${index + 1}"
              class="aspect-[3/4] w-full rounded object-cover"
              ${index > 0 ? 'loading="lazy"' : ""}
            />
            <button
              type="button"
              class="absolute inset-0 flex cursor-pointer items-center justify-center bg-black/20 transition-colors hover:bg-black/30"
              data-video-play
              data-video-src="${item.link}"
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
        <div class="product-gallery__slide relative min-w-0 flex-[0_0_75%] md:flex-[0_0_calc(100%-8px)]">
          <img
            src="${imgSrc}"
            alt="${selectedProduct.name || ""} - Image ${index + 1}"
            class="aspect-[3/4] w-full cursor-zoom-in rounded object-cover"
            data-lightbox-trigger="${index}"
            ${index > 0 ? 'loading="lazy"' : ""}
          />
        </div>
      `;
      })
      .join("");

    // Build hidden lightbox gallery for PhotoSwipe (images only, no videos)
    if (lightboxGallery) {
      lightboxGallery.innerHTML = media
        .filter((item) => !(item.provider && item.link)) // Exclude videos
        .map(
          (item, index) => `
          <a
            href="${item.image?.full_size || item.image?.medium || ""}"
            data-pswp-width="1600"
            data-pswp-height="2133"
          >
            <img
              src="${item.image?.thumbnail || item.image?.medium || ""}"
              alt="${selectedProduct.name || ""} - Image ${index + 1}"
            />
          </a>
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
            const thumbSrc = item.image?.thumbnail || item.image?.medium || "";

            return `
            <button
              class="product-gallery-thumbs__slide hover:border-primary relative min-w-0 flex-[0_0_calc(25%-8px)] overflow-hidden rounded border-1 border-transparent transition-colors"
              data-gallery-id="${GALLERY_ID}"
              type="button"
            >
              <img
                src="${thumbSrc}"
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
}

// Expose for external use
window.updateProductImages = updateProductImages;

// ─────────────────────────────────────────────────────────────
// Main Callback (Called by platform's product.js)
// ─────────────────────────────────────────────────────────────

/**
 * Called by platform's product.js after variant selection changes
 * @param {Object} selectedProduct - The selected variant data from API
 */
window.productOptionsChanged = function (selectedProduct) {
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
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
