# Headless Product Attribute Filters

A single, purely headless Jinja component that renders product attribute filters as semantic HTML. Zero inline JavaScript. All visual behavior is controlled by CSS layout wrapper classes.

## Philosophy

- **One output, many layouts** — The component always renders `<details>/<summary>` accordion markup. A single CSS class on the parent container transforms its appearance (sidebar accordion, topbar dropdown, inline chips, minimal list, 2-column grid).
- **Zero inline JS** — No `onchange`, `onclick`, or any inline handlers. Developers attach their own event listeners via BEM classes and `data-*` attributes.
- **Form-native** — Checkboxes use `name="attributes[slug][]"` so wrapping in a `<form>` gives you native form submission for free.
- **Pre-selection** — Reads `session.query_params` to check matching checkboxes on page load.

## File

```
components/products/headless/filters/product-filters.jinja
```

CSS (optional — provides base styles + sidebar layout):

```
assets/css/headless-filters.css
```

## Quick Start

### Basic usage (sidebar accordion)

```jinja
<form method="get" action="" data-product-filters>
  <div class="filters--sidebar">
    {% with open=true, max_visible=5 %}
      {% include 'components/products/headless/filters/product-filters.jinja' %}
    {% endwith %}
  </div>
  <button type="reset">{{ _("Clear") }}</button>
  <button type="submit">{{ _("Apply") }}</button>
</form>
```

### Inside the theme's filter drawer

This is how the default theme uses it inside `advanced-filters.jinja`:

```jinja
<div class="filters--sidebar">
  {% with max_visible=5, open=true %}
    {% include 'components/products/headless/filters/product-filters.jinja' %}
  {% endwith %}
</div>
```

## Parameters

Pass via `{% with %}` before including.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `open` | bool | `false` | Start `<details>` elements open |
| `max_visible` | int | `0` | Max visible options per attribute. `0` = show all. When set, excess options are hidden behind a "View more" toggle |

### Required context

These variables must be available in the template context (provided automatically by the Vitrin platform on product listing pages):

| Variable | Description |
|----------|-------------|
| `filters` | Object with `attributes` array. Each attribute has `slug`, `name`, `is_enabled`, `data` (array of options) |
| `session` | Session object with `query_params` for reading current URL parameters |

Each option in `attribute.data` has:

| Property | Description |
|----------|-------------|
| `value` | Display text and form value |
| `type` | `'default'`, `'color'`, or `'icon'` |
| `type_value` | For `color`: hex string. For `icon`: object with `thumbnail` URL |

## HTML Output

The component renders this structure for each enabled attribute:

```html
<details
  class="product-filter product-filter--attribute"
  data-filter-type="attribute"
  data-attribute="color"
  data-attribute-name="Color"
  data-total-options="8"
  data-visible-options="5"
  data-selected-count="2"
  open
>
  <summary class="product-filter__summary">
    <span class="product-filter__summary-text">Color</span>
    <span class="product-filter__summary-badge" aria-label="2 selected">2</span>
    <svg class="product-filter__summary-icon">...</svg>
  </summary>

  <div class="product-filter__content">
    <div class="product-filter__options" role="group" aria-label="Color">

      <!-- Default option -->
      <label class="product-filter__option product-filter__option--default"
             data-option-type="default" data-option-value="Red">
        <input type="checkbox" name="attributes[color][]" value="Red"
               class="product-filter__checkbox" data-attribute-option="color" checked />
        <span class="product-filter__text">Red</span>
      </label>

      <!-- Color swatch option -->
      <label class="product-filter__option product-filter__option--color"
             data-option-type="color" data-option-value="Blue">
        <input type="checkbox" name="attributes[color][]" value="Blue"
               class="product-filter__checkbox" data-attribute-option="color" />
        <span class="product-filter__color" style="background-color: #0000FF;"
              data-color="#0000FF" title="Blue"></span>
        <span class="product-filter__text">Blue</span>
      </label>

      <!-- Icon option -->
      <label class="product-filter__option product-filter__option--icon"
             data-option-type="icon" data-option-value="Cotton">
        <input type="checkbox" name="attributes[material][]" value="Cotton"
               class="product-filter__checkbox" data-attribute-option="material" />
        <span class="product-filter__icon">
          <img src="..." alt="Cotton" class="product-filter__icon-image" loading="lazy" />
        </span>
        <span class="product-filter__text">Cotton</span>
      </label>
    </div>

    <!-- View more/less (only when max_visible truncates) -->
    <details class="product-filter__more">
      <summary class="product-filter__toggle">
        <span class="product-filter__toggle-more">View more (3)</span>
        <span class="product-filter__toggle-less">View less</span>
      </summary>
      <div class="product-filter__options product-filter__options--overflow">
        <!-- remaining options -->
      </div>
    </details>
  </div>
</details>
```

