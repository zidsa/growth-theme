/**
 * Product Gallery Module
 *
 * Handles product image/video gallery with:
 * - Embla carousel for main gallery and thumbnails
 * - Video playback support (YouTube, etc.)
 * - Thumbnail sync
 * - Progress bar
 */

import { createCarousel, syncCarousels } from "../lib/carousel.js";

// Store initialized galleries
const galleries = new Map();

/**
 * Convert YouTube URL to embeddable iframe URL
 */
function getYouTubeEmbedUrl(videoUrl) {
  if (!videoUrl || typeof videoUrl !== "string") return null;

  const videoIdMatch = videoUrl.match(
    /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^/\n\s]+\/\S+\/|(?:v|e(?:mbed)?|.*[?&]v=)|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/
  );

  if (videoIdMatch && videoIdMatch[1]) {
    return `https://www.youtube.com/embed/${videoIdMatch[1]}?autoplay=1&enablejsapi=1`;
  }

  return null;
}

/**
 * Show video in iframe
 */
function showVideo(playButton) {
  const slide = playButton.closest(".product-gallery__slide");
  if (!slide) return;

  const videoContainer = slide.querySelector("[data-video-container]");
  const iframe = videoContainer?.querySelector("iframe");
  const videoSrc = playButton.getAttribute("data-video-src");

  if (!videoContainer || !iframe || !videoSrc) return;

  const embedUrl = getYouTubeEmbedUrl(videoSrc);
  iframe.src = embedUrl || videoSrc;

  videoContainer.classList.remove("hidden");
  playButton.classList.add("hidden");
}

/**
 * Hide video and stop playback
 */
function hideVideo(closeButton) {
  const videoContainer = closeButton.closest("[data-video-container]");
  const slide = closeButton.closest(".product-gallery__slide");

  if (!videoContainer || !slide) return;

  const iframe = videoContainer.querySelector("iframe");
  const playButton = slide.querySelector("[data-video-play]");

  if (iframe) iframe.src = "";

  videoContainer.classList.add("hidden");
  if (playButton) playButton.classList.remove("hidden");
}

/**
 * Stop all videos in a gallery
 */
function stopAllVideos(galleryNode) {
  galleryNode.querySelectorAll("[data-video-container]").forEach((container) => {
    const iframe = container.querySelector("iframe");
    const slide = container.closest(".product-gallery__slide");
    const playButton = slide?.querySelector("[data-video-play]");

    if (iframe) iframe.src = "";
    container.classList.add("hidden");
    if (playButton) playButton.classList.remove("hidden");
  });
}

/**
 * Auto-play video on the current slide if it's a video
 */
function autoPlayCurrentVideo(galleryNode, emblaApi) {
  if (!emblaApi) return;

  const selectedIndex = emblaApi.selectedScrollSnap();
  const slides = galleryNode.querySelectorAll(".product-gallery__slide");
  const currentSlide = slides[selectedIndex];

  if (!currentSlide) return;

  const playButton = currentSlide.querySelector("[data-video-play]");
  if (playButton) {
    showVideo(playButton);
  }
}

/**
 * Initialize video controls for a gallery
 */
function initVideoControls(galleryNode, emblaApi) {
  // Handle play/close button clicks via event delegation
  galleryNode.addEventListener("click", (event) => {
    const playButton = event.target.closest("[data-video-play]");
    if (playButton) {
      event.preventDefault();
      event.stopPropagation();
      showVideo(playButton);
      return;
    }

    const closeButton = event.target.closest("[data-video-close]");
    if (closeButton) {
      event.preventDefault();
      event.stopPropagation();
      hideVideo(closeButton);
    }
  });

  // Handle slide changes - stop current video and autoplay new video if applicable
  if (emblaApi) {
    emblaApi.on("select", () => {
      stopAllVideos(galleryNode);
      // Auto-play video after a brief delay to ensure slide is visible
      setTimeout(() => autoPlayCurrentVideo(galleryNode, emblaApi), 300);
    });
  }
}

/**
 * Initialize a product gallery by ID
 */
