# Variant Options - Dropdown Style

Renders product variant options as dropdown selects (`<select>`).
Outputs raw HTML with BEM classes for complete styling freedom.

## Platform Integration

### Required Selectors

| Selector | Element | Purpose |
|----------|---------|---------|
| `#product-parent-id` | `<input type="hidden">` | Stores parent product ID for variant lookup |
| `#product-variants-options` | `<div>` | Container for all variant option groups |

### Event Handlers

| Handler | Element | Trigger |
|---------|---------|---------|
| `productOptionInputChanged(event)` | `<select>` | Change |

### Data Flow

```
1. User selects option from <select>
2. productOptionInputChanged(event) triggered
3. Platform reads value from selected <option>
4. Platform reads name, data-option-id, index from <select>
5. Platform fetches new variant data from API
6. Platform calls window.productOptionsChanged(selectedProduct)
7. Theme updates UI via the callback
```

### Required Attributes

| Element | Attribute | Purpose |
|---------|-----------|---------|
| `<select>` | `name` | Option name (e.g., "Size", "Color") |
| `<select>` | `id` | Unique ID (`option-{option.id}`) |
| `<select>` | `data-option-id` | Option ID for platform lookup |
| `<select>` | `index` | Zero-based option index |
| `<select>` | `onchange` | Must call `productOptionInputChanged(event)` |
| `<option>` | `value` | Choice value |
| `<div>` (group) | `index` | Zero-based option index |

## HTML Output

```html
<input id="product-parent-id" type="hidden" value="{product.id}" />

<div id="product-variants-options" class="product-options product-options--dropdown">
  <div class="product-options__group" index="0">
    <label class="product-options__label" for="option-123">Size</label>
    <select
      name="Size"
      id="option-123"
      data-option-id="123"
      index="0"
      onchange="productOptionInputChanged(event)"
      required
      class="product-options__select"
    >
      <option value="S">S</option>
      <option value="M" selected>M</option>
      <option value="L">L</option>
    </select>
  </div>
</div>
```

## BEM Classes

### Block

| Class | Element | Description |
|-------|---------|-------------|
| `.product-options` | `<div>` | Main container |

### Modifiers

| Class | Description |
|-------|-------------|
| `.product-options--dropdown` | Dropdown style variant |

### Elements

| Class | Element | Description |
|-------|---------|-------------|
| `.product-options__group` | `<div>` | Option group container |
| `.product-options__label` | `<label>` | Option name label |
| `.product-options__select` | `<select>` | Dropdown select element |

## Styling Guide

All styles must be applied via CSS. No default styles are included.

### Basic Example

```css
/* Container */
.product-options--dropdown {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Option group */
.product-options__group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Label */
.product-options__label {
  font-weight: 500;
  color: var(--foreground);
}

/* Select */
.product-options__select {
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background-color: var(--background);
  color: var(--foreground);
  font-size: 1rem;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,..."); /* Custom arrow */
  background-repeat: no-repeat;
  background-position: right 1rem center;
}

.product-options__select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--ring);
}
```

### Tailwind Example

```html
<style>
.product-options--dropdown { @apply flex flex-col gap-4; }
.product-options__group { @apply flex flex-col gap-2; }
.product-options__label { @apply text-sm font-medium text-foreground; }
.product-options__select { @apply w-full px-4 py-3 border border-border rounded bg-background text-foreground focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring; }
</style>
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `options` | array | Yes | Product options with `id`, `name`, `choices` |
| `product` | object | Yes | Product object with `selected_product` |

## Usage

```jinja
{% with options=product.options, product=product %}
  {% include 'components/products/headless/options/variant-options-dropdown.jinja' %}
{% endwith %}
```

## File Location

```
components/products/headless/options/variant-options-dropdown.jinja
```
