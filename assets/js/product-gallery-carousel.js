/**
 * Product Gallery Carousel Initialization
 * Initializes EmblaCarousel for product galleries (both Jinja and JS rendered)
 *
 * Usage:
 * - Automatically initializes all galleries on page load
 * - Call initializeProductGallery(galleryId) for dynamically added galleries
 * - Call initializeAllProductGalleries() to re-scan the page
 */

(function () {
  // Check if EmblaCarousel is available
  if (typeof EmblaCarousel === "undefined") {
    return;
  }

  // Store initialized galleries to prevent double initialization
  const initializedGalleries = new Map();

  /**
   * Initialize a single product gallery
   * @param {String} galleryId - The gallery ID from data-gallery-id attribute
   */
  function initializeProductGallery(galleryId) {
    // Destroy existing instance if it exists
    destroyProductGallery(galleryId);

    // Find gallery elements by gallery ID
    const galleryNode = document.querySelector(`.product-gallery[data-gallery-id="${galleryId}"]`);
    const thumbsNode = document.querySelector(`.product-gallery-thumbs[data-gallery-id="${galleryId}"]`);

    if (!galleryNode) {
      return;
    }

    // Check RTL direction
    const isRTL = document.documentElement.dir === "rtl" || document.body.dir === "rtl";

    // Initialize main gallery carousel
    const emblaApi = EmblaCarousel(galleryNode, {
      direction: isRTL ? "rtl" : "ltr",
      loop: false,
      align: "start",
      slidesToScroll: 1,
      skipSnaps: false,
      containScroll: "trimSnaps"
    });

    // Initialize thumbnails carousel (if exists)
    let emblaThumbsApi = null;
    if (thumbsNode) {
      emblaThumbsApi = EmblaCarousel(thumbsNode, {
        containScroll: "keepSnaps",
        dragFree: true,
        direction: isRTL ? "rtl" : "ltr"
      });
    }

    // Get buttons and progress bar
    const prevBtn = document.querySelector(`.product-gallery__prev[data-gallery-id="${galleryId}"]`);
    const nextBtn = document.querySelector(`.product-gallery__next[data-gallery-id="${galleryId}"]`);
    const prevBtnMobile = document.querySelector(`.product-gallery__prev-mobile[data-gallery-id="${galleryId}"]`);
    const nextBtnMobile = document.querySelector(`.product-gallery__next-mobile[data-gallery-id="${galleryId}"]`);
    const thumbButtons = document.querySelectorAll(`.product-gallery-thumbs__slide[data-gallery-id="${galleryId}"]`);
    const progressBar = document.querySelector(`.product-gallery__progress-bar[data-gallery-id="${galleryId}"]`);

    // Create handler functions (stored for cleanup)
    const handlers = {
      prevClick: () => emblaApi.scrollPrev(),
      nextClick: () => emblaApi.scrollNext(),
      thumbClicks: []
    };

    // Previous/Next button handlers (Desktop)
    // Embla handles RTL direction internally via direction option
    if (prevBtn) {
      prevBtn.addEventListener("click", handlers.prevClick);
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", handlers.nextClick);
    }

    // Previous/Next button handlers (Mobile)
    if (prevBtnMobile) {
      prevBtnMobile.addEventListener("click", handlers.prevClick);
    }
    if (nextBtnMobile) {
      nextBtnMobile.addEventListener("click", handlers.nextClick);
    }

    // Thumbnail click handlers
    thumbButtons.forEach((btn, index) => {
      const handler = () => emblaApi.scrollTo(index);
      handlers.thumbClicks.push(handler);
      btn.addEventListener("click", handler);
    });

    // Helper function to clamp values
    const clamp = (n, min, max) => Math.max(min, Math.min(n, max));

    // Update progress bar
    const updateProgress = () => {
      if (progressBar) {
        const progress = clamp(emblaApi.scrollProgress(), 0, 1);
        progressBar.style.width = `${progress * 100}%`;
      }

      // Update button states (Desktop)
      if (prevBtn) {
        prevBtn.disabled = !emblaApi.canScrollPrev();
      }
      if (nextBtn) {
        nextBtn.disabled = !emblaApi.canScrollNext();
      }

      // Update button states (Mobile)
      if (prevBtnMobile) {
        prevBtnMobile.disabled = !emblaApi.canScrollPrev();
      }
      if (nextBtnMobile) {
        nextBtnMobile.disabled = !emblaApi.canScrollNext();
      }
    };

    // Update active thumbnail and scroll thumbnail carousel
    const updateActiveThumb = () => {
      const selectedIndex = emblaApi.selectedScrollSnap();

      // Update border styling
      thumbButtons.forEach((btn, index) => {
        if (index === selectedIndex) {
          btn.classList.add("border-primary");
          btn.classList.remove("border-transparent");
        } else {
          btn.classList.remove("border-primary");
          btn.classList.add("border-transparent");
        }
      });

      // Scroll thumbnail carousel to show active thumbnail
      if (emblaThumbsApi) {
        emblaThumbsApi.scrollTo(selectedIndex);
      }
    };

    // Listen to gallery changes
    emblaApi.on("init", updateProgress);
    emblaApi.on("scroll", updateProgress);
    emblaApi.on("reInit", updateProgress);
    emblaApi.on("select", updateActiveThumb);

    // Set initial states
    updateProgress();
    updateActiveThumb();

    // Store instances and references for cleanup later
    initializedGalleries.set(galleryId, {
      emblaApi,
      emblaThumbsApi,
      handlers,
      elements: { prevBtn, nextBtn, prevBtnMobile, nextBtnMobile, thumbButtons }
    });
  }

  /**
   * Initialize all product galleries on the page
   */
  function initializeAllProductGalleries() {
    const galleries = document.querySelectorAll(".product-gallery[data-gallery-id]");

    galleries.forEach((gallery) => {
      const galleryId = gallery.getAttribute("data-gallery-id");
      if (galleryId) {
        initializeProductGallery(galleryId);
      }
    });
  }

  /**
   * Destroy a product gallery instance
   * @param {String} galleryId - The gallery ID to destroy
   */
  function destroyProductGallery(galleryId) {
    if (initializedGalleries.has(galleryId)) {
      const instance = initializedGalleries.get(galleryId);
      const { handlers, elements } = instance;

      // Remove event listeners
      if (elements.prevBtn) {
        elements.prevBtn.removeEventListener("click", handlers.prevClick);
      }
      if (elements.nextBtn) {
        elements.nextBtn.removeEventListener("click", handlers.nextClick);
      }
      if (elements.prevBtnMobile) {
        elements.prevBtnMobile.removeEventListener("click", handlers.prevClick);
      }
      if (elements.nextBtnMobile) {
        elements.nextBtnMobile.removeEventListener("click", handlers.nextClick);
      }
      elements.thumbButtons.forEach((btn, index) => {
        btn.removeEventListener("click", handlers.thumbClicks[index]);
      });

      // Destroy Embla instances
      if (instance.emblaApi) instance.emblaApi.destroy();
      if (instance.emblaThumbsApi) instance.emblaThumbsApi.destroy();

      initializedGalleries.delete(galleryId);
    }
  }

  // Auto-initialize on page load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAllProductGalleries);
  } else {
    initializeAllProductGalleries();
  }

  // Expose functions globally for dynamic use
  window.initializeProductGallery = initializeProductGallery;
  window.initializeAllProductGalleries = initializeAllProductGalleries;
  window.destroyProductGallery = destroyProductGallery;
})();