export function initProductGallery(galleryId) {
  // Destroy existing instance
  destroyProductGallery(galleryId);

  // Find gallery elements
  const galleryNode = document.querySelector(`.product-gallery[data-gallery-id="${galleryId}"]`);
  const thumbsNode = document.querySelector(`.product-gallery-thumbs[data-gallery-id="${galleryId}"]`);

  if (!galleryNode) return null;

  // Check for slides
  const slides = galleryNode.querySelectorAll(".product-gallery__slide");

  // For single slide, just initialize video controls and return
  if (slides.length <= 1) {
    initVideoControls(galleryNode, null);
    return null;
  }

  // Create main gallery carousel
  const mainCarousel = createCarousel(galleryNode, {
    loop: false,
    align: "start",
    containScroll: "trimSnaps",
    forceInit: true
  });

  if (!mainCarousel) return null;

  // Create thumbnails carousel if present
  let thumbsCarousel = null;
  if (thumbsNode) {
    thumbsCarousel = createCarousel(thumbsNode, {
      dragFree: true,
      containScroll: "keepSnaps",
      forceInit: true
    });
  }

  // Get all navigation elements
  const prevBtn = document.querySelector(`.product-gallery__prev[data-gallery-id="${galleryId}"]`);
  const nextBtn = document.querySelector(`.product-gallery__next[data-gallery-id="${galleryId}"]`);
  const prevBtnMobile = document.querySelector(`.product-gallery__prev-mobile[data-gallery-id="${galleryId}"]`);
  const nextBtnMobile = document.querySelector(`.product-gallery__next-mobile[data-gallery-id="${galleryId}"]`);
  const thumbButtons = document.querySelectorAll(`.product-gallery-thumbs__slide[data-gallery-id="${galleryId}"]`);
  const progressBar = document.querySelector(`.product-gallery__progress-bar[data-gallery-id="${galleryId}"]`);

  // Navigation click handlers
  const prevClick = () => mainCarousel.scrollPrev();
  const nextClick = () => mainCarousel.scrollNext();

  if (prevBtn) prevBtn.addEventListener("click", prevClick);
  if (nextBtn) nextBtn.addEventListener("click", nextClick);
  if (prevBtnMobile) prevBtnMobile.addEventListener("click", prevClick);
  if (nextBtnMobile) nextBtnMobile.addEventListener("click", nextClick);

  // Thumbnail click handlers
  const thumbClickHandlers = [];
  thumbButtons.forEach((btn, index) => {
    const handler = () => mainCarousel.scrollTo(index);
    thumbClickHandlers.push(handler);
    btn.addEventListener("click", handler);
  });

  // Update progress bar
  const updateProgress = () => {
    if (progressBar) {
      const progress = Math.max(0, Math.min(1, mainCarousel.embla.scrollProgress()));
      progressBar.style.width = `${progress * 100}%`;
    }

    // Update button states
    const canPrev = mainCarousel.embla.canScrollPrev();
    const canNext = mainCarousel.embla.canScrollNext();

    if (prevBtn) prevBtn.disabled = !canPrev;
    if (nextBtn) nextBtn.disabled = !canNext;
    if (prevBtnMobile) prevBtnMobile.disabled = !canPrev;
    if (nextBtnMobile) nextBtnMobile.disabled = !canNext;
  };

  // Update active thumbnail
  const updateActiveThumb = () => {
    const selectedIndex = mainCarousel.embla.selectedScrollSnap();

    thumbButtons.forEach((btn, index) => {
      if (index === selectedIndex) {
        btn.classList.add("border-primary");
        btn.classList.remove("border-transparent");
      } else {
        btn.classList.remove("border-primary");
        btn.classList.add("border-transparent");
      }
    });

    // Scroll thumbnail carousel to active
    if (thumbsCarousel) {
      thumbsCarousel.scrollTo(selectedIndex);
    }
  };

  // Bind events
  mainCarousel.embla.on("init", updateProgress);
  mainCarousel.embla.on("scroll", updateProgress);
  mainCarousel.embla.on("reInit", updateProgress);
  mainCarousel.embla.on("select", updateActiveThumb);

  // Initial state
  updateProgress();
  updateActiveThumb();

  // Initialize video controls
  initVideoControls(galleryNode, mainCarousel.embla);

  // Store instance for cleanup
  galleries.set(galleryId, {
    mainCarousel,
    thumbsCarousel,
    handlers: { prevClick, nextClick, thumbClickHandlers },
    elements: { prevBtn, nextBtn, prevBtnMobile, nextBtnMobile, thumbButtons }
  });

  return { mainCarousel, thumbsCarousel };
}

/**
 * Destroy a product gallery instance
 */
export function destroyProductGallery(galleryId) {
  const instance = galleries.get(galleryId);
  if (!instance) return;

  const { mainCarousel, thumbsCarousel, handlers, elements } = instance;

  // Remove event listeners
  if (elements.prevBtn) elements.prevBtn.removeEventListener("click", handlers.prevClick);
  if (elements.nextBtn) elements.nextBtn.removeEventListener("click", handlers.nextClick);
  if (elements.prevBtnMobile) elements.prevBtnMobile.removeEventListener("click", handlers.prevClick);
  if (elements.nextBtnMobile) elements.nextBtnMobile.removeEventListener("click", handlers.nextClick);

  elements.thumbButtons.forEach((btn, index) => {
    btn.removeEventListener("click", handlers.thumbClickHandlers[index]);
  });

  // Destroy carousels
  if (mainCarousel) mainCarousel.destroy();
  if (thumbsCarousel) thumbsCarousel.destroy();

  galleries.delete(galleryId);
}

/**
 * Initialize all product galleries on the page
 */
export function initAllProductGalleries() {
  document.querySelectorAll(".product-gallery[data-gallery-id]").forEach((gallery) => {
    const galleryId = gallery.getAttribute("data-gallery-id");
    if (galleryId) {
      initProductGallery(galleryId);
    }
  });
}

// Expose to window for variants.js to call after rebuilding gallery DOM
window.initProductGallery = initProductGallery;
window.destroyProductGallery = destroyProductGallery;