## Data Attributes

All data attributes are on the rendered HTML for JS hooking. No inline handlers — you query these yourself.

### On `<details>` (the filter block)

| Attribute | Value | Description |
|-----------|-------|-------------|
| `data-filter-type` | `"attribute"` | Filter type identifier |
| `data-attribute` | e.g. `"color"` | Attribute slug (unique key) |
| `data-attribute-name` | e.g. `"Color"` | Human-readable name |
| `data-total-options` | e.g. `"8"` | Total option count |
| `data-visible-options` | e.g. `"5"` | Visible before "View more" (only present when truncated) |
| `data-selected-count` | e.g. `"2"` | Pre-selected count from URL |

### On `<label>` (each option)

| Attribute | Value | Description |
|-----------|-------|-------------|
| `data-option-type` | `"default"` / `"color"` / `"icon"` | Option display type |
| `data-option-value` | e.g. `"Red"` | Option value string |

### On `<input>` (each checkbox)

| Attribute | Value | Description |
|-----------|-------|-------------|
| `data-attribute-option` | e.g. `"color"` | Attribute slug (for `querySelectorAll`) |

### On color swatches

| Attribute | Value | Description |
|-----------|-------|-------------|
| `data-color` | e.g. `"#FF0000"` | Hex color value |

## BEM Classes Reference

### Block & Modifiers

```css
.product-filter                    /* Block: single filter (a <details> element) */
.product-filter--attribute         /* Modifier: attribute filter type */
```

### Elements

```css
.product-filter__summary           /* <summary> trigger row */
.product-filter__summary-text      /* Attribute name text */
.product-filter__summary-badge     /* Selected count badge (only when > 0) */
.product-filter__summary-icon      /* Chevron SVG icon */
.product-filter__content           /* Content wrapper inside <details> */
.product-filter__options           /* Options list container */
.product-filter__options--overflow /* Hidden options (inside "view more") */
.product-filter__option            /* Single option <label> */
.product-filter__option--default   /* Text-only option */
.product-filter__option--color     /* Color swatch option */
.product-filter__option--icon      /* Icon/image option */
.product-filter__checkbox          /* Checkbox <input> */
.product-filter__text              /* Option label text */
.product-filter__color             /* Color swatch <span> */
.product-filter__icon              /* Icon wrapper <span> */
.product-filter__icon-image        /* Icon <img> */
.product-filter__more              /* "View more" <details> */
.product-filter__toggle            /* "View more/less" <summary> */
.product-filter__toggle-more       /* "View more (N)" text */
.product-filter__toggle-less       /* "View less" text */
```

## CSS Layout Modes

The same HTML output can look completely different depending on the CSS class on the wrapper. This is the core of the headless approach — **one component, many layouts**.

The included `headless-filters.css` ships with **base styles + `.filters--sidebar`** only. The other layouts below are provided as copy-paste examples you can add to your own CSS.

### `.filters--sidebar` — Vertical Accordions (included)

```html
<div class="filters--sidebar">
  {% include 'components/products/headless/filters/product-filters.jinja' %}
</div>
```

Each attribute becomes a bordered accordion section with `py-4` spacing and `divide-y` borders, matching the theme's `disclosure.jinja` visual style. This is the only layout included in the CSS file.

---

### `.filters--topbar` — Horizontal Dropdowns (example)

Filters display inline. When a `<details>` opens, its content drops down as an absolutely-positioned panel with shadow and border.

```html
<div class="filters--topbar">
  {% include 'components/products/headless/filters/product-filters.jinja' %}
</div>
```

```css
.filters--topbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1.5rem;
}

.filters--topbar .product-filter__summary {
  padding: 0.5rem 0;
}

.filters--topbar .product-filter__summary:hover {
  text-decoration: underline;
}

/* Dropdown panel */
.filters--topbar .product-filter__content {
  position: absolute;
  top: 100%;
  inset-inline-start: 0;
  z-index: 50;
  min-width: 220px;
  max-height: 320px;
  overflow-y: auto;
  padding: 1rem;
  margin-top: 0.25rem;
  background: var(--background);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  box-shadow: 0 4px 16px rgb(0 0 0 / 0.08);
}
```

