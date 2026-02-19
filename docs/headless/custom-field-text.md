# Custom Field - Text Input

Renders a single-line text custom input field.
Supports types: `TEXT`, `NUMBER`, `DATE`, `TIME`.
Outputs raw HTML with BEM classes for complete styling freedom.

## Platform Integration

### Required Selectors

| Selector | Element | Purpose |
|----------|---------|---------|
| `#product-custom-user-input-fields` | `<div>` | Container ID (on wrapper) |
| `#{custom_field.id}` | `<input>` | Field ID for platform to read value |

### Event Handlers

| Handler | Element | Trigger |
|---------|---------|---------|
| `productOptionInputChanged(event)` | `<input>` | Input |

### Data Flow

```
1. User types in <input>
2. productOptionInputChanged(event) triggered
3. Platform reads value, id, name, data-type from <input>
4. Platform stores custom field data for cart
5. On add-to-cart, platform includes custom field values
```

### Required Attributes

| Element | Attribute | Purpose |
|---------|-----------|---------|
| `<input>` | `id` | Custom field ID |
| `<input>` | `name` | Field label (for form data) |
| `<input>` | `data-type` | Field type (`TEXT`, `NUMBER`, `DATE`, `TIME`) |
| `<input>` | `oninput` | Must call `productOptionInputChanged(event)` |

## HTML Output

```html
<div id="product-custom-user-input-fields" class="custom-field custom-field--text">
  <label class="custom-field__label" for="field-123">
    Engraving Text
    <span class="custom-field__price">(+$5.00)</span>
    <span class="custom-field__required">*</span>
  </label>

  <input
    type="text"
    id="field-123"
    name="Engraving Text"
    data-type="TEXT"
    title="Engraving Text"
    lang="en"
    placeholder="Enter your text"
    oninput="productOptionInputChanged(event)"
    required
    class="custom-field__input"
  />

  <p class="custom-field__hint">Maximum 20 characters</p>
</div>
```

### Type Variations

```html
<!-- NUMBER type -->
<input type="number" data-type="NUMBER" ... />

<!-- DATE type -->
<input type="date" data-type="DATE" ... />

<!-- TIME type -->
<input type="time" data-type="TIME" ... />
```

## BEM Classes

### Block

| Class | Element | Description |
|-------|---------|-------------|
| `.custom-field` | `<div>` | Main container |

### Modifiers

| Class | Description |
|-------|-------------|
| `.custom-field--text` | Text input type |
| `.custom-field--number` | Number input type |
| `.custom-field--date` | Date input type |
| `.custom-field--time` | Time input type |

### Elements

| Class | Element | Description |
|-------|---------|-------------|
| `.custom-field__label` | `<label>` | Field label |
| `.custom-field__input` | `<input>` | Input element |
| `.custom-field__hint` | `<p>` | Hint/help text |
| `.custom-field__price` | `<span>` | Additional price indicator |
| `.custom-field__required` | `<span>` | Required field marker |

## Styling Guide

All styles must be applied via CSS. No default styles are included.

### Basic Example

```css
/* Container */
.custom-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Label */
.custom-field__label {
  font-weight: 500;
  color: var(--foreground);
}

/* Price addon */
.custom-field__price {
  font-weight: normal;
  color: var(--secondary);
  margin-left: 0.25rem;
}

/* Required marker */
.custom-field__required {
  color: var(--destructive);
  margin-left: 0.25rem;
}

/* Input */
.custom-field__input {
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 1rem;
  color: var(--foreground);
  background-color: var(--background);
}

.custom-field__input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--ring);
}

.custom-field__input::placeholder {
  color: var(--secondary);
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
.custom-field { @apply flex flex-col gap-2; }
.custom-field__label { @apply text-sm font-medium text-foreground; }
.custom-field__price { @apply font-normal text-secondary ml-1; }
.custom-field__required { @apply text-destructive ml-1; }
.custom-field__input { @apply w-full px-4 py-3 border border-border rounded bg-background text-foreground placeholder:text-secondary focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring; }
.custom-field__hint { @apply text-sm text-secondary; }
</style>
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `custom_field` | object | Yes | Field object with `id`, `label`, `type`, `is_required`, `hint`, `price` |

### Custom Field Object

```javascript
{
  id: "field-123",
  label: "Engraving Text",
  type: "TEXT",        // TEXT | NUMBER | DATE | TIME
  is_required: true,
  hint: "Maximum 20 characters",
  price: 5.00,
  formatted_price: "$5.00"
}
```

## Usage

```jinja
{% with custom_field=field %}
  {% include 'components/products/headless/fields/custom-field-text.jinja' %}
{% endwith %}
```

## File Location

```
components/products/headless/fields/custom-field-text.jinja
```
