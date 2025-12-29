/**
 * Price Slider Module
 *
 * Initializes noUiSlider for price range filtering.
 * Requires noUiSlider CDN to be loaded.
 */

function initPriceSliders() {
  if (typeof noUiSlider === "undefined") return;

  const sliders = document.querySelectorAll("[data-price-slider]");

  sliders.forEach((slider) => {
    if (slider.noUiSlider) return;

    const minInputId = slider.dataset.minInput;
    const maxInputId = slider.dataset.maxInput;
    const MIN = Number(slider.dataset.minPrice) || 0;
    const MAX = Number(slider.dataset.maxPrice) || 20000;

    const minInput = document.getElementById(minInputId);
    const maxInput = document.getElementById(maxInputId);

    if (!minInput || !maxInput) return;

    const urlParams = new URLSearchParams(window.location.search);
    const fromPrice = urlParams.get("from_price");
    const toPrice = urlParams.get("to_price");

    let realMinValue = fromPrice ? Number(fromPrice) : null;
    let realMaxValue = toPrice ? Number(toPrice) : null;

    const startMin = Math.min(Math.max(realMinValue || MIN, MIN), MAX);
    const startMax = Math.min(Math.max(realMaxValue || MAX, MIN), MAX);

    function formatNumber(n) {
      if (n === null || n === undefined || n === "") return "";
      return Number(n).toLocaleString("en-US");
    }

    function unformatNumber(str) {
      if (str === "" || str === null || str === undefined) return null;
      return Number(String(str).replace(/,/g, "")) || 0;
    }

    const isRTL = document.documentElement.dir === "rtl" || document.body.dir === "rtl";

    noUiSlider.create(slider, {
      start: [startMin, startMax],
      range: { min: MIN, max: MAX },
      connect: true,
      direction: isRTL ? "rtl" : "ltr",
      tooltips: false,
      format: {
        to: (value) => Math.round(value),
        from: (value) => Number(value)
      }
    });

    minInput.value = realMinValue !== null ? formatNumber(realMinValue) : "";
    maxInput.value = realMaxValue !== null ? formatNumber(realMaxValue) : "";

    let updatingFromSlider = false;

    slider.noUiSlider.on("slide", (values) => {
      updatingFromSlider = true;
      const [minVal, maxVal] = values.map(Number);

      realMinValue = minVal === MIN ? null : minVal;
      realMaxValue = maxVal === MAX ? null : maxVal;

      minInput.value = realMinValue !== null ? formatNumber(realMinValue) : "";
      maxInput.value = realMaxValue !== null ? formatNumber(realMaxValue) : "";

      updatingFromSlider = false;
    });

    function syncFromInputs() {
      if (updatingFromSlider) return;

      realMinValue = unformatNumber(minInput.value);
      realMaxValue = unformatNumber(maxInput.value);

      if (realMinValue !== null) {
        minInput.value = formatNumber(realMinValue);
      }
      if (realMaxValue !== null) {
        maxInput.value = formatNumber(realMaxValue);
      }

      let sliderMin = realMinValue !== null ? Math.min(Math.max(realMinValue, MIN), MAX) : MIN;
      let sliderMax = realMaxValue !== null ? Math.min(Math.max(realMaxValue, MIN), MAX) : MAX;

      if (sliderMin > sliderMax) {
        sliderMin = sliderMax;
      }

      slider.noUiSlider.set([sliderMin, sliderMax]);
    }

    minInput.addEventListener("change", syncFromInputs);
    maxInput.addEventListener("change", syncFromInputs);

    function handleNumericInput(e) {
      const value = e.target.value.replace(/[^0-9]/g, "");
      if (value !== e.target.value.replace(/,/g, "")) {
        e.target.value = value;
      }
    }

    minInput.addEventListener("input", handleNumericInput);
    maxInput.addEventListener("input", handleNumericInput);
  });
}

// Expose globally for product filter
window.initPriceSliders = initPriceSliders;

// ─────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────

export function init() {
  initPriceSliders();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

export { initPriceSliders };
