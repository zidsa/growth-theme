# Default Theme for Vitrin

The default storefront theme for [Zid's Vitrin platform](https://zid.sa). Built with TailwindCSS v4, Vite 7, and Jinja2 templates.

**TailwindCSS v4** | **Vite 7** | **Jinja2** | **RTL-first (Arabic)**

---

## Table of Contents

- [Quick Start](#quick-start)
- [Build and Deploy](#build-and-deploy)
- [Project Structure](#project-structure)
- [Template System](#template-system)
- [CSS Architecture](#css-architecture)
- [JavaScript Architecture](#javascript-architecture)
- [Event System](#event-system)
- [Cart System](#cart-system)
- [Product System](#product-system)
- [Platform Integration](#platform-integration)
- [Window Globals and Platform Callbacks](#window-globals-and-platform-callbacks)
- [Component Patterns](#component-patterns)
- [Localization and RTL](#localization-and-rtl)
- [External Dependencies](#external-dependencies)
- [Secrets and Configuration](#secrets-and-configuration)
- [Non-Obvious Behaviors](#non-obvious-behaviors)
- [Resources](#resources)

---

## Quick Start

```bash
npm install
npm run dev                    # Watch mode (CSS + JS)
vitrin push -s <store-email> -a   # Push and activate theme
```

## Build and Deploy

### Commands

| Command          | Description                                                                  |
| ---------------- | ---------------------------------------------------------------------------- |
| `npm run dev`    | Parallel CSS watch + JS watch (via `npm-run-all`)                            |
| `npm run build`  | Production build: minified CSS + both JS bundles (sequential)                |
| `npm run format` | Prettier with Jinja + Tailwind plugins                                       |

### Build Pipeline

The build has **two separate pipelines** that run sequentially:

**1. CSS** (`@tailwindcss/cli`):
```
assets/tailwindcss.css  →  @tailwindcss/cli  →  assets/styles.css
```

**2. JavaScript** (Vite, two bundles):
```
ENTRY=main vite build  →  assets/dist/theme.js        (global: VitrinTheme)
ENTRY=cart vite build  →  assets/dist/cart-controller.js (global: CartController)
```

The `ENTRY` environment variable controls which bundle Vite builds. The main bundle empties `dist/` first (`emptyOutDir: entry === "main"`), so order matters -- main must build before cart.

In development mode (`npm run build:dev`), sourcemaps are enabled and minification is disabled.

### Deployment via Vitrin CLI

```bash
npm install -g @zidsa/vitrin-cli
vitrin login                        # One-time auth (stored globally by CLI)
vitrin push -s <store-email> -a     # Push and activate theme
vitrin preview -s <store-id>        # Preview in browser
```

The `vitrin push` command pushes the entire theme directory. The `-a` flag activates the theme immediately after pushing. There are no `.env` files, API keys, or secrets in this repo -- all authentication is handled by the Vitrin CLI's global login session.

### Build Artifacts

- `assets/styles.css` -- compiled CSS output (**do not edit**, gitignored)
- `assets/dist/theme.js` -- main JS bundle (gitignored)
- `assets/dist/cart-controller.js` -- cart page JS bundle (gitignored)

Always run `npm run build` before `vitrin push`.

---

## Project Structure

```
├── layout.jinja                  # Base HTML wrapper (all templates extend this)
├── layout.schema.json            # Global theme settings (colors, fonts, radius)
├── header.jinja / footer.jinja   # Header and footer partials
├── templates/                    # Page templates (12 pages)
├── sections/                     # Homepage blocks with .schema.json settings
├── components/
│   ├── ui/                       # Base UI (breadcrumb, disclosure, quantity-input, phone-input)
│   ├── products/                 # Product components (card, gallery, variants, reviews)
│   │   ├── filters/              # Product filter components
│   │   └── headless/             # Unstyled product components (options, fields, filters)
│   ├── cart/                     # Cart page components (coupon, gift, loyalty, summary)
│   ├── categories/               # Category page components
│   ├── header/                   # Header sub-components (logo, nav, search, drawer)
│   ├── shipping-payment/         # Shipping and payment components
│   └── shared/                   # Shared components (metafields)
├── assets/
│   ├── tailwindcss.css           # Main CSS source (theme config + imports)
│   ├── styles.css                # Compiled output (do not edit)
│   ├── css/                      # Extracted component stylesheets
│   │   ├── components.css        # @layer components (buttons, forms, badges)
│   │   ├── product-options.css   # Headless variant selector styles
│   │   ├── custom-fields.css     # Headless custom input field styles
│   │   ├── product-filters.css   # Headless product filter styles
│   │   ├── price-slider.css      # noUiSlider overrides
│   │   └── lightbox.css          # PhotoSwipe overrides
│   ├── js/                       # JavaScript source modules
│   │   ├── main.js               # Theme entry point (imports all modules)
│   │   ├── cart/                  # Cart modules (controller, add-to-cart, coupon, etc.)
│   │   ├── product/              # Product features (variants, gallery, lightbox, sticky-bar, quick-view)
│   │   ├── features/             # Self-initializing modules (wishlist, search, filters, etc.)
│   │   ├── lib/                  # Utilities (carousel wrapper)
│   │   ├── utils/                # Shared helpers (events, loading)
│   │   └── data/                 # Static data (countries list)
│   └── dist/                     # Vite build output (theme.js, cart-controller.js)
├── locale/ar/LC_MESSAGES/        # Arabic translations (messages.po)
└── docs/                         # Component and architecture documentation
```

### Templates

12 page templates in `templates/`:

`home` · `product` · `products` · `cart` · `category` · `categories` · `page` · `faqs` · `reviews` · `questions` · `shipping_payment` · `404_not_found`

### Sections

11 homepage sections in `sections/`, each a `.jinja` + `.schema.json` pair:

`hero` · `carousel` · `products` · `categories` · `gallery` · `video` · `benefits` · `partners` · `testimonials` · `logo-social` · `countdown`

---

## Template System

### Inheritance

Every template extends `layout.jinja`:

```jinja
{% extends "layout.jinja" %}
{% block content %}
  <!-- Page content -->
{% endblock %}
```

Page-specific scripts use the `footer_scripts` block:

```jinja
{% block footer_scripts %}
  <script src="{{ 'assets/dist/cart-controller.js' | asset_url }}"></script>
  <script>
    window.CartPage.init({ /* config */ });
  </script>
{% endblock %}
```

### Required Platform Tags

Every page **must** include these Vitrin tags in `layout.jinja`:

```html
<head>
  {% vitrin_head %}
</head>
<body>
  ...
  {% vitrin_body %}
</body>
```

`{% vitrin_head %}` injects platform CSS, analytics, and meta tags. `{% vitrin_body %}` injects platform scripts (auth dialogs, Zid SDK, tracking). The loyalty rewards script (`layout-loyalty.js`) must be loaded **after** `{% vitrin_body %}` because it depends on platform globals that `vitrin_body` injects.

### Sections and Schema

Each homepage section is a pair:

```
sections/
├── hero.jinja           # Template with {{ section.settings.title }}
└── hero.schema.json     # Defines editable fields for merchants
```

The schema defines groups, fields, and defaults that merchants configure through the visual Theme Editor. Settings are accessed via `section.settings.<field_name>`.

### Template Data Flow

Templates receive data from the platform as context variables. Key variables available per page:

| Template | Key Context Variables |
|----------|----------------------|
| `product` | `product`, `product.attributes`, `product.images`, `product.variants` |
| `products` | `products` (paginated list), `filters`, `sort_options` |
| `cart` | `cart`, `cart.products`, `cart.totals`, `cart.coupon` |
| `category` | `category`, `category.products` |
| `page` | `page.title`, `page.content` (HTML) |

Global variables (available in all templates via `layout.jinja`):

- `settings.*` -- merchant theme settings from `layout.schema.json`
- `store` -- store info (name, logo, currency, etc.)
- `session` -- current session info
- `request` -- HTTP request context

---

## CSS Architecture

### Overview

**TailwindCSS v4** with `@theme inline` -- no `tailwind.config.js` needed.

`assets/tailwindcss.css` is the main source file. It contains:
- `@theme inline` block (maps CSS variables to Tailwind tokens)
- `:root` variables (layout, fixed colors, typography)
- Prose typography utility
- Base styles (body, container)
- Announcement marquee animation
- Platform widget overrides

It imports component stylesheets from `assets/css/`:

| File | Content |
|------|---------|
| `css/components.css` | `@layer components`: buttons, forms, badges, qty-input, button-groups |
| `css/product-options.css` | Headless variant selector styles (`.product-options__*`) |
| `css/custom-fields.css` | Headless custom input field styles (`.custom-field__*`, `.file-upload__*`) |
| `css/product-filters.css` | Headless product filter styles (`.product-filter__*`, `.filters--sidebar`) |
| `css/price-slider.css` | noUiSlider theme overrides |
| `css/lightbox.css` | PhotoSwipe theme overrides |

### CSS Variables Flow

This is the core theming mechanism. Merchant settings flow through three layers:

```
layout.schema.json (merchant picks colors/fonts in Theme Editor)
  → layout.jinja <style> block (sets CSS custom properties on :root)
    → @theme inline in tailwindcss.css (maps to Tailwind tokens)
      → Tailwind utility classes (bg-primary, text-foreground, etc.)
```

**Step 1:** `layout.jinja` reads merchant settings and sets CSS variables:

```html
<style>
  :root {
    --background: {{ settings.background_color }};
    --foreground: {{ settings.foreground_color }};
    --primary: {{ settings.primary_color }};
    --primary-foreground: {{ settings.primary_foreground_color }};
    --secondary: {{ settings.secondary_color }};
    --muted: {{ settings.muted_color }};
    --accent: {{ settings.accent_color }};
    --border: {{ settings.border_color }};
    --input: {{ settings.input_color }};
    --ring: {{ settings.ring_color }};
    --radius: {{ settings.border_radius }}px;
    --font-family: {{ settings.font_family }};
  }
</style>
```

**Step 2:** `tailwindcss.css` maps these to Tailwind:

```css
@theme inline {
  --color-background: var(--background);
  --color-primary: var(--primary);
  --radius-sm: calc(var(--radius) * 0.5);
  /* ... */
}
```

**Step 3:** Templates use Tailwind classes: `bg-primary`, `text-foreground`, `rounded-lg`, etc.

### Fixed System Colors

These are NOT merchant-configurable. They're set in `:root` in `tailwindcss.css`:

| Token | Hex | Usage |
|-------|-----|-------|
| `--destructive` | `#C22B51` | Error states |
| `--success` | `#649560` | Success states |
| `--warning` | `#FFB400` | Warning states |

### Typography Variables

Typography is defined as CSS custom properties consumed by component classes in `css/components.css`:

| Variable Prefix | Size | Weight | Used by |
|----------------|------|--------|---------|
| `--font-body1--` | 16px | 400 | `.btn-lg`, `.form-input` |
| `--font-subtitle2--` | 14px | 600 | SemiBold small titles |
| `--font-body2--` | 14px | 400 | `.btn-md`, `.qty-input` |
| `--font-caption--` | 12px | 400 | `.btn-sm`, `.form-caption` |
| `--font-tagline--` | 16px | 400 | `.form-label`, `.badge` |

Each has `--size`, `--line-height`, and `--weight` suffixes.

### Headless Components CSS

The `css/product-options.css`, `css/custom-fields.css`, and `css/product-filters.css` files provide styles for the unstyled "headless" components in `components/products/headless/`. They use BEM naming (`.product-options__group`, `.custom-field__input`, `.product-filter__checkbox`). These are independent of Tailwind and can be completely restyled.

---

## JavaScript Architecture

### Bundle Structure

Vite builds **two IIFE bundles** (not ES modules) for direct `<script>` tag inclusion:

| Bundle | Entry Point | Global Variable | Loaded On |
|--------|-------------|-----------------|-----------|
| `theme.js` | `assets/js/main.js` | `VitrinTheme` | Every page (in `layout.jinja`) |
| `cart-controller.js` | `assets/js/cart/controller.js` | `CartController` | Cart page only (in `templates/cart.jinja`) |

### Module Organization

```
assets/js/
├── main.js                    # Entry point: imports everything, inits on DOMContentLoaded
│
├── cart/                      # Cart system (split between both bundles)
│   ├── controller.js          # Cart PAGE controller (separate bundle)
│   ├── add-to-cart.js         # Add-to-cart buttons (theme.js bundle)
│   ├── badge.js               # Header cart count badge
│   ├── coupon.js              # Coupon code apply/remove
│   ├── gift.js                # Gift card operations
│   ├── loyalty.js             # Loyalty points redemption
│   ├── quantity.js            # Cart page quantity update/remove
│   ├── refresh.js             # AJAX cart page refresh
│   └── totals.js              # Cart totals rendering + payment widgets
│
├── product/                   # Product page features
│   ├── variants.js            # Variant selection and SKU switching
│   ├── gallery.js             # Product image carousel (Embla)
│   ├── lightbox.js            # Full-screen image viewer (PhotoSwipe)
│   ├── quick-view.js          # Quick view modal with LRU cache
│   └── sticky-bar.js          # Sticky add-to-cart bar on scroll
│
├── features/                  # Self-initializing feature modules
│   ├── layout.js              # Auth visibility, locale nav, announcement bar
│   ├── wishlist.js            # Wishlist toggle (heart button)
│   ├── search.js              # Search drawer/overlay
│   ├── product-filter.js      # AJAX product filtering with History API
│   ├── price-slider.js        # noUiSlider initialization
│   ├── qty-input.js           # Quantity +/- input component
│   ├── phone-input.js         # Phone number input with country selector
│   ├── notify-me.js           # Back-in-stock notification form
│   ├── bundle-offers.js       # Bundle offer badges on product cards
│   └── loyalty-rewards.js     # Floating loyalty rewards button
│
├── lib/
│   └── carousel.js            # Embla Carousel wrapper (createCarousel helper)
│
├── utils/
│   ├── events.js              # Custom event dispatch/listen helpers
│   └── loading.js             # Spinner show/hide utilities (WeakMap-backed)
│
├── data/
│   └── countries.js           # Country data with dial codes + phone validation
│
├── time-ago.js                # Relative time display ("2 days ago")
├── question-form.js           # Product question form handler
├── shipping-payment.js        # Shipping page cities dialog + copy buttons
└── layout-loyalty.js          # Standalone loyalty popup (loaded AFTER vitrin_body)
```

### Module Patterns

**Self-initializing modules** (in `features/`): Each module auto-initializes on DOMContentLoaded and re-initializes on dynamic content events. Pattern:

```js
// Track initialized elements with WeakSet (prevents double-init)
const initialized = new WeakSet();

function initModule() {
  document.querySelectorAll("[data-my-component]").forEach((el) => {
    if (initialized.has(el)) return;
    initialized.add(el);
    // Setup...
  });
}

export function init() {
  initModule();
  window.addEventListener("content:loaded", initModule);
  window.addEventListener("products-updated", initModule);
}

// Self-initialize
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
```

Key patterns used throughout:
- **WeakSet/WeakMap** for element tracking (prevents double-initialization, auto-cleans on DOM removal)
- **Data attributes** for component binding (`data-qty-input`, `data-cart-badge`, `data-phone-input`, etc.)
- **Event delegation** where appropriate (cart controller uses `[data-action]` clicks)
- **Exponential backoff** for SDK availability (`waitForZid()` in add-to-cart.js)

---

## Event System

The theme uses custom DOM events for communication between modules. This is critical for AJAX content updates -- when new HTML is injected, modules must re-initialize on the new elements.

### Theme Events (dispatched by theme code)

| Event | Dispatched By | Listened By | Purpose |
|-------|---------------|-------------|---------|
| `content:loaded` | Quick view, AJAX content | Carousels, galleries, wishlist, qty-inputs, phone-input, notify-me | Re-initialize components after dynamic content injection |
| `products-updated` | Product filter (AJAX) | Cart buttons, qty-inputs, bundle offers, wishlist | Re-initialize after product listing update |
| `cart:updated` | Cart refresh module | Loyalty module | Cart data changed |
| `product:variant-changed` | Variant selector | Notify-me form | Update product ID when variant changes |
| `qty:change` | Quantity input | Cart quantity module | Quantity value changed (bubbles) |
| `qty:remove` | Quantity input | Cart quantity module | Delete button clicked (bubbles) |
| `phone:change` | Phone input | Notify-me form | Phone number value changed |
| `phone:country-change` | Phone input | (External listeners) | Country/dial code changed |
| `toast:show` | Notify-me fallback | (External toast handler) | Show toast notification |

### Platform Events (dispatched by Vitrin/Zid SDK)

| Event | Source | Handled By | Purpose |
|-------|--------|------------|---------|
| `vitrin:auth:success` | Platform auth dialog | Layout module, cart controller | User completed login (OTP verified) |
| `vitrin:gift:submitted` | Platform gift dialog | Gift card module | Gift card form submitted |
| `vitrin:bundle-selections:updated` | Platform bundle UI | Add-to-cart module | Bundle product selections changed |
| `zidcart:loading` | Platform cart SDK | Cart refresh module | Cart operation started |
| `zidcart:updated` | Platform cart SDK | Cart refresh module | Cart operation completed |
| `zidcart:error` | Platform cart SDK | Cart refresh module | Cart operation failed |
| `zid-customer-fetched` | Platform auth | Layout module, notify-me | Customer data available after login |

### Event Flow Example: AJAX Product Filtering

```
User clicks filter checkbox
  → productFilter.applyFilter({ attributes: [...] })
    → History API pushState (URL updated)
    → fetch() current URL with X-Requested-With: XMLHttpRequest
    → DOMParser extracts #products-content from response
    → innerHTML swap
    → window.dispatchEvent("products-updated")
      → add-to-cart: syncCartState() + re-init buttons
      → qty-input: initAll() on new elements
      → bundle-offers: reload badges
      → wishlist: re-init hearts
```

### Event Flow Example: Add to Cart

```
User clicks "Add to cart" button
  → addToCart(productId, quantity, customFields)
    → waitForZid() (exponential backoff until window.zid ready)
    → zid.cart.addProduct({ product_id, quantity, ... })
    → On success:
      → showQuantityInput(button) — swap button to qty input
      → refreshBadge() — update header cart count
      → If Buy Now: redirect to cart
```

---

## Cart System

The cart has two separate JavaScript entry points:

### 1. Add-to-Cart (`theme.js` bundle)

Runs on **every page**. Handles:
- "Add to cart" buttons on product cards and product pages
- Cart badge count in header
- Cart state sync (showing qty inputs vs add buttons based on what's in cart)
- Buy Now functionality
- Bundle product add-to-cart

Key behaviors:
- **`syncCartState()`**: On page load, fetches current cart and updates all product cards to show either the "Add to cart" button or a quantity input based on what's already in cart
- **ID normalization**: Cart product IDs from the API may differ in format (hyphens, case). The `findCartItem()` function normalizes IDs by stripping hyphens and lowercasing for comparison
- **`waitForZid()`**: The Zid SDK loads asynchronously. `waitForZid()` uses exponential backoff (100ms, 200ms, 400ms...) up to 10 retries to wait for `window.zid` to be available

### 2. Cart Page Controller (`cart-controller.js` bundle)

Runs on the **cart page only**. Orchestrates all cart page features:

```
CartPage.init(config)
  ├── setupEventDelegation()     # [data-action] click handlers
  ├── setupZidCartEventListeners()  # zidcart:* platform events
  ├── setupCouponInput()         # Coupon code apply
  ├── setupGiftEventListener()   # Gift card events
  ├── initLoyaltyProgram()       # Loyalty points
  └── setupAuthSuccessListener() # Post-login redirect
```

**Event delegation**: All cart actions use `data-action` attributes:

```html
<button data-action="apply-coupon">Apply</button>
<button data-action="remove-coupon">Remove</button>
<button data-action="gift-card">Add Gift</button>
<button data-action="edit-gift">Edit</button>
<button data-action="delete-gift">Delete</button>
<button data-action="apply-loyalty">Apply</button>
<button data-action="remove-loyalty">Remove</button>
```

### Cart AJAX Refresh

When cart data changes, the page refreshes via AJAX (no full reload):

```
Cart operation (add/remove/update)
  → zidcart:updated event fires
  → refreshCartPage():
    → fetch(window.location.href) with X-Requested-With header
    → DOMParser extracts sections from response HTML
    → swapElement() replaces: products list, totals, coupon, loyalty, shipping bar, payment widgets
    → Re-init: qty inputs, coupon handlers, cart badge, payment widgets (Tamara/Tabby)
    → Dispatch "cart-updated" event
```

If the cart becomes empty after a removal, it falls back to `window.location.reload()` to show the empty state.

### Payment Widget Updates

After cart total changes, the theme updates BNPL (Buy Now Pay Later) widgets:
- **Tamara**: Updates `tamara-widget` amount attribute and calls `TamaraWidgetV2.refresh()`
- **Tabby**: Reconstructs `TabbyPromo` with new price

---

## Product System

### Variant Selection (`variants.js`)

Handles product variant/option selection on the product page. When a customer selects options (size, color, etc.):

1. Calls `zid.products.getProductOptions(productId, { attributes: true, option_fields: true, input_fields: true })`
2. Matches selected attributes to find the correct variant
3. Dispatches `product:variant-changed` event with variant data
4. Updates: price display, stock status, images, SKU, add-to-cart button state

The platform function `window.productOptionsChanged(product)` is called as a callback. This is a **platform requirement** -- the Vitrin platform expects this function to exist and calls it after variant changes.

### Product Gallery (`gallery.js`)

Uses Embla Carousel for product image galleries:
- Main image carousel with thumbnail navigation
- Thumbnail carousel synced to main
- Responsive: horizontal thumbnails on mobile, vertical on desktop
- Gallery re-initializes on `content:loaded` for quick view support

### Quick View (`quick-view.js`)

Modal that shows product details without navigating to the product page:

- **Hover prefetch**: When hovering over a product card, the quick view content is prefetched via `fetch()` (3-second delay)
- **LRU cache**: Cached responses are stored in a Map. When cache exceeds 20 entries, oldest entries are evicted
- **Content injection**: Response HTML is parsed and injected into a dialog element
- After injection, dispatches `content:loaded` to re-init carousels, galleries, and other components

### Lightbox (`lightbox.js`)

PhotoSwipe integration for full-screen image viewing:
- Initializes on product gallery click events
- Supports dynamic slide data from `data-pswp-*` attributes
- Re-initializes on `content:loaded` for quick view modals

### Sticky Bar (`sticky-bar.js`)

Shows a sticky add-to-cart bar at the bottom when the main add-to-cart button scrolls out of view:
- Uses IntersectionObserver to detect when the add-to-cart section leaves the viewport
- Shows/hides the sticky bar with a slide-up animation

### Product Filters (`product-filter.js`)

AJAX-based filtering on the products listing page:
- Uses History API (`pushState`) for clean URLs
- Fetches filtered results via `fetch()` with `X-Requested-With: XMLHttpRequest` header
- Parses response HTML with DOMParser and swaps `#products-content`
- Supports: sort, price range, availability, attribute filters
- Global instance at `window.productFilter`

### Bundle Offers (`bundle-offers.js`)

Bundle offer data is NOT included in product listing API responses. This module:
1. Collects all `data-bundle-offer-product-id` elements on the page
2. Batch-fetches bundle offers via `/api/v1/products/bundle-offers?product_ids=...`
3. Displays bundle offer badges on matching product cards
4. Uses a `Map` to track loaded offers (avoids re-fetching)
5. Global instance at `window.bundleOffersLoader`

---

## Platform Integration

### Zid SDK (`window.zid`)

The Zid SDK is loaded by `{% vitrin_body %}` and provides client-side APIs. It loads asynchronously -- always check for availability or use `waitForZid()`:

```js
// Cart
await zid.cart.get();
await zid.cart.addProduct({ product_id, quantity, custom_fields });
await zid.cart.updateProduct({ id, quantity });
await zid.cart.removeProduct({ id });
await zid.cart.applyCoupon({ coupon_code });
await zid.cart.removeCoupon();
await zid.cart.getCalculatedPoints(total);
await zid.cart.getCustomerLoyaltyPoints();
await zid.cart.getRedemptionMethods(currencyCode);
await zid.cart.addRedemptionMethod({ id });
await zid.cart.removeRedemptionMethod();
await zid.cart.removeGiftCard();

// Products
const product = await zid.products.get(product_id);
const options = await zid.products.getProductOptions(product_id, {
  attributes: true,
  option_fields: true,
  input_fields: true
});
await zid.products.createQuestion(productId, { question, name, email, is_anonymous });

// Account
await zid.account.addToWishList(product_id);
await zid.account.removeFromWishList(product_id);

// Customer
zid.customer.login.open({ redirectTo });

// Store
zid.store.showMessage(message, type);
```

### Auth Dialog (`window.auth_dialog`)

The Vitrin platform injects an authentication dialog. The theme opens it via:

```js
window.auth_dialog.open();
```

After successful OTP verification, the platform dispatches `vitrin:auth:success`. The theme's layout module handles this by:
1. Updating `window.customerAuthState`
2. Redirecting to any `pendingAuthRedirect` URL

### Platform-Injected HTML

`{% vitrin_body %}` injects several HTML elements into the page:
- Auth dialog
- Gift card dialog (`window.gift_dialog`)
- Loyalty rewards popup (`.loyalty-rewards-popup-init`)
- Payment widgets (Tamara, Tabby)
- Toast notification system (`window.toastr`)

---

## Window Globals and Platform Callbacks

### Window Globals Set by Theme

These are exposed for platform integration and must be maintained:

| Global | Set By | Purpose |
|--------|--------|---------|
| `window.productFilter` | `product-filter.js` | Product filter instance (`applyFilter`, `clearFilters`, etc.) |
| `window.bundleOffersLoader` | `bundle-offers.js` | Bundle offers loader (`reload()`) |
| `window.PhoneInput` | `phone-input.js` | Phone input API (`init`, `initElement`, `get`) |
| `window.CartPage` | `cart/controller.js` | Cart page controller (`init`) |
| `window.cartManager` | `cart/add-to-cart.js` | Cart manager (`refreshBadge`) |
| `window.handleLoginAction` | `features/layout.js` | Login trigger with optional redirect |
| `window.initQtyInputs` | `features/qty-input.js` | Re-init quantity inputs (used by cart refresh) |
| `window.initPriceSliders` | `features/price-slider.js` | Re-init price sliders |
| `window.updateQtyMax` | `features/qty-input.js` | Update max quantity for an input |
| `window.updateTimeAgoElements` | `time-ago.js` | Re-render relative time displays |
| `window.selectMobileCountry` | `features/layout.js` | Locale navigation (mobile) |
| `window.selectMobileLanguage` | `features/layout.js` | Locale navigation (mobile) |
| `window.popupLoyaltyReward` | `layout-loyalty.js` / `loyalty-rewards.js` | Open loyalty rewards popup |
| `window.closeLoyaltyRewardsWindow` | `layout-loyalty.js` / `loyalty-rewards.js` | Close loyalty rewards popup |
| `window.CountriesData` | `data/countries.js` | Countries list with phone validation |

### Platform Callbacks (MUST keep these)

The Vitrin platform calls these functions directly. **Removing them will break platform features:**

| Callback | Called By | Purpose |
|----------|-----------|---------|
| `window.productOptionsChanged(product)` | Platform variant system | Called when product options/variant data changes |
| `window.cartProductsHtmlChanged()` | Platform cart system | Called when cart HTML is updated by platform |
| `window.toggleBundleItems(item, btn)` | Platform bundle UI | Toggle bundle item expand/collapse |
| `window.refreshCartPage()` | Platform cart system | Trigger cart page AJAX refresh |

### Global Config Objects (set in `layout.jinja`)

These are set as inline `<script>` blocks in the layout:

```js
window.layoutConfig = {
  profileUrl: "{{ store_url }}/account-profile",
  defaultCountryCode: "{{ store.country_code }}",
  currentLanguage: "{{ request.language }}",
  currentCountry: "{{ request.country }}"
};

window.productTranslations = {
  addedToCart: "{{ _('Added to cart') }}",
  outOfStock: "{{ _('Out of stock') }}",
  // ...
};

window.notifyMeTranslations = {
  success: "{{ _('You will be notified...') }}",
  // ...
};

window.customerAuthState = {
  isAuthenticated: {{ not session.is_guest | lower }},
  isGuest: {{ session.is_guest | lower }}
};
```

---

## Component Patterns

### Buttons

```html
<button class="btn btn-filled btn-lg">Primary</button>
<button class="btn btn-outlined btn-md">Secondary</button>
<button class="btn btn-text btn-sm">Text</button>
<button class="btn btn-destructive btn-md">Delete</button>
<button class="btn btn-icon btn-icon-md"><svg>...</svg></button>
```

### Inputs

```html
<label class="form-label">Label <span class="form-label-required">*</span></label>
<input class="form-input" placeholder="Enter text" />
<p class="form-caption">Helper text</p>
```

### Checkboxes and Radios

```html
<label class="form-control">
  <input type="checkbox" class="form-checkbox" />
  Label
</label>
```

### Badges

```html
<span class="badge badge-filled">Tag</span>
<span class="badge badge-outlined">Tag</span>
```

### Quantity Input

A reusable component with `+`, `-`, and delete buttons:

```html
<div data-qty-input="product-123">
  <button data-qty-action="remove">Delete</button>
  <button data-qty-action="decrease">-</button>
  <input data-qty-value min="1" max="10" value="1" />
  <button data-qty-action="increase">+</button>
</div>
```

Supports syncing between multiple inputs via `data-qty-sync="other-id"`.

### Phone Input

Full phone input component with country selector, search, and validation:

```html
<div data-phone-input data-all-countries="true">
  <input type="hidden" data-phone-full-value />
  <input type="hidden" data-phone-country-code value="+966" />
  <button data-slot="country-trigger" popovertarget="phone-popover">
    <span data-phone-country-display>+966</span>
  </button>
  <input data-phone-number-input placeholder="5XX XXX XXX" />
</div>
```

The component exposes a programmatic API via `wrapper._phoneInput`:
- `getValue()`, `getDialCode()`, `getPhoneNumber()`
- `setDialCode(code)`, `setPhoneNumber(number)`
- `validate()`, `isValid()`, `reset()`

### Headless Components

Unstyled, BEM-named product components in `components/products/headless/`. These provide structure without default styles -- developers control all styling via CSS classes in `css/product-options.css`, `css/custom-fields.css`, and `css/product-filters.css`.

See `docs/headless/` for full documentation.

---

## Localization and RTL

### Translations

```jinja
{{ _("Add to cart") }}
{{ _("Remaining %s only") }}
```

Translation strings live in `locale/ar/LC_MESSAGES/messages.po`. Each `msgid` must be unique -- duplicates break compilation.

### RTL Support

The theme is designed RTL-first (Arabic). Use logical properties and Tailwind's `rtl:` prefix:

```html
<div class="ms-4 me-2">Logical margins</div>
<svg class="rtl:rotate-180">Arrow icon</svg>
```

For CSS overrides:

```css
[dir="rtl"] .element {
  /* RTL-specific styles */
}
```

RTL handling in JavaScript:
- **Carousels**: Embla direction is set based on `document.documentElement.dir`
- **Price slider**: noUiSlider direction is set to `"rtl"` when `document.documentElement.dir === "rtl"`
- **Marquee**: Uses separate `marquee-scroll-rtl` keyframes (translates +50% instead of -50%)
- **Loyalty button**: Positioned based on `loyalty_button_direction` config

### Locale Navigation

The layout module handles language/region switching via:
- `navigateToLocale(countryCode, languageCode)` -- constructs locale URL and redirects
- `window.selectMobileCountry(code)` and `window.selectMobileLanguage(code)` -- mobile drawer shortcuts
- `[data-locale-form]` forms for desktop locale selection

---

## External Dependencies

### npm Packages (bundled by Vite)

| Package | Purpose | Used In |
|---------|---------|---------|
| `embla-carousel` | Product carousels and sliders | `lib/carousel.js`, `product/gallery.js` |
| `embla-carousel-auto-height` | Auto-height plugin for carousels | `lib/carousel.js` |
| `embla-carousel-auto-scroll` | Auto-scroll plugin for carousels | `lib/carousel.js` |
| `nouislider` | Price range filter slider | `features/price-slider.js` |
| `photoswipe` | Product image lightbox | `product/lightbox.js` |

### npm Packages (CSS only, imported by TailwindCSS)

| Package | Purpose |
|---------|---------|
| `photoswipe` | Base lightbox styles (overridden by `css/lightbox.css`) |
| `nouislider` | Base slider styles (overridden by `css/price-slider.css`) |
| `@tailwindcss/typography` | Prose content styling for static pages |

### CDN (loaded in `layout.jinja`)

| Library | Version | Purpose |
|---------|---------|---------|
| TailwindPlus Elements | `@tailwindplus/elements@1.0.22` | Interactive UI: `el-dialog`, `el-disclosure`, `el-dropdown`, `el-select`, `el-popover` |
| Google Fonts | (varies per merchant) | Font family set by merchant in theme settings |
| Flag CDN | `flagcdn.com` | Country flag images for phone input component |

---

## Secrets and Configuration

**There are no secrets in this repository.** No `.env` files, no API keys, no credentials.

- Authentication is handled by the Vitrin CLI's global login session (`vitrin login`)
- All API calls go through `window.zid` (SDK injected by the platform)
- The one API call made directly (`/api/v1/products/bundle-offers` and `/api/v1/products/{id}/stock-alerts`) uses the store's own domain origin and requires no auth tokens

### `.gitignore` excludes:

- `node_modules/`
- `.env` files (precautionary, none exist)
- `*.zip` files
- `.vitrin/dist/` (CLI build artifacts)
- `assets/styles.css` (compiled CSS)
- `assets/dist/` (compiled JS)

---

## Non-Obvious Behaviors

### Auth-Based Visibility (Cache-Safe)

Elements with `data-auth-guest` or `data-auth-user` attributes are shown/hidden based on login state. This allows page HTML to be cached by CDN while still showing correct content after client-side hydration:

```html
<a data-auth-guest href="/login">Login</a>
<a data-auth-user href="/profile" class="hidden">My Account</a>
```

The `initAuthVisibility()` function in `layout.js` toggles these on load and after `vitrin:auth:success`.

### Product ID Normalization

Cart product IDs from the API sometimes include hyphens and mixed case. The `findCartItem()` function normalizes both IDs before comparison:

```js
const normalize = (id) => String(id).replace(/-/g, "").toLowerCase();
```

This prevents mismatches where the same product would show "Add to cart" instead of a quantity input.

### Dual Loyalty Systems

There are two loyalty modules:

1. **`layout-loyalty.js`** -- A standalone script loaded via `<script>` tag after `{% vitrin_body %}`. It uses global variables (`store_currency_code`, `text_loyalty_rewards`, etc.) set by inline script in `layout.jinja`. This runs on all pages and creates a floating rewards button.

2. **`features/loyalty-rewards.js`** -- A module bundled in `theme.js`. It initializes only when `window.loyaltyConfig` is set. It provides the same floating button but through the module system.

The store configuration determines which one is active. Both expose the same global functions (`window.popupLoyaltyReward`, `window.closeLoyaltyRewardsWindow`).

### Quick View Prefetch

When a user hovers over a product card's quick-view trigger, the theme starts fetching the product data after a 3-second delay. This means the modal opens instantly when clicked. The LRU cache holds up to 20 product responses.

### Cart State Sync on Page Load

On every page load, `syncCartState()` fetches the current cart and scans the page for all "Add to cart" buttons. If a product is already in the cart, the button is replaced with a quantity input showing the current quantity. This ensures consistency between the cart and product listings.

### Platform Widget Post-Injection

The loyalty rewards popup HTML is injected by `{% vitrin_body %}` with the class `.loyalty-rewards-popup-init`. On first open, the theme moves this element to `document.body` (reparenting from its injected position) and removes the init class. This is necessary because the platform injects it in a position that may have CSS overflow issues.

### `cartObj` Global

The cart page stores the cart data on `window.cartObj` for payment widget updates. The totals module reads from this global when updating Tamara/Tabby widgets and loyalty calculations.

### Time Ago Auto-Update

The `time-ago.js` utility updates relative time strings every 60 seconds via `setInterval`. Elements with `data-time-ago-date` are automatically refreshed.

---

## Resources

- [Vitrin Platform Docs](https://docs.zid.sa/llms.txt)
- [Headless Components](docs/headless/)
- [Architecture Notes](docs/architecture.md)