---

### `.filters--chips` — Inline Pills (example)

Summary headers are hidden. Options render as pill-shaped chips. Checkbox is visually hidden; the whole pill highlights on `:checked`.

```html
<div class="filters--chips">
  {% include 'components/products/headless/filters/product-filters.jinja' %}
</div>
```

```css
.filters--chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.filters--chips .product-filter {
  display: contents;
}

.filters--chips .product-filter__summary {
  display: none;
}

.filters--chips .product-filter__content,
.filters--chips .product-filter__options {
  display: contents;
}

/* Style options as pills */
.filters--chips .product-filter__option {
  padding: 0.375rem 0.75rem;
  background: var(--secondary);
  border: 1px solid var(--border);
  border-radius: 9999px;
  gap: 0.375rem;
}

.filters--chips .product-filter__option:hover {
  border-color: var(--foreground);
  color: var(--foreground);
}

.filters--chips .product-filter__option:has(input:checked) {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-foreground);
}

.filters--chips .product-filter__checkbox {
  display: none;
}
```

---

### `.filters--minimal` — Clean, No Borders (example)

Uppercase label, no chevron icon, no borders. Clean, sparse layout.

```html
<div class="filters--minimal">
  {% include 'components/products/headless/filters/product-filters.jinja' %}
</div>
```

```css
.filters--minimal {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.filters--minimal .product-filter__summary {
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0;
  margin-bottom: 0.75rem;
}

.filters--minimal .product-filter__summary-icon {
  display: none;
}

.filters--minimal details[open] .product-filter__content,
.filters--minimal .product-filter__content,
.filters--minimal .product-filter__options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filters--minimal .product-filter__option {
  padding: 0.25rem 0;
}
```

---

### `.filters--grid` — 2-Column Cards (example)

Each attribute becomes a card in a 2-column grid (1-column on mobile). Cards have `bg-secondary` background and rounded corners.

```html
<div class="filters--grid">
  {% include 'components/products/headless/filters/product-filters.jinja' %}
</div>
```

```css
.filters--grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

@media (max-width: 640px) {
  .filters--grid {
    grid-template-columns: 1fr;
  }
}

.filters--grid .product-filter {
  padding: 1rem;
  background: var(--secondary);
  border-radius: var(--radius-lg);
}

.filters--grid .product-filter__summary {
  font-weight: 500;
  margin-bottom: 0.75rem;
}

.filters--grid .product-filter__summary-icon {
  display: none;
}

.filters--grid details .product-filter__content {
  display: flex;
}
```

---

### Wrapper utilities (examples)

Helper layouts for page-level composition. Copy the ones you need.

#### Topbar row (filters + sort on right)

```css
.filters-topbar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 0;
}

.filters-topbar-row .filters--topbar {
  flex: 1;
}
```

#### Sidebar + content 2-column layout

```css
.filters-sidebar-layout {
  display: grid;
  gap: 2rem;
}

@media (min-width: 1024px) {
  .filters-sidebar-layout {
    grid-template-columns: 280px 1fr;
  }
}

.filters-sidebar-layout__filters {
  position: sticky;
  top: 8rem;
  max-height: calc(100vh - 10rem);
  overflow-y: auto;
}

@media (max-width: 1023px) {
  .filters-sidebar-layout__filters {
    display: none;
  }
}
```

Usage:

```html
<div class="filters-sidebar-layout">
  <aside class="filters-sidebar-layout__filters">
    <div class="filters--sidebar">...</div>
  </aside>
  <main>
    <!-- Product grid -->
  </main>
</div>
```

## View More / View Less

When `max_visible` is set and an attribute has more options than the limit, the excess options are wrapped in a nested `<details>` element. This is entirely CSS-driven — no JavaScript needed.

```jinja
{% with max_visible=5 %}
  {% include 'components/products/headless/filters/product-filters.jinja' %}
{% endwith %}
```

The CSS toggles "View more (N)" / "View less" text via the `[open]` attribute:

```css
/* "View more" visible by default */
.product-filter__toggle-less { display: none; }

/* When opened, swap */
.product-filter__more[open] .product-filter__toggle-more { display: none; }
.product-filter__more[open] .product-filter__toggle-less { display: inline; }
```

