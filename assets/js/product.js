(function () {
  "use strict";

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

  function updatePrice(selectedProduct) {
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

  function updateProductInfo(selectedProduct) {
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

  function updateStockStatus(selectedProduct) {
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
    } else if (quantityEl.tagName === "INPUT") {
      // Update input max
      quantityEl.max = maxQuantity;
      quantityEl.value = Math.min(parseInt(quantityEl.value) || 1, maxQuantity);
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Gallery Updates
  // ─────────────────────────────────────────────────────────────

  /**
   * Update product gallery when variant changes
   * Rebuilds DOM and re-initializes EmblaCarousel
   */
  function updateProductImages(selectedProduct) {
    if (!selectedProduct) return;

    const media = selectedProduct.media || [];
    const galleryContainer = document.querySelector(
      `.product-gallery[data-gallery-id="${GALLERY_ID}"] .product-gallery__container`
    );
    const thumbsContainer = document.querySelector(
      `.product-gallery-thumbs[data-gallery-id="${GALLERY_ID}"] .product-gallery-thumbs__container`
    );
    const thumbsWrapper = document.querySelector(`.product-gallery-thumbs[data-gallery-id="${GALLERY_ID}"]`);

    if (!galleryContainer) return;

    // Destroy existing carousel instance
    if (typeof window.destroyProductGallery === "function") {
      window.destroyProductGallery(GALLERY_ID);
    }

    if (media.length > 0) {
      // Build main gallery slides
      galleryContainer.innerHTML = media
        .map(
          (item, index) => `
          <div class="product-gallery__slide min-w-0 flex-[0_0_75%] md:flex-[0_0_calc(100%-8px)]">
            <img
              src="${item.image?.medium || item.image?.full_size || ""}"
              alt="${selectedProduct.name || ""} - Image ${index + 1}"
              class="aspect-[3/4] w-full rounded object-cover"
              ${index > 0 ? 'loading="lazy"' : ""}
            />
          </div>
        `
        )
        .join("");

      // Build thumbnails (if more than 1 image)
      if (thumbsContainer) {
        if (media.length > 1) {
          thumbsContainer.innerHTML = media
            .map(
              (item) => `
              <button
                class="product-gallery-thumbs__slide hover:border-primary relative min-w-0 flex-[0_0_calc(25%-8px)] overflow-hidden rounded border-1 border-transparent transition-colors"
                data-gallery-id="${GALLERY_ID}"
                type="button"
              >
                <img
                  src="${item.image?.thumbnail || item.image?.medium || ""}"
                  alt="Thumbnail"
                  class="aspect-square w-full object-cover"
                  loading="lazy"
                />
              </button>
            `
            )
            .join("");

          if (thumbsWrapper) thumbsWrapper.classList.remove("hidden");
        } else {
          if (thumbsWrapper) thumbsWrapper.classList.add("hidden");
        }
      }

      // Re-initialize carousel after DOM update
      requestAnimationFrame(() => {
        if (typeof window.initializeProductGallery === "function") {
          window.initializeProductGallery(GALLERY_ID);
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
  // Quantity Input Handlers
  // ─────────────────────────────────────────────────────────────

  function initQuantityHandlers() {
    const quantityInput = document.querySelector("#product-quantity");
    if (!quantityInput) return;

    const wrapper = quantityInput.closest(".qty-input");
    const decreaseBtn = wrapper?.querySelector('[data-quantity-action="decrease"]');
    const increaseBtn = wrapper?.querySelector('[data-quantity-action="increase"]');

    // Update productObj when quantity changes
    const updateSelectedQuantity = () => {
      if (window.productObj?.selected_product) {
        window.productObj.selected_product.selected_quantity = Number(quantityInput.value) || 1;
      }
    };

    quantityInput.addEventListener("change", updateSelectedQuantity);
    quantityInput.addEventListener("input", updateSelectedQuantity);

    // Decrease button handler
    if (decreaseBtn) {
      decreaseBtn.addEventListener("click", () => {
        const current = parseInt(quantityInput.value) || 1;
        const min = parseInt(quantityInput.min) || 1;
        if (current > min) {
          quantityInput.value = current - 1;
          quantityInput.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
    }

    // Increase button handler
    if (increaseBtn) {
      increaseBtn.addEventListener("click", () => {
        const current = parseInt(quantityInput.value) || 1;
        const max = quantityInput.max ? parseInt(quantityInput.max) : Infinity;
        if (current < max) {
          quantityInput.value = current + 1;
          quantityInput.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Initialization
  // ─────────────────────────────────────────────────────────────

  function init() {
    initQuantityHandlers();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Re-init when quick view content loads
  window.addEventListener("quick-view-content-loaded", initQuantityHandlers);
})();
