initPriceSliders = function () {
  if (typeof noUiSlider === "undefined") return;

  const sliders = document.querySelectorAll("[data-price-slider]");

  sliders.forEach((slider) => {
    // Skip if already initialized
    if (slider.noUiSlider) return;

    const minInputId = slider.dataset.minInput;
    const maxInputId = slider.dataset.maxInput;
    const MIN = Number(slider.dataset.minPrice) || 0;
    const MAX = Number(slider.dataset.maxPrice) || 20000;

    const minInput = document.getElementById(minInputId);
    const maxInput = document.getElementById(maxInputId);

    if (!minInput || !maxInput) return;

    // Get current prices from URL
    const urlParams = new URLSearchParams(window.location.search);
    const fromPrice = urlParams.get("from_price");
    const toPrice = urlParams.get("to_price");

    // Track real values (can exceed slider range)
    let realMinValue = fromPrice ? Number(fromPrice) : null;
    let realMaxValue = toPrice ? Number(toPrice) : null;

    // Slider start values (clamped to slider range)
    const startMin = Math.min(Math.max(realMinValue || MIN, MIN), MAX);
    const startMax = Math.min(Math.max(realMaxValue || MAX, MIN), MAX);

    // Helpers
    function formatNumber(n) {
      if (n === null || n === undefined || n === "") return "";
      return Number(n).toLocaleString("en-US");
    }

    function unformatNumber(str) {
      if (str === "" || str === null || str === undefined) return null;
      return Number(String(str).replace(/,/g, "")) || 0;
    }

    // Check if RTL
    const isRTL = document.documentElement.dir === "rtl" || document.body.dir === "rtl";

    // Create slider
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

    // Set initial input values (can be beyond slider range)
    minInput.value = realMinValue !== null ? formatNumber(realMinValue) : "";
    maxInput.value = realMaxValue !== null ? formatNumber(realMaxValue) : "";

    // Flag to prevent circular updates
    let updatingFromSlider = false;

    // Slider → inputs (only update if value changed from slider interaction)
    slider.noUiSlider.on("slide", (values) => {
      updatingFromSlider = true;
      const [minVal, maxVal] = values.map(Number);

      // Update real values and inputs
      realMinValue = minVal === MIN ? null : minVal;
      realMaxValue = maxVal === MAX ? null : maxVal;

      minInput.value = realMinValue !== null ? formatNumber(realMinValue) : "";
      maxInput.value = realMaxValue !== null ? formatNumber(realMaxValue) : "";

      updatingFromSlider = false;
    });

    // Inputs → slider (clamp to slider range, but keep real value in input)
    function syncFromInputs() {
      if (updatingFromSlider) return;

      realMinValue = unformatNumber(minInput.value);
      realMaxValue = unformatNumber(maxInput.value);

      // Format input values with commas
      if (realMinValue !== null) {
        minInput.value = formatNumber(realMinValue);
      }
      if (realMaxValue !== null) {
        maxInput.value = formatNumber(realMaxValue);
      }

      // Clamp values for slider (slider only goes 0-20k)
      let sliderMin = realMinValue !== null ? Math.min(Math.max(realMinValue, MIN), MAX) : MIN;
      let sliderMax = realMaxValue !== null ? Math.min(Math.max(realMaxValue, MIN), MAX) : MAX;

      // Ensure min <= max for slider
      if (sliderMin > sliderMax) {
        sliderMin = sliderMax;
      }

      slider.noUiSlider.set([sliderMin, sliderMax]);
    }

    // Handle input on blur and change
    minInput.addEventListener("change", syncFromInputs);
    maxInput.addEventListener("change", syncFromInputs);

    // Allow only numeric input
    function handleNumericInput(e) {
      const value = e.target.value.replace(/[^0-9]/g, "");
      if (value !== e.target.value.replace(/,/g, "")) {
        e.target.value = value;
      }
    }

    minInput.addEventListener("input", handleNumericInput);
    maxInput.addEventListener("input", handleNumericInput);
  });
};

// Initialize sliders on DOMContentLoaded
document.addEventListener("DOMContentLoaded", initPriceSliders);
