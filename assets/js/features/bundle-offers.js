/**
 * Bundle Offers Module
 *
 * Fetches and displays bundle offers for products in listings.
 * Bundle offer data is not included in product listing API, so we fetch it separately.
 */

const BundleOffersLoader = {
  baseUrl: window.location.origin,
  loadedOffers: new Map(),

  collectProductIds() {
    const productIds = new Set();
    const elements = document.querySelectorAll(".bundle-offer-badge[data-bundle-offer-product-id]");

    elements.forEach((el) => {
      const productId = el.getAttribute("data-bundle-offer-product-id");
      if (productId && !this.loadedOffers.has(productId)) {
        productIds.add(productId);
      }
    });

    return Array.from(productIds);
  },

  async fetchBundleOffers(productIds) {
    if (!productIds || productIds.length === 0) {
      return null;
    }

    const params = productIds.map((id) => `product_ids=${id}`).join("&");
    const url = `${this.baseUrl}/api/v1/products/bundle-offers?${params}`;

    try {
      const response = await fetch(url);
      if (!response.ok) {
        console.error("Failed to fetch bundle offers:", response.status);
        return null;
      }

      return await response.json();
    } catch (error) {
      console.error("Error fetching bundle offers:", error);
      return null;
    }
  },

  createTagIcon() {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", "16");
    svg.setAttribute("height", "16");
    svg.setAttribute("viewBox", "0 0 16 16");
    svg.setAttribute("fill", "none");

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute(
      "d",
      "M8.57129 1.25488H13.6562C13.9618 1.25489 14.2228 1.36327 14.4404 1.58105C14.6581 1.79871 14.7666 2.05976 14.7666 2.36523V7.4375C14.7666 7.58599 14.7358 7.72769 14.6738 7.8623C14.6115 7.99756 14.5316 8.11495 14.4346 8.21484L8.2334 14.4287C8.12146 14.5288 7.99845 14.606 7.86426 14.6602C7.73001 14.7143 7.5927 14.7412 7.45312 14.7412C7.31346 14.7412 7.17481 14.7155 7.03711 14.6641C6.89982 14.6127 6.77477 14.5342 6.66309 14.4287L1.5918 9.34082L1.59082 9.33984L1.51367 9.26074C1.4414 9.17848 1.38421 9.08497 1.34277 8.97949C1.28714 8.83758 1.25977 8.69644 1.25977 8.55762C1.25981 8.41792 1.28642 8.27939 1.33984 8.1416C1.39308 8.00461 1.47689 7.88034 1.5918 7.76855V7.76758L7.78027 1.58691H7.78125C7.88159 1.48455 8.00131 1.40329 8.14062 1.34375C8.2797 1.28424 8.42318 1.25489 8.57129 1.25488ZM8.55859 2.35156L2.33984 8.56152L2.32227 8.5791L2.33984 8.59668L7.40723 13.6816L7.42578 13.6992L7.44336 13.6816L13.6738 7.4209L13.6816 7.41406V2.34375H8.56641L8.55859 2.35156ZM11.9102 3.26074C12.1369 3.26074 12.333 3.34394 12.499 3.51074C12.6651 3.67744 12.748 3.87218 12.748 4.09668C12.748 4.32117 12.6653 4.51613 12.499 4.68262C12.3328 4.84889 12.1368 4.93153 11.9102 4.93164C11.6835 4.93164 11.4879 4.84927 11.3232 4.68262C11.1583 4.51565 11.0762 4.31964 11.0762 4.09473C11.0763 3.87001 11.1582 3.67486 11.3232 3.50879C11.4883 3.34293 11.6837 3.26084 11.9102 3.26074Z"
    );
    path.setAttribute("fill", "currentColor");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "0.05");

    svg.appendChild(path);
    return svg;
  },

  displayBundleOffer(productId, bundleOffer) {
    const elements = document.querySelectorAll(`.bundle-offer-badge[data-bundle-offer-product-id="${productId}"]`);

    elements.forEach((el) => {
      if (bundleOffer && bundleOffer.name) {
        el.className = "badge badge-outlined text-destructive border-destructive";
        el.appendChild(this.createTagIcon());

        const text = document.createTextNode(bundleOffer.name);
        el.appendChild(text);

        this.loadedOffers.set(productId, bundleOffer);
      }
    });
  },

  async loadBundleOffers() {
    const productIds = this.collectProductIds();

    if (productIds.length === 0) {
      return;
    }

    const bundleOffersData = await this.fetchBundleOffers(productIds);

    if (bundleOffersData && bundleOffersData.payload) {
      bundleOffersData.payload.forEach((bundleOffer) => {
        if (bundleOffer.product_ids && bundleOffer.product_ids.length > 0) {
          bundleOffer.product_ids.forEach((productId) => {
            this.displayBundleOffer(productId, bundleOffer);
          });
        }
      });
    }
  },

  reload() {
    this.loadBundleOffers();
  }
};

// Expose globally
window.bundleOffersLoader = BundleOffersLoader;

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  BundleOffersLoader.loadBundleOffers();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

export { BundleOffersLoader };
