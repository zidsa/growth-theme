/**
 * Embla Carousel Factory
 *
 * Creates consistent carousel instances with common features:
 * - RTL support (automatic)
 * - Navigation buttons
 * - Dots
 * - Progress bar
 * - Thumbnail sync
 * - Autoplay
 * - Fade effect
 */

import EmblaCarousel from "embla-carousel";
import Autoplay from "embla-carousel-autoplay";
import Fade from "embla-carousel-fade";
import AutoScroll from "embla-carousel-auto-scroll";

/**
 * Create a carousel instance
 *
 * @param {HTMLElement|string} container - Container element or selector
 * @param {Object} options - Configuration options
 * @param {boolean} options.loop - Enable infinite loop (default: false)
 * @param {string} options.align - Slide alignment: 'start' | 'center' | 'end' (default: 'start')
 * @param {boolean} options.fade - Enable fade transition (default: false)
 * @param {number|false} options.autoplay - Autoplay delay in ms, false to disable (default: false)
 * @param {number|false} options.autoScroll - Auto-scroll speed, false to disable (default: false)
 * @param {boolean} options.dragFree - Enable free dragging (default: false)
 *
 * @returns {Object} Carousel instance with methods: scrollTo, scrollPrev, scrollNext, destroy, embla
 *
 * @example
 * // Basic carousel
 * const carousel = createCarousel('#my-carousel');
 *
 * // With autoplay and fade
 * const heroCarousel = createCarousel(element, {
 *   loop: true,
 *   autoplay: 5000,
 *   fade: true
 * });
 *
 * // Cleanup
 * carousel.destroy();
 */
export function createCarousel(container, options = {}) {
  const containerEl = typeof container === "string" ? document.querySelector(container) : container;

  if (!containerEl) {
    console.warn("Carousel container not found:", container);
    return null;
  }

  // Find viewport (may be a child element or the container itself)
  const viewport =
    containerEl.querySelector("[data-carousel-viewport]") ||
    containerEl.querySelector(".embla__viewport") ||
    containerEl.querySelector(".embla") ||
    containerEl;

  // Check if we have slides
  const slides = viewport.querySelectorAll(
    ".embla__slide, .product-gallery__slide, .product-gallery-thumbs__slide, [data-carousel-slide]"
  );
  if (slides.length <= 1 && !options.forceInit) {
    return null;
  }

  // RTL support
  const isRTL = document.dir === "rtl" || document.documentElement.dir === "rtl";

  // Build plugins array
  const plugins = [];

  if (options.fade) {
    plugins.push(Fade());
  }

  if (options.autoplay) {
    plugins.push(
      Autoplay({
        delay: options.autoplay,
        stopOnMouseEnter: true,
        stopOnInteraction: false
      })
    );
  }

  if (options.autoScroll) {
    plugins.push(
      AutoScroll({
        speed: options.autoScroll,
        stopOnInteraction: false
      })
    );
  }

  // Embla options
  const emblaOptions = {
    direction: isRTL ? "rtl" : "ltr",
    loop: options.loop ?? false,
    align: options.align ?? "start",
    containScroll: options.containScroll ?? "trimSnaps",
    slidesToScroll: options.slidesToScroll ?? 1,
    dragFree: options.dragFree ?? false,
    duration: options.fade ? 25 : 20
  };

  // Initialize Embla
  const embla = EmblaCarousel(viewport, emblaOptions, plugins);

  // Setup navigation buttons
  setupNavigation(containerEl, embla);

  // Setup dots if present
  setupDots(containerEl, embla);

  // Setup progress bar if present
  setupProgress(containerEl, embla);

  // Return public API
  return {
    embla,
    destroy: () => embla.destroy(),
    scrollTo: (index) => embla.scrollTo(index),
    scrollPrev: () => embla.scrollPrev(),
    scrollNext: () => embla.scrollNext(),
    selectedIndex: () => embla.selectedScrollSnap()
  };
}

/**
 * Setup navigation buttons
 */
function setupNavigation(container, embla) {
  const prevBtn =
    container.querySelector("[data-carousel-prev]") ||
    container.querySelector(".embla__prev") ||
    container.querySelector(".product-gallery__prev");

  const nextBtn =
    container.querySelector("[data-carousel-next]") ||
    container.querySelector(".embla__next") ||
    container.querySelector(".product-gallery__next");

  // Also check for mobile buttons
  const prevBtnMobile = container.querySelector(".product-gallery__prev-mobile");
  const nextBtnMobile = container.querySelector(".product-gallery__next-mobile");

  const buttons = [prevBtn, prevBtnMobile].filter(Boolean);
  const nextButtons = [nextBtn, nextBtnMobile].filter(Boolean);

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => embla.scrollPrev());
  });

  nextButtons.forEach((btn) => {
    btn.addEventListener("click", () => embla.scrollNext());
  });

  const updateButtonStates = () => {
    const canScrollPrev = embla.canScrollPrev();
    const canScrollNext = embla.canScrollNext();

    buttons.forEach((btn) => (btn.disabled = !canScrollPrev));
    nextButtons.forEach((btn) => (btn.disabled = !canScrollNext));
  };

  embla.on("init", updateButtonStates);
  embla.on("select", updateButtonStates);
  embla.on("reInit", updateButtonStates);
}

