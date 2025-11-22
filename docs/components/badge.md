# Badge

Displays a badge or a component that looks like a badge.

## Overview

The Badge component is a small, versatile UI element used to highlight information, statuses, or categories. It supports multiple variants and can render as either a `<span>` or `<a>` tag while maintaining consistent styling.

## Usage

```jinja
{% with content='New', variant='filled' %}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

## Variants

### Filled (Default)

Light gray background with dark text. Used for general labels and tags.

```jinja
{% with content='Featured', variant='filled' %}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

### Outlined

Transparent background with border. Used for secondary labels or tags.

```jinja
{% with content='On Sale', variant='outlined' %}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

## Examples

### Basic Badge

Simple text badge with default filled variant.

```jinja
{% with content='New Arrival' %}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

### Badge with Icon

Icons and text are automatically spaced with a 4px gap.

```jinja
{% set badge_content %}
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M8 2v12M2 8h12" stroke="currentColor" stroke-width="2"/>
  </svg>
  Trending
{% endset %}
{% with content=badge_content, variant='outlined' %}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

### Link as Badge

Use the `href` parameter to render as an `<a>` tag.

```jinja
{% with content='Shop Electronics', variant='filled', href='/categories/electronics' %}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

### Badge with Custom Classes

Add custom classes with the `class` parameter.

```jinja
{% with content='Limited Edition', variant='outlined', class='uppercase' %}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

### Badge with Data Attributes

Pass custom attributes using the `attrs` parameter.

```jinja
{% with
  content='VIP',
  variant='filled',
  attrs='data-badge-type="membership" aria-label="VIP member badge"'
%}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

## Real-World Examples

### Product Status Badges

```jinja
{# Sale badge #}
{% if product.sale_price and product.sale_price < product.price %}
  {% with content=_(\"Sale\"), variant='filled' %}
    {% include 'components/ui/badge.jinja' %}
  {% endwith %}
{% endif %}

{# Out of stock badge #}
{% if not product.in_stock %}
  {% with content=_(\"Out of Stock\"), variant='outlined' %}
    {% include 'components/ui/badge.jinja' %}
  {% endwith %}
{% endif %}
```

### Category Tags

```jinja
{% if product.keywords and product.keywords|length > 0 %}
  {% for keyword in product.keywords[:3] %}
    {% with content=keyword|upper, variant='outlined' %}
      {% include 'components/ui/badge.jinja' %}
    {% endwith %}
  {% endfor %}
{% endif %}
```

### Discount Badge

```jinja
{% if product.discount_percentage and product.discount_percentage > 0 %}
  {% set discount_badge %}
    {{ _(\"Discount\") }} {{ product.discount_percentage }}%
  {% endset %}
  {% with content=discount_badge, variant='filled', class='bg-[#DDF8DC] text-[#649560]' %}
    {% include 'components/ui/badge.jinja' %}
  {% endwith %}
{% endif %}
```

### Badge with Icon and Text

```jinja
{% set star_badge %}
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 1l2 5h5l-4 3 1.5 5L8 11l-4.5 3L5 9 1 6h5l2-5z"/>
  </svg>
  Best Seller
{% endset %}
{% with content=star_badge, variant='filled' %}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

### Shipping Badge

```jinja
{% set shipping_badge %}
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M1 4h10v8H1V4zm10 2h3l1 2v4h-4V6z" stroke="currentColor" stroke-width="1.5"/>
  </svg>
  {{ _(\"Free Shipping\") }}
{% endset %}
{% with content=shipping_badge, variant='outlined' %}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

## API Reference

### Parameters

| Parameter  | Type      | Default   | Description                                    |
|------------|-----------|-----------|------------------------------------------------|
| `content`  | `string`  | Required  | Badge text or HTML content (use `{% set %}`)   |
| `variant`  | `string`  | `filled`  | Badge style: `filled`, `outlined`              |
| `href`     | `string`  | -         | If set, renders as `<a>` tag                   |
| `class`    | `string`  | -         | Additional CSS classes                         |
| `attrs`    | `string`  | -         | Raw HTML attributes (data-*, aria-*, etc.)     |

## Accessibility

- Use semantic `<span>` for labels, `<a>` for navigation
- Add `aria-label` for icon-only badges
- Ensure sufficient color contrast for readability
- Keep badge text concise and descriptive

## Customization

### Rounded Badge

```jinja
{% with content='99+', variant='outlined', class='rounded-full' %}
  {% include 'components/ui/badge.jinja' %}
{% endwith %}
```

## Source Code

[`components/ui/badge.jinja`](../../components/ui/badge.jinja)
