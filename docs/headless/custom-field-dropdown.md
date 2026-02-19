# Custom Field - Dropdown

Renders a dropdown select custom input field.
Outputs raw HTML with BEM classes for complete styling freedom.

## Platform Integration

### Required Selectors

| Selector | Element | Purpose |
|----------|---------|---------|
| `#product-custom-user-input-fields` | `<div>` | Container ID (on wrapper) |
| `#{custom_field.id}` | `<select>` | Field ID for platform to read value |

### Event Handlers

| Handler | Element | Trigger |
|---------|---------|---------|
| `productOptionInputChanged(event)` | `<select>` | Change |

### Data Flow

```
1. User selects option from <select>
2. productOptionInputChanged(event) triggered
3. Platform reads value, id, name, data-type from <select>
4. Platform stores custom field data for cart
5. On add-to-cart, platform includes custom field values
```

### Required Attributes

| Element | Attribute | Purpose |
|---------|-----------|---------|
| `<select>` | `id` | Custom field ID |
| `<select>` | `name` | Field label (for form data) |
| `<select>` | `data-type` | Must be `DROPDOWN` |
| `<select>` | `onchange` | Must call `productOptionInputChanged(event)` |
| `<option>` | `value` | Option value |

## HTML Output

```html
<div id="product-custom-user-input-fields" class="custom-field custom-field--dropdown">
  <label class="custom-field__label" for="field-789">
    Gift Wrap Style
    <span class="custom-field__price">(+$3.00)</span>
    <span class="custom-field__required">*</span>
  </label>

  <select
    id="field-789"
    name="Gift Wrap Style"
    data-type="DROPDOWN"
    title="Gift Wrap Style"
    lang="en"
    onchange="productOptionInputChanged(event)"
    required
    class="custom-field__select"
  >
    <option value="">Select an option...</option>
    <option value="Classic">Classic</option>
    <option value="Premium">Premium</option>
    <option value="Luxury">Luxury</option>
  </select>

  <p class="custom-field__hint">Choose your preferred gift wrap</p>
</div>
```

## BEM Classes

### Block

| Class | Element | Description |
|-------|---------|-------------|
| `.custom-field` | `<div>` | Main container |

### Modifiers

| Class | Description |
|-------|-------------|
| `.custom-field--dropdown` | Dropdown input type |

### Elements

| Class | Element | Description |
|-------|---------|-------------|
| `.custom-field__label` | `<label>` | Field label |
| `.custom-field__select` | `<select>` | Dropdown select element |
| `.custom-field__hint` | `<p>` | Hint/help text |
| `.custom-field__price` | `<span>` | Additional price indicator |
| `.custom-field__required` | `<span>` | Required field marker |

## Styling Guide

All styles must be applied via CSS. No default styles are included.

### Basic Example

```css
/* Container */
.custom-field--dropdown {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Label */
.custom-field__label {
  font-weight: 500;
  color: var(--foreground);
}

/* Select */
.custom-field__select {
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 1rem;
  color: var(--foreground);
  background-color: var(--background);
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 1rem center;
  padding-right: 2.5rem;
}

.custom-field__select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--ring);
}

/* Hint text */
.custom-field__hint {
  font-size: 0.875rem;
  color: var(--secondary);
}
```

### Tailwind Example

```html
<style>
.custom-field--dropdown { @apply flex flex-col gap-2; }
.custom-field__label { @apply text-sm font-medium text-foreground; }
.custom-field__select { @apply w-full px-4 py-3 pr-10 border border-border rounded bg-background text-foreground cursor-pointer appearance-none focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring; }
.custom-field__hint { @apply text-sm text-secondary; }
</style>
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `custom_field` | object | Yes | Field object with `id`, `label`, `type`, `is_required`, `hint`, `price`, `options` |

### Custom Field Object

```javascript
{
  id: "field-789",
  label: "Gift Wrap Style",
  type: "DROPDOWN",
  is_required: true,
  hint: "Choose your preferred gift wrap",
  price: 3.00,
  formatted_price: "$3.00",
  options: [
    { name: "Classic", value: "Classic" },
    { name: "Premium", value: "Premium" },
    { name: "Luxury", value: "Luxury" }
  ]
}
```

## Usage

```jinja
{% with custom_field=field %}
  {% include 'components/products/headless/fields/custom-field-dropdown.jinja' %}
{% endwith %}
```

## File Location

```
components/products/headless/fields/custom-field-dropdown.jinja
```
