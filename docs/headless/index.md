# Headless Product Components

Headless components for Zid's Vitrin platform. These components output raw HTML with BEM classes, giving developers complete styling freedom.

## Design Philosophy

- **Headless**: No default styles included - you control all styling
- **BEM Naming**: Consistent Block-Element-Modifier class naming
- **Platform Compatible**: All required selectors and event handlers for Zid's product.js
- **Styling Freedom**: Apply styles via CSS, Tailwind, or any framework

## Component Structure

```
components/products/headless/
├── options/
│   ├── variant-options.jinja          # Orchestrator
│   ├── variant-options-list.jinja     # Clickable list style
│   └── variant-options-dropdown.jinja # Dropdown select style
├── fields/
│   ├── custom-input-fields.jinja      # Orchestrator
│   ├── custom-field-text.jinja        # Text/number/date/time
│   ├── custom-field-textarea.jinja    # Multi-line text
│   ├── custom-field-dropdown.jinja    # Select dropdown
│   ├── custom-field-checkbox.jinja    # Multi-select checkboxes
│   └── custom-field-file.jinja        # File/image upload
├── filters/
│   └── product-filters.jinja          # Attribute filters (headless, zero JS)
└── quantity-input.jinja               # Quantity selector
```

## Quick Reference

### Variant Options

| Component | Purpose | Documentation |
|-----------|---------|---------------|
| `variant-options.jinja` | Orchestrator (routes to list or dropdown) | [Read more](./variant-options.md) |
| `variant-options-list.jinja` | Clickable chips/buttons | [Read more](./variant-options-list.md) |
| `variant-options-dropdown.jinja` | Select dropdowns | [Read more](./variant-options-dropdown.md) |

### Custom Input Fields

| Component | Types | Documentation |
|-----------|-------|---------------|
| `custom-input-fields.jinja` | Orchestrator (routes by type) | [Read more](./custom-input-fields.md) |
| `custom-field-text.jinja` | TEXT, NUMBER, DATE, TIME | [Read more](./custom-field-text.md) |
| `custom-field-textarea.jinja` | TEXTAREA | [Read more](./custom-field-textarea.md) |
| `custom-field-dropdown.jinja` | DROPDOWN | [Read more](./custom-field-dropdown.md) |
| `custom-field-checkbox.jinja` | CHECKBOX | [Read more](./custom-field-checkbox.md) |
| `custom-field-file.jinja` | FILE, IMAGE | [Read more](./custom-field-file.md) |

### Quantity Input

| Component | Purpose | Documentation |
|-----------|---------|---------------|
| `quantity-input.jinja` | Quantity selector with +/- buttons | [Read more](./quantity-input.md) |

### Product Filters

| Component | Purpose | Documentation |
|-----------|---------|---------------|
| `product-filters.jinja` | Headless attribute filters (zero inline JS, CSS layout modes) | [Read more](./product-filters.md) |

## BEM Classes Overview

### Variant Options

```css
.product-options                /* Block */
.product-options--list          /* Modifier: list style */
.product-options--dropdown      /* Modifier: dropdown style */
.product-options__group         /* Element: option group */
.product-options__label         /* Element: option label */
.product-options__list          /* Element: <ul> container */
.product-options__item          /* Element: <li> choice */
.product-options__item.active   /* State: selected */
.product-options__item-text     /* Element: choice text */
.product-options__select        /* Element: <select> dropdown */
```

### Custom Fields

```css
.custom-field                   /* Block */
.custom-field--text             /* Modifier: text input */
.custom-field--number           /* Modifier: number input */
.custom-field--date             /* Modifier: date input */
.custom-field--time             /* Modifier: time input */
.custom-field--textarea         /* Modifier: textarea */
.custom-field--dropdown         /* Modifier: select dropdown */
.custom-field--checkbox         /* Modifier: checkboxes */
.custom-field--file             /* Modifier: file upload */
.custom-field--image            /* Modifier: image upload */
.custom-field__label            /* Element: field label */
.custom-field__input            /* Element: input field */
.custom-field__textarea         /* Element: textarea */
.custom-field__select           /* Element: select dropdown */
.custom-field__options          /* Element: checkbox container */
.custom-field__option           /* Element: checkbox wrapper */
.custom-field__checkbox         /* Element: checkbox input */
.custom-field__option-text      /* Element: checkbox label text */
.custom-field__hint             /* Element: hint text */
.custom-field__price            /* Element: price indicator */
.custom-field__required         /* Element: required marker */
```

### File Upload

```css
.file-upload                    /* Block */
.file-upload__input             /* Element: hidden file input */
.file-upload__delete            /* Element: delete button */
.file-upload__delete-icon       /* Element: delete icon */
.file-upload__preview           /* Element: image preview container */
.file-upload__preview-image     /* Element: preview image */
.file-upload__name              /* Element: filename display */
.file-upload__button            /* Element: upload button */
```

### Product Filters

```css
.product-filter                    /* Block: single filter (<details>) */
.product-filter--attribute         /* Modifier: attribute filter */
.product-filter__summary           /* <summary> trigger row */
.product-filter__summary-text      /* Attribute name */
.product-filter__summary-badge     /* Selected count badge */
.product-filter__summary-icon      /* Chevron icon */
.product-filter__content           /* Content wrapper */
.product-filter__options           /* Options list */
.product-filter__option            /* Single option <label> */
.product-filter__option--default   /* Text option */
.product-filter__option--color     /* Color swatch option */
.product-filter__option--icon      /* Icon option */
.product-filter__checkbox          /* Checkbox input */
.product-filter__text              /* Option text */
.product-filter__color             /* Color swatch */
.product-filter__icon              /* Icon container */
.product-filter__icon-image        /* Icon image */
.product-filter__more              /* "View more" <details> */
.product-filter__toggle            /* "View more/less" trigger */
```

## Platform Integration

These components integrate with Zid's platform `product.js` which handles:

- Variant selection and API calls
- Custom field data collection
- Cart operations
- Price updates

### Key Callbacks

```javascript
// Called by platform when variant changes
window.productOptionsChanged = function(selectedProduct) {
  // Update UI with new variant data
};
```

### Required Selectors

The platform expects these IDs to exist:

| Selector | Purpose |
|----------|---------|
| `#product-parent-id` | Hidden input with parent product ID |
| `#product-variants-options` | Container for variant options |
| `#product-custom-user-input-fields` | Container for custom fields |
| `#product-quantity` | Quantity input field |

## Usage Examples

### Basic Variant Options (Dropdown)

```jinja
{% with options=product.options, product=product %}
  {% include 'components/products/headless/options/variant-options.jinja' %}
{% endwith %}
```

### Variant Options (List Style)

```jinja
{% with options=product.options, product=product, style='list' %}
  {% include 'components/products/headless/options/variant-options.jinja' %}
{% endwith %}
```

### Custom Input Fields

```jinja
{% with fields=product.fields %}
  {% include 'components/products/headless/fields/custom-input-fields.jinja' %}
{% endwith %}
```

### Quantity Input

```jinja
{% include 'components/products/headless/quantity-input.jinja' %}
```

## Styling Tips

1. **Start with a CSS reset** for the BEM classes
2. **Use CSS custom properties** for theming (colors, spacing, radius)
3. **Style the `.active` state** - it's required for variant selection
4. **Hide file inputs** with `display: none` - they're triggered by buttons
5. **Test RTL layouts** - these components support RTL via CSS

