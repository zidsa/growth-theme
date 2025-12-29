/**
 * Event Utilities
 */

/**
 * Dispatch a custom event
 * @param {string} name - Event name (e.g., 'cart:added')
 * @param {Object} detail - Event data
 * @param {EventTarget} target - Target element (default: window)
 */
export function dispatch(name, detail = {}, target = window) {
  target.dispatchEvent(
    new CustomEvent(name, {
      detail,
      bubbles: true
    })
  );
}

/**
 * Add event listener with cleanup function
 * @param {EventTarget} target - Element to listen on
 * @param {string} event - Event name
 * @param {Function} handler - Event handler
 * @param {Object} options - Event options
 * @returns {Function} Cleanup function to remove listener
 */
export function on(target, event, handler, options) {
  target.addEventListener(event, handler, options);
  return () => target.removeEventListener(event, handler, options);
}