## JavaScript Integration

The component outputs zero inline JS. Here's how to hook into it.

### Listen to checkbox changes

```js
document.addEventListener('change', (e) => {
  const checkbox = e.target.closest('.product-filter__checkbox');
  if (!checkbox) return;

  const slug = checkbox.dataset.attributeOption;  // e.g. "color"
  const value = checkbox.value;                     // e.g. "Red"
  const checked = checkbox.checked;

  console.log(`${slug}: ${value} → ${checked}`);
});
```

### Get all selected values for an attribute

```js
function getSelectedValues(slug) {
  return Array.from(
    document.querySelectorAll(`[data-attribute-option="${slug}"]:checked`)
  ).map(el => el.value);
}

// Usage
getSelectedValues('color');  // ["Red", "Blue"]
```

### Get all active filters

```js
function getAllFilters() {
  const filters = {};
  document.querySelectorAll('[data-filter-type="attribute"]').forEach(el => {
    const slug = el.dataset.attribute;
    const selected = getSelectedValues(slug);
    if (selected.length > 0) {
      filters[slug] = selected;
    }
  });
  return filters;
}
```

### Clear all filters

```js
document.querySelectorAll('.product-filter__checkbox:checked').forEach(cb => {
  cb.checked = false;
});
```

### Update selected count badge

```js
function updateBadge(slug) {
  const filter = document.querySelector(`[data-attribute="${slug}"]`);
  const count = filter.querySelectorAll('.product-filter__checkbox:checked').length;
  filter.dataset.selectedCount = count;

  let badge = filter.querySelector('.product-filter__summary-badge');
  if (count > 0) {
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'product-filter__summary-badge';
      filter.querySelector('.product-filter__summary-text').after(badge);
    }
    badge.textContent = count;
    badge.setAttribute('aria-label', `${count} selected`);
  } else if (badge) {
    badge.remove();
  }
}
```

### With the theme's `productFilter` system

The default theme uses `window.productFilter` from `product-filter.js`. When using the headless component inside the theme's drawer (as in `advanced-filters.jinja`), the form's `onsubmit` calls `productFilter.submitDrawerForm(event)` which collects all form data and applies filters via URL params.

## Styling Customization

### Override BEM classes

The provided `headless-filters.css` is optional. You can write your own styles targeting the BEM classes.

#### Example: Custom checkbox style

```css
.product-filter__checkbox {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-radius: var(--radius);
  appearance: none;
}

.product-filter__checkbox:checked {
  background: var(--primary);
  border-color: var(--primary);
}
```

#### Example: Color swatches as circles

```css
.product-filter__color {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 9999px;
  border: 2px solid transparent;
}

.product-filter__option--color:has(:checked) .product-filter__color {
  border-color: var(--primary);
}
```

#### Example: Hide checkbox, style whole option as chip

```css
.product-filter__checkbox {
  display: none;
}

.product-filter__option {
  padding: 0.5rem 1rem;
  border: 1px solid var(--border);
  border-radius: 9999px;
  cursor: pointer;
}

.product-filter__option:has(:checked) {
  background: var(--primary);
  color: var(--primary-foreground);
  border-color: var(--primary);
}
```

#### Example: Tailwind utility overrides

```html
<style>
  .product-filter__summary { @apply py-4 text-sm font-semibold; }
  .product-filter__options { @apply flex flex-col gap-3; }
  .product-filter__option { @apply flex items-center gap-2 text-sm; }
  .product-filter__checkbox { @apply size-5 rounded border-gray-300; }
  .product-filter__color { @apply size-6 rounded-full; }
</style>
```

### Writing a custom layout mode

Create your own layout class following the same pattern:

```css
/* .filters--my-layout */
.filters--my-layout {
  /* Container styles */
}

.filters--my-layout .product-filter {
  /* Per-filter block styles */
}

.filters--my-layout .product-filter__summary {
  /* Trigger/header styles */
}

.filters--my-layout .product-filter__content {
  /* Content panel styles */
}

.filters--my-layout .product-filter__options {
  /* Options list styles */
}

.filters--my-layout .product-filter__option {
  /* Individual option styles */
}

.filters--my-layout .product-filter__checkbox {
  /* Checkbox styles (or hide with display: none for chip-style) */
}
```

## File Location

```
components/products/headless/filters/product-filters.jinja
```