/**
 * Setup dots navigation
 */
function setupDots(container, embla) {
  const dotsContainer = container.querySelector("[data-carousel-dots]") || container.querySelector(".embla__dots");

  if (!dotsContainer) return;

  const createDots = () => {
    dotsContainer.innerHTML = "";
    embla.slideNodes().forEach((_, index) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className =
        "h-1.5 w-3 rounded-full bg-white/50 transition-all data-[active=true]:w-5 data-[active=true]:bg-white/80";
      dot.addEventListener("click", () => embla.scrollTo(index));
      dotsContainer.appendChild(dot);
    });
  };

  const updateActiveDot = () => {
    const selectedIndex = embla.selectedScrollSnap();
    dotsContainer.querySelectorAll("button").forEach((dot, index) => {
      dot.dataset.active = String(index === selectedIndex);
    });
  };

  embla.on("init", () => {
    createDots();
    updateActiveDot();
  });
  embla.on("select", updateActiveDot);
  embla.on("reInit", () => {
    createDots();
    updateActiveDot();
  });
}

/**
 * Setup progress bar
 */
function setupProgress(container, embla) {
  const progressBar =
    container.querySelector("[data-carousel-progress]") ||
    container.querySelector(".embla__progress-bar") ||
    container.querySelector(".product-gallery__progress-bar");

  if (!progressBar) return;

  const updateProgress = () => {
    const progress = Math.max(0, Math.min(1, embla.scrollProgress()));
    progressBar.style.width = `${progress * 100}%`;
  };

  embla.on("init", updateProgress);
  embla.on("scroll", updateProgress);
  embla.on("reInit", updateProgress);
}

/**
 * Sync two carousels (e.g., main gallery + thumbnails)
 *
 * @param {Object} main - Main carousel instance
 * @param {Object} thumbs - Thumbnails carousel instance
 * @param {NodeList|Array} thumbButtons - Thumbnail button elements
 */
export function syncCarousels(main, thumbs, thumbButtons) {
  if (!main || !thumbs) return;

  // Click on thumbnail scrolls main
  thumbButtons.forEach((btn, index) => {
    btn.addEventListener("click", () => main.scrollTo(index));
  });

  // Main carousel changes scroll thumbs
  main.embla.on("select", () => {
    const selectedIndex = main.selectedIndex();
    thumbs.scrollTo(selectedIndex);

    // Update active state
    thumbButtons.forEach((btn, index) => {
      if (index === selectedIndex) {
        btn.classList.add("border-primary");
        btn.classList.remove("border-transparent");
      } else {
        btn.classList.remove("border-primary");
        btn.classList.add("border-transparent");
      }
    });
  });
}

/**
 * Create a conditional carousel that only initializes when content overflows
 * Useful for responsive layouts where carousel may not be needed on large screens
 *
 * @param {HTMLElement|string} container - Container element
 * @param {Object} options - Same as createCarousel options
 * @param {HTMLElement} controlsElement - Element to show/hide based on carousel state
 * @returns {Object} Controller with init/destroy methods
 */
export function createConditionalCarousel(container, options = {}, controlsElement = null) {
  const containerEl = typeof container === "string" ? document.querySelector(container) : container;

  if (!containerEl) return null;

  const viewport =
    containerEl.querySelector("[data-carousel-viewport]") ||
    containerEl.querySelector(".embla__viewport") ||
    containerEl;

  const slides = viewport.querySelector(".embla__container, [data-carousel-container]");

  let instance = null;

  function needsCarousel() {
    if (!slides) return false;
    return slides.scrollWidth > viewport.clientWidth;
  }

  function init() {
    if (instance) return;
    if (!needsCarousel()) return;

    instance = createCarousel(containerEl, { ...options, forceInit: true });

    if (controlsElement && instance) {
      controlsElement.classList.remove("hidden");
      controlsElement.classList.add("flex");
    }
  }

  function destroy() {
    if (!instance) return;
    instance.destroy();
    instance = null;

    if (controlsElement) {
      controlsElement.classList.add("hidden");
      controlsElement.classList.remove("flex");
    }
  }

  function check() {
    if (needsCarousel()) {
      init();
    } else {
      destroy();
    }
  }

  // Initial check
  check();

  // Re-check on resize
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(check, 150);
  });

  return {
    init,
    destroy,
    check,
    get instance() {
      return instance;
    }
  };
}
