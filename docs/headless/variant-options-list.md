# Variant Options - List Style

Renders product variant options as clickable list items (`<ul>` > `<li>`).
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
| `productOptionListItemClicked(event)` | `<li>` | Click |

### Data Flow

```
1. User clicks <li> element
2. productOptionListItemClicked(event) triggered
3. Platform reads `value` attribute from clicked <li>
4. Platform reads `name` and `index` from parent <ul>
5. Platform fetches new variant data from API
6. Platform calls window.productOptionsChanged(selectedProduct)
7. Theme updates UI via the callback
```

### Required Attributes

| Element | Attribute | Purpose |
|---------|-----------|---------|
| `<ul>` | `name` | Option name (e.g., "Size", "Color") |
| `<ul>` | `index` | Zero-based option index |
| `<li>` | `value` | Choice value |
| `<li>` | `onclick` | Must call `productOptionListItemClicked(event)` |
| `<div>` (group) | `index` | Zero-based option index |

## HTML Output

```html
<input id="product-parent-id" type="hidden" value="{product.id}" />

<div id="product-variants-options" class="product-options product-options--list">
  <div class="product-options__group" index="0">
    <label class="product-options__label">Size</label>
    <ul name="Size" index="0" class="product-options__list">
      <li value="S" onclick="productOptionListItemClicked(event)" class="product-options__item">
        <span class="product-options__item-text">S</span>
      </li>
      <li value="M" onclick="productOptionListItemClicked(event)" class="product-options__item active">
        <span class="product-options__item-text">M</span>
      </li>
      <li value="L" onclick="productOptionListItemClicked(event)" class="product-options__item">
        <span class="product-options__item-text">L</span>
      </li>
    </ul>
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
| `.product-options--list` | List style variant (clickable items) |

### Elements

| Class | Element | Description |
|-------|---------|-------------|
| `.product-options__group` | `<div>` | Option group container |
| `.product-options__label` | `<label>` | Option name label |
| `.product-options__list` | `<ul>` | List containing choices |
| `.product-options__item` | `<li>` | Clickable choice item |
| `.product-options__item-text` | `<span>` | Text inside choice |

### States

| Class | Element | Description |
|-------|---------|-------------|
| `.active` | `.product-options__item` | Currently selected option |

## Styling Guide

All styles must be applied via CSS. No default styles are included.

### Basic Example

```css
/* Container */
.product-options--list {
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

/* Options list */
.product-options__list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  list-style: none;
  padding: 0;
  margin: 0;
}

/* Option item */
.product-options__item {
  padding: 0.5rem 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.2s;
}

.product-options__item:hover {
  border-color: var(--primary);
}

/* REQUIRED: Active state styling */
.product-options__item.active {
  border-color: var(--primary);
  background-color: var(--primary);
  color: var(--primary-foreground);
}
```

### Tailwind Example

```html
<style>
.product-options--list { @apply flex flex-col gap-4; }
.product-options__group { @apply flex flex-col gap-2; }
.product-options__label { @apply text-sm font-medium text-foreground; }
.product-options__list { @apply flex flex-wrap gap-2 list-none p-0 m-0; }
.product-options__item { @apply px-4 py-2 border border-border rounded cursor-pointer transition-all hover:border-primary; }
.product-options__item.active { @apply border-primary bg-primary text-primary-foreground; }
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
  {% include 'components/products/headless/options/variant-options-list.jinja' %}
{% endwith %}
```

## File Location

```
components/products/headless/options/variant-options-list.jinja
```
