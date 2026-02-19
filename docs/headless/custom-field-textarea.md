# Custom Field - Textarea

Renders a multi-line text custom input field.
Outputs raw HTML with BEM classes for complete styling freedom.

## Platform Integration

### Required Selectors

| Selector | Element | Purpose |
|----------|---------|---------|
| `#product-custom-user-input-fields` | `<div>` | Container ID (on wrapper) |
| `#{custom_field.id}` | `<textarea>` | Field ID for platform to read value |

### Event Handlers

| Handler | Element | Trigger |
|---------|---------|---------|
| `productOptionInputChanged(event)` | `<textarea>` | Input |

### Data Flow

```
1. User types in <textarea>
2. productOptionInputChanged(event) triggered
3. Platform reads value, id, name, data-type, data-type-att from <textarea>
4. Platform stores custom field data for cart
5. On add-to-cart, platform includes custom field values
```

### Required Attributes

| Element | Attribute | Purpose |
|---------|-----------|---------|
| `<textarea>` | `id` | Custom field ID |
| `<textarea>` | `name` | Field label (for form data) |
| `<textarea>` | `data-type` | Base type (`TEXT`) |
| `<textarea>` | `data-type-att` | Must be `TEXTAREA` |
| `<textarea>` | `oninput` | Must call `productOptionInputChanged(event)` |

## HTML Output

```html
<div id="product-custom-user-input-fields" class="custom-field custom-field--textarea">
  <label class="custom-field__label" for="field-456">
    Special Instructions
    <span class="custom-field__price">(+$2.00)</span>
    <span class="custom-field__required">*</span>
  </label>

  <textarea
    id="field-456"
    name="Special Instructions"
    data-type="TEXT"
    data-type-att="TEXTAREA"
    title="Special Instructions"
    lang="en"
    placeholder="Enter any special instructions..."
    rows="5"
    oninput="productOptionInputChanged(event)"
    required
    class="custom-field__input custom-field__textarea"
  ></textarea>

  <p class="custom-field__hint">Describe any special requirements</p>
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
| `.custom-field--textarea` | Textarea input type |

### Elements

| Class | Element | Description |
|-------|---------|-------------|
| `.custom-field__label` | `<label>` | Field label |
| `.custom-field__input` | `<textarea>` | Base input class |
| `.custom-field__textarea` | `<textarea>` | Textarea-specific class |
| `.custom-field__hint` | `<p>` | Hint/help text |
| `.custom-field__price` | `<span>` | Additional price indicator |
| `.custom-field__required` | `<span>` | Required field marker |

## Styling Guide

All styles must be applied via CSS. No default styles are included.

### Basic Example

```css
/* Container */
.custom-field--textarea {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Label */
.custom-field__label {
  font-weight: 500;
  color: var(--foreground);
}

/* Textarea */
.custom-field__textarea {
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 1rem;
  color: var(--foreground);
  background-color: var(--background);
  resize: vertical;
  min-height: 120px;
  font-family: inherit;
}

.custom-field__textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--ring);
}

.custom-field__textarea::placeholder {
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
.custom-field--textarea { @apply flex flex-col gap-2; }
.custom-field__label { @apply text-sm font-medium text-foreground; }
.custom-field__textarea { @apply w-full px-4 py-3 border border-border rounded bg-background text-foreground resize-y min-h-[120px] placeholder:text-secondary focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring; }
.custom-field__hint { @apply text-sm text-secondary; }
</style>
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `custom_field` | object | Yes | - | Field object with `id`, `label`, `type`, `is_required`, `hint`, `price` |
| `rows` | number | No | `5` | Number of visible text rows |

### Custom Field Object

```javascript
{
  id: "field-456",
  label: "Special Instructions",
  type: "TEXT",
  is_required: true,
  hint: "Describe any special requirements",
  price: 2.00,
  formatted_price: "$2.00"
}
```

## Usage

```jinja
{% with custom_field=field, rows=5 %}
  {% include 'components/products/headless/fields/custom-field-textarea.jinja' %}
{% endwith %}
```

## File Location

```
components/products/headless/fields/custom-field-textarea.jinja
```
