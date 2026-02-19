# Custom Field - Checkbox

Renders a multi-select checkbox custom input field.
Outputs raw HTML with BEM classes for complete styling freedom.

## Platform Integration

### Required Selectors

| Selector | Element | Purpose |
|----------|---------|---------|
| `#product-custom-user-input-fields` | `<div>` | Container ID (on wrapper) |
| `#{custom_field.id}` | `<div>` | Container with data attributes for platform |

### Event Handlers

| Handler | Element | Trigger |
|---------|---------|---------|
| `productOptionInputChanged(event)` | `<input type="checkbox">` | Change |

### Data Flow

```
1. User checks/unchecks checkbox(es)
2. productOptionInputChanged(event) triggered
3. Platform reads checked values from all checkboxes with matching name
4. Platform stores custom field data for cart
5. On add-to-cart, platform includes selected checkbox values
```

### Required Attributes

| Element | Attribute | Purpose |
|---------|-----------|---------|
| Container `<div>` | `id` | Custom field ID |
| Container `<div>` | `data-type` | Must be `CHECKBOX` |
| Container `<div>` | `data-name` | Field label |
| `<input>` | `type` | Must be `checkbox` |
| `<input>` | `name` | Field label (for form data) |
| `<input>` | `value` | Option value |
| `<input>` | `onchange` | Must call `productOptionInputChanged(event)` |

## HTML Output

```html
<div id="product-custom-user-input-fields" class="custom-field custom-field--checkbox">
  <label class="custom-field__label">
    Add-ons
    <span class="custom-field__price">(+$1.00 each)</span>
    <span class="custom-field__required">*</span>
  </label>

  <div
    id="field-101"
    data-type="CHECKBOX"
    data-name="Add-ons"
    title="Add-ons"
    class="custom-field__options"
  >
    <label class="custom-field__option">
      <input
        type="checkbox"
        name="Add-ons"
        value="Extra Sauce"
        onchange="productOptionInputChanged(event)"
        class="custom-field__checkbox"
      />
      <span class="custom-field__option-text">Extra Sauce</span>
    </label>

    <label class="custom-field__option">
      <input
        type="checkbox"
        name="Add-ons"
        value="Extra Cheese"
        onchange="productOptionInputChanged(event)"
        class="custom-field__checkbox"
      />
      <span class="custom-field__option-text">Extra Cheese</span>
    </label>

    <label class="custom-field__option">
      <input
        type="checkbox"
        name="Add-ons"
        value="Bacon"
        onchange="productOptionInputChanged(event)"
        class="custom-field__checkbox"
      />
      <span class="custom-field__option-text">Bacon</span>
    </label>
  </div>

  <p class="custom-field__hint">Select all that apply</p>
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
| `.custom-field--checkbox` | Checkbox input type |

### Elements

| Class | Element | Description |
|-------|---------|-------------|
| `.custom-field__label` | `<label>` | Field label |
| `.custom-field__options` | `<div>` | Container for all checkbox options |
| `.custom-field__option` | `<label>` | Individual option wrapper |
| `.custom-field__checkbox` | `<input>` | Checkbox input |
| `.custom-field__option-text` | `<span>` | Option label text |
| `.custom-field__hint` | `<p>` | Hint/help text |
| `.custom-field__price` | `<span>` | Additional price indicator |
| `.custom-field__required` | `<span>` | Required field marker |

## Styling Guide

All styles must be applied via CSS. No default styles are included.

### Basic Example

```css
/* Container */
.custom-field--checkbox {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Label */
.custom-field__label {
  font-weight: 500;
  color: var(--foreground);
}

/* Options container */
.custom-field__options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Individual option */
.custom-field__option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

/* Checkbox */
.custom-field__checkbox {
  width: 1rem;
  height: 1rem;
  accent-color: var(--primary);
  cursor: pointer;
}

/* Option text */
.custom-field__option-text {
  color: var(--foreground);
}

/* Hint text */
.custom-field__hint {
  font-size: 0.875rem;
  color: var(--secondary);
}
```

### Custom Checkbox Style

```css
/* Hide default checkbox */
.custom-field__checkbox {
  appearance: none;
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid var(--border);
  border-radius: 0.25rem;
  cursor: pointer;
  position: relative;
}

.custom-field__checkbox:checked {
  background-color: var(--primary);
  border-color: var(--primary);
}

.custom-field__checkbox:checked::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 1px;
  width: 5px;
  height: 10px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.custom-field__checkbox:focus {
  outline: none;
  box-shadow: 0 0 0 2px var(--ring);
}
```

### Tailwind Example

```html
<style>
.custom-field--checkbox { @apply flex flex-col gap-2; }
.custom-field__label { @apply text-sm font-medium text-foreground; }
.custom-field__options { @apply flex flex-col gap-2; }
.custom-field__option { @apply flex items-center gap-2 cursor-pointer; }
.custom-field__checkbox { @apply w-4 h-4 accent-primary cursor-pointer; }
.custom-field__option-text { @apply text-foreground; }
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
  id: "field-101",
  label: "Add-ons",
  type: "CHECKBOX",
  is_required: false,
  hint: "Select all that apply",
  price: 1.00,
  formatted_price: "$1.00",
  options: [
    { name: "Extra Sauce", value: "Extra Sauce" },
    { name: "Extra Cheese", value: "Extra Cheese" },
    { name: "Bacon", value: "Bacon" }
  ]
}
```

## Usage

```jinja
{% with custom_field=field %}
  {% include 'components/products/headless/fields/custom-field-checkbox.jinja' %}
{% endwith %}
```

## File Location

```
components/products/headless/fields/custom-field-checkbox.jinja
```
