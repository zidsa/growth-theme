/**
 * Cart Gift Card Module
 *
 * Handles gift card operations: open dialog, edit, delete, and display updates.
 */

/**
 * Handle login action for unauthenticated users
 * Uses the global handleLoginAction if available, otherwise opens auth dialog
 */
function handleLoginAction() {
  if (window.customerAuthState && window.customerAuthState.isAuthenticated) {
    return;
  }

  // Use global handleLoginAction if available (handles post-login redirect)
  if (typeof window.handleLoginAction === "function") {
    window.handleLoginAction("", false);
    return;
  }

  // Fallback: Use auth_dialog directly
  if (window.auth_dialog?.open && typeof window.auth_dialog.open === "function") {
    window.auth_dialog.open();
  }
}

/**
 * Handle gift card button click
 * Opens gift dialog if authenticated, otherwise prompts login
 */
export function handleGiftCardClick() {
  // Check if user is authenticated
  if (!window.customerAuthState || !window.customerAuthState.isAuthenticated) {
    handleLoginAction("", false);
    return;
  }

  // Open gift dialog
  if (window.gift_dialog?.open && typeof window.gift_dialog.open === "function") {
    window.gift_dialog.open();
  }
}

/**
 * Edit existing gift card (opens dialog)
 */
export function editGiftCard() {
  handleGiftCardClick();
}

/**
 * Delete gift card from cart
 */
export function deleteGiftCard() {
  const btn = document.querySelector("[data-gift-delete-btn]");
  const icon = document.querySelector("[data-gift-delete-icon]");
  const spinner = document.querySelector("[data-gift-delete-spinner]");

  // Show loading state
  if (icon) icon.classList.add("hidden");
  if (spinner) spinner.classList.remove("hidden");

  window.zid.cart
    .removeGiftCard({ showErrorNotification: true })
    .then(() => {
      // Hide gift card display in products list
      const giftCardDisplays = document.querySelectorAll("[data-gift-card-display]");
      giftCardDisplays.forEach((el) => {
        el.classList.add("hidden");
      });

      // Toggle Add/Edit details links on gift button
      const addLink = document.querySelector("[data-gift-add-link]");
      const editLink = document.querySelector("[data-gift-edit-link]");
      if (addLink) addLink.classList.remove("hidden");
      if (editLink) editLink.classList.add("hidden");

      // Reset loading state
      if (icon) icon.classList.remove("hidden");
      if (spinner) spinner.classList.add("hidden");
    })
    .catch((err) => {
      console.error("Failed to remove gift card:", err);
      // Reset loading state
      if (icon) icon.classList.remove("hidden");
      if (spinner) spinner.classList.add("hidden");
    });
}

/**
 * Update gift card display with new data
 * @param {Object} giftData - Gift card data from API
 */
export function updateGiftCardDisplay(giftData) {
  if (!giftData) return;

  // Show gift card display in products list
  const giftCardDisplays = document.querySelectorAll("[data-gift-card-display]");
  giftCardDisplays.forEach((el) => {
    el.classList.remove("hidden");
  });

  // Toggle Add/Edit details links on gift button
  const addLink = document.querySelector("[data-gift-add-link]");
  const editLink = document.querySelector("[data-gift-edit-link]");
  if (addLink) addLink.classList.add("hidden");
  if (editLink) editLink.classList.remove("hidden");

  // Update sender/receiver
  const senders = document.querySelectorAll("[data-gift-sender]");
  const receivers = document.querySelectorAll("[data-gift-receiver]");
  senders.forEach((el) => {
    el.textContent = giftData.sender_name || "";
  });
  receivers.forEach((el) => {
    el.textContent = giftData.receiver_name || "";
  });

  // Update gift message
  const messageEls = document.querySelectorAll("[data-gift-message]");
  messageEls.forEach((el) => {
    if (giftData.gift_message) {
      el.textContent = giftData.gift_message;
      el.classList.remove("hidden");
    } else {
      el.classList.add("hidden");
    }
  });

  // Update media link
  const mediaLinkEls = document.querySelectorAll("[data-gift-media-link]");
  mediaLinkEls.forEach((el) => {
    if (giftData.media_link) {
      el.textContent = giftData.media_link;
      el.classList.remove("hidden");
    } else {
      el.classList.add("hidden");
    }
  });

  // Update card design image
  const giftIcons = document.querySelectorAll("[data-gift-icon]");
  const giftImages = document.querySelectorAll("[data-gift-image]");
  if (giftData.card_design) {
    giftIcons.forEach((el) => {
      el.classList.add("hidden");
    });
    giftImages.forEach((el) => {
      el.src = giftData.card_design;
      el.classList.remove("hidden");
    });
  } else {
    giftIcons.forEach((el) => {
      el.classList.remove("hidden");
    });
    giftImages.forEach((el) => {
      el.classList.add("hidden");
    });
  }
}

/**
 * Setup gift card event listener
 * Listens for vitrin:gift:submitted event from platform
 */
export function setupGiftEventListener() {
  window.addEventListener("vitrin:gift:submitted", (event) => {
    const giftData = event?.detail?.data?.gift_card_details;
    if (giftData) {
      updateGiftCardDisplay(giftData);
    }
  });
}
