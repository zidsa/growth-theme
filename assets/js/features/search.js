/**
 * Search Module
 *
 * Handles search dialog with live results.
 * Uses el-dialog for modal behavior.
 */

class SearchManager {
  constructor() {
    this.dialog = null;
    this.input = null;
    this.clearBtn = null;
    this.resultsContainer = null;
    this.productsContainer = null;
    this.loadingContainer = null;
    this.emptyContainer = null;
    this.searchAllLink = null;
    this.searchAllText = null;

    this.debounceTimeout = null;
    this.debounceDelay = 300;
    this.minQueryLength = 2;
    this.maxResults = 8;
  }

  init() {
    this.dialog = document.getElementById("search-dialog-wrapper");
    this.input = document.querySelector("[data-search-input]");
    this.clearBtn = document.querySelector("[data-search-clear]");
    this.resultsContainer = document.querySelector("[data-search-results]");
    this.productsContainer = document.querySelector("[data-search-products]");
    this.loadingContainer = document.querySelector("[data-search-loading]");
    this.emptyContainer = document.querySelector("[data-search-empty]");
    this.searchAllLink = document.querySelector("[data-search-all-link]");
    this.searchAllText = document.querySelector("[data-search-all-text]");

    if (!this.input) return;

    this.bindEvents();
  }

