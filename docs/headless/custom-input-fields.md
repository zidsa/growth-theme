# Custom Input Fields - Orchestrator

Routes custom fields to the appropriate field component based on type.
This is the main entry point for rendering product custom input fields.

## Overview

This component iterates over product custom fields and includes the appropriate component for each field type:

| Type | Component |
|------|-----------|
| `TEXT` | `custom-field-text.jinja` |
| `NUMBER` | `custom-field-text.jinja` |
| `DATE` | `custom-field-text.jinja` |
| `TIME` | `custom-field-text.jinja` |
| `TEXTAREA` | `custom-field-textarea.jinja` |
| `DROPDOWN` | `custom-field-dropdown.jinja` |
| `CHECKBOX` | `custom-field-checkbox.jinja` |
| `FILE` | `custom-field-file.jinja` |
| `IMAGE` | `custom-field-file.jinja` |

## Platform Integration

See individual component documentation:
- [custom-field-text.md](./custom-field-text.md) - Text, number, date, time
- [custom-field-textarea.md](./custom-field-textarea.md) - Multi-line text
- [custom-field-dropdown.md](./custom-field-dropdown.md) - Select dropdown
- [custom-field-checkbox.md](./custom-field-checkbox.md) - Multi-select checkboxes
- [custom-field-file.md](./custom-field-file.md) - File and image upload

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `fields` | array | Yes | Array of custom field objects |

### Custom Field Object

```javascript
{
  id: "field-123",
  label: "Field Label",
  type: "TEXT",        // TEXT | NUMBER | DATE | TIME | TEXTAREA | DROPDOWN | CHECKBOX | FILE | IMAGE
  is_required: true,
  hint: "Help text",
  price: 5.00,
  formatted_price: "$5.00",
  options: []          // For DROPDOWN and CHECKBOX types
}
```

## Usage

```jinja
{% with fields=product.fields %}
  {% include 'components/products/headless/fields/custom-input-fields.jinja' %}
{% endwith %}
```

## Behavior

```
┌─────────────────────────────────────┐
│     custom-input-fields.jinja       │
│         (Orchestrator)              │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        │  for field in     │
        │     fields        │
        └─────────┬─────────┘
                  │
     ┌────────────┼────────────┬────────────┬────────────┐
     │            │            │            │            │
     ▼            ▼            ▼            ▼            ▼
   TEXT       TEXTAREA     DROPDOWN    CHECKBOX    FILE/IMAGE
  NUMBER
   DATE
   TIME
     │            │            │            │            │
     ▼            ▼            ▼            ▼            ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐
│ custom- │ │ custom-  │ │ custom-  │ │ custom-  │ │ custom- │
│ field-  │ │ field-   │ │ field-   │ │ field-   │ │ field-  │
│ text    │ │ textarea │ │ dropdown │ │ checkbox │ │ file    │
└─────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘
```

## File Location

```
components/products/headless/fields/custom-input-fields.jinja
```

## Related Documentation

- [custom-field-text.md](./custom-field-text.md) - Text input details
- [custom-field-textarea.md](./custom-field-textarea.md) - Textarea details
- [custom-field-dropdown.md](./custom-field-dropdown.md) - Dropdown details
- [custom-field-checkbox.md](./custom-field-checkbox.md) - Checkbox details
- [custom-field-file.md](./custom-field-file.md) - File upload details
