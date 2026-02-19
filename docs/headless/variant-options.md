# Variant Options - Orchestrator

Routes to the appropriate variant display style (list or dropdown).
This is the main entry point for rendering product variant options.

## Overview

This component acts as an orchestrator that includes either:
- `variant-options-list.jinja` for clickable list/chip style
- `variant-options-dropdown.jinja` for dropdown select style

## Platform Integration

See individual component documentation:
- [variant-options-list.md](./variant-options-list.md)
- [variant-options-dropdown.md](./variant-options-dropdown.md)

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `options` | array | Yes | - | Product options with `id`, `name`, `choices` |
| `product` | object | Yes | - | Product object with `selected_product` |
| `style` | string | No | `'dropdown'` | Display style: `'list'` or `'dropdown'` |

## Usage

### Default (Dropdown Style)

```jinja
{% with options=product.options, product=product %}
  {% include 'components/products/headless/options/variant-options.jinja' %}
{% endwith %}
```

### List Style

```jinja
{% with options=product.options, product=product, style='list' %}
  {% include 'components/products/headless/options/variant-options.jinja' %}
{% endwith %}
```

## Behavior

```
┌─────────────────────────────────────┐
│        variant-options.jinja        │
│         (Orchestrator)              │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        │  style param?     │
        └─────────┬─────────┘
                  │
     ┌────────────┴────────────┐
     │                         │
     ▼                         ▼
style='list'            style='dropdown'
     │                    (default)
     │                         │
     ▼                         ▼
┌─────────────────┐   ┌─────────────────┐
│ variant-options │   │ variant-options │
│   -list.jinja   │   │ -dropdown.jinja │
└─────────────────┘   └─────────────────┘
```

## File Location

```
components/products/headless/options/variant-options.jinja
```

## Related Documentation

- [variant-options-list.md](./variant-options-list.md) - List style details
- [variant-options-dropdown.md](./variant-options-dropdown.md) - Dropdown style details