  bindEvents() {
    this.input.addEventListener("input", () => this.handleInput());

    if (this.clearBtn) {
      this.clearBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.clearInput();
        this.input.focus();
      });
    }

    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const query = this.input.value.trim();
        if (query.length >= this.minQueryLength) {
          this.navigateToSearch(query);
        }
      }
    });

    if (this.dialog) {
      this.dialog.addEventListener("open", () => {
        requestAnimationFrame(() => this.input.focus());
      });

      this.dialog.addEventListener("close", () => {
        this.clearInput();
        this.hideAllStates();
      });
    }
  }

  handleInput() {
    const query = this.input.value.trim();

    if (this.clearBtn) {
      this.clearBtn.classList.toggle("hidden", query.length === 0);
    }

    this.updateSearchAllLink(query);

    clearTimeout(this.debounceTimeout);

    if (query.length < this.minQueryLength) {
      this.hideAllStates();
      return;
    }

    this.debounceTimeout = setTimeout(() => {
      this.search(query);
    }, this.debounceDelay);
  }

  async search(query) {
    this.showLoading();

    try {
      const response = await zid.products.list(
        { page_size: this.maxResults, q: query },
        { showErrorNotification: false }
      );

      if (response && response.results && response.results.length > 0) {
        const products = response.results.map((product) => ({
          id: product.id,
          url: product.html_url,
          image: product.main_image?.image?.small || product.images?.[0]?.image?.small || null,
          name: product.name,
          price: product.formatted_price || "",
          salePrice: product.formatted_sale_price || null,
          hasOptions: product.has_options || false,
          rating: product.rating || null,
          badges: this.getProductBadges(product)
        }));
        this.showResults(products);
      } else {
        this.showEmpty();
      }
    } catch (error) {
      this.showEmpty();
    }
  }

  getProductBadges(product) {
    const badges = [];
    const lang = document.documentElement.lang || "ar";

    if (product.badge?.body) {
      const badgeText = product.badge.body[lang] || product.badge.body.ar || product.badge.body.en || "";
      if (badgeText) badges.push(badgeText);
    }

    if (product.sale_price && product.sale_price < product.price) {
      badges.push(lang === "ar" ? "تخفيض" : "SALE");
    }

    if (
      product.in_stock === false ||
      (product.is_infinite === false && product.quantity !== null && product.quantity <= 0)
    ) {
      badges.push(lang === "ar" ? "نفذت الكمية" : "OUT OF STOCK");
    }

    if (product.keywords?.length > 0 && badges.length < 2) {
      const remaining = 2 - badges.length;
      badges.push(...product.keywords.slice(0, remaining).map((k) => k.toUpperCase()));
    }

    return badges.slice(0, 2);
  }

  showResults(products) {
    this.hideAllStates();

    const html = products
      .map(
        (product) => `
      <a href="${product.url}" class="block w-[320px] shrink-0 md:w-[380px]">
        <div class="relative aspect-[3/4] overflow-hidden rounded">
          ${product.image ? `<img src="${product.image}" alt="${this.escapeHtml(product.name)}" class="h-full w-full object-cover" loading="lazy" />` : '<div class="bg-secondary h-full w-full rounded"></div>'}
          ${product.badges.length > 0 ? `<div class="absolute left-4 top-4 flex flex-col gap-1 rtl:left-auto rtl:right-4">${product.badges.map((b) => `<span class="bg-secondary text-foreground text-tagline rounded px-2 py-1">${this.escapeHtml(b)}</span>`).join("")}</div>` : ""}
        </div>
        <div class="mt-4 flex flex-col gap-2">
          <div class="flex flex-col gap-1">
            <h3 class="text-foreground text-h6 text-caps">${this.escapeHtml(product.name)}</h3>
            ${this.renderRating(product.rating)}
          </div>
          ${this.renderPrice(product)}
        </div>
      </a>
    `
      )
      .join("");

    if (this.productsContainer) {
      this.productsContainer.innerHTML = html;
    }
    if (this.resultsContainer) {
      this.resultsContainer.classList.remove("hidden");
      this.resultsContainer.classList.add("flex");
    }
  }

  renderRating(rating) {
    if (!rating || !rating.average) return "";

    const ratingRounded = Math.ceil(rating.average * 2) / 2;
    const starPath =
      "M8 11.1733L11.5733 13.3333L10.6933 9.30667L13.7333 6.59333L9.63333 6.28L8 2.5L6.36667 6.28L2.26667 6.59333L5.30667 9.30667L4.42667 13.3333L8 11.1733Z";

    let starsHtml = "";
    for (let n = 1; n <= 5; n++) {
      if (n <= ratingRounded) {
        starsHtml += `<svg class="size-4 text-foreground" viewBox="0 0 16 16" fill="currentColor"><path d="${starPath}"/></svg>`;
      } else if (n <= ratingRounded + 0.5) {
        starsHtml += `<svg class="size-4" viewBox="0 0 16 16" fill="none">
          <defs><linearGradient id="half-star-search-${n}"><stop offset="50%" stop-color="var(--color-foreground)"/><stop offset="50%" stop-color="var(--color-text-disabled)"/></linearGradient></defs>
          <path d="${starPath}" fill="url(#half-star-search-${n})"/>
        </svg>`;
      } else {
        starsHtml += `<svg class="size-4 text-text-disabled" viewBox="0 0 16 16" fill="currentColor"><path d="${starPath}"/></svg>`;
      }
    }

    return `
      <div class="flex items-center gap-2">
        <div class="flex gap-0.5">${starsHtml}</div>
        ${rating.total_count ? `<span class="text-muted text-body2">(${rating.total_count})</span>` : ""}
      </div>
    `;
  }

  renderPrice(product) {
    const fromPrefix = product.hasOptions ? "From " : "";

    if (product.salePrice) {
      return `
        <div class="flex flex-col">
          <p class="text-foreground text-body1">${fromPrefix}${this.escapeHtml(product.salePrice)}</p>
          <span class="text-destructive text-body2 line-through">${this.escapeHtml(product.price)}</span>
        </div>
      `;
    }

    return `<p class="text-foreground text-body1">${fromPrefix}${this.escapeHtml(product.price)}</p>`;
  }

  showLoading() {
    this.hideAllStates();
    if (this.loadingContainer) {
      this.loadingContainer.classList.remove("hidden");
      this.loadingContainer.classList.add("flex");
    }
  }

  showEmpty() {
    this.hideAllStates();
    if (this.emptyContainer) {
      this.emptyContainer.classList.remove("hidden");
      this.emptyContainer.classList.add("block");
    }
  }

  hideAllStates() {
    if (this.resultsContainer) {
      this.resultsContainer.classList.add("hidden");
      this.resultsContainer.classList.remove("flex");
    }
    if (this.loadingContainer) {
      this.loadingContainer.classList.add("hidden");
      this.loadingContainer.classList.remove("flex");
    }
    if (this.emptyContainer) {
      this.emptyContainer.classList.add("hidden");
      this.emptyContainer.classList.remove("block");
    }
  }

  updateSearchAllLink(query) {
    if (!this.searchAllLink || !this.searchAllText) return;

    const searchForText = this.searchAllText.textContent.split("'")[0];
    this.searchAllText.textContent = `${searchForText}'${query}'`;

    const url = new URL(window.location.origin + "/products");
    if (query) {
      url.searchParams.set("q", query);
    }
    this.searchAllLink.setAttribute("href", url.toString());
  }

  navigateToSearch(query) {
    const url = new URL(window.location.origin + "/products");
    url.searchParams.set("q", query);
    window.location.href = url.toString();
  }

  clearInput() {
    this.input.value = "";
    if (this.clearBtn) {
      this.clearBtn.classList.add("hidden");
    }
    this.updateSearchAllLink("");
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

// ─────────────────────────────────────────────────────────────
// Global Instance
// ─────────────────────────────────────────────────────────────

const searchManager = new SearchManager();
window.searchManager = searchManager;

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  searchManager.init();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

export { searchManager };
export default SearchManager;
