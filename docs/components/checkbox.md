# Checkbox

A control that allows the user to toggle between checked and not checked.

## Overview

The Checkbox component is a simple, accessible form control that allows users to select one or multiple options. It's built with native HTML checkbox inputs and custom styling for a consistent appearance across browsers.

## Usage

```jinja
{% with label='Accept terms and conditions', id='terms', name='terms' %}
  {% include 'components/ui/checkbox.jinja' %}
{% endwith %}
```

## Examples

### Basic Checkbox

Simple checkbox with label.

```jinja
{% with label='Subscribe to newsletter', id='newsletter', name='newsletter' %}
  {% include 'components/ui/checkbox.jinja' %}
{% endwith %}
```

### Checkbox Without Label

Checkbox without visible label (use `aria-label` for accessibility).

```jinja
{% with id='agree', name='agree', attrs='aria-label="I agree"' %}
  {% include 'components/ui/checkbox.jinja' %}
{% endwith %}
```

### Checked by Default

Use the `checked` parameter to set initial state.

```jinja
{% with label='Remember me', id='remember', name='remember', checked=true %}
  {% include 'components/ui/checkbox.jinja' %}
{% endwith %}
```

### Disabled Checkbox

Disable interaction with the `disabled` parameter.

```jinja
{% with label='Unavailable option', id='unavailable', name='unavailable', disabled=true %}
  {% include 'components/ui/checkbox.jinja' %}
{% endwith %}
```

### Required Checkbox

Mark as required for form validation.

```jinja
{% with label='I accept the terms *', id='required-terms', name='required-terms', required=true %}
  {% include 'components/ui/checkbox.jinja' %}
{% endwith %}
```

### Checkbox with Custom Value

Specify a custom value for form submission.

```jinja
{% with label='Enable notifications', id='notifications', name='settings', value='notifications_enabled' %}
  {% include 'components/ui/checkbox.jinja' %}
{% endwith %}
```

### Checkbox with Data Attributes

Pass custom attributes for JavaScript interaction.

```jinja
{% with
  label='Track my order',
  id='track-order',
  name='track_order',
  attrs='data-action="track" data-category="shipping"'
%}
  {% include 'components/ui/checkbox.jinja' %}
{% endwith %}
```

## Real-World Examples

### Terms and Conditions Form

```jinja
<form method="post" action="/checkout">
  {% with
    label='I agree to the terms and conditions',
    id='terms',
    name='terms',
    required=true
  %}
    {% include 'components/ui/checkbox.jinja' %}
  {% endwith %}

  {% with
    label='Subscribe to marketing emails',
    id='marketing',
    name='marketing'
  %}
    {% include 'components/ui/checkbox.jinja' %}
  {% endwith %}

  {% with content='Continue to payment', variant='filled', size='lg', type='submit' %}
    {% include 'components/ui/button.jinja' %}
  {% endwith %}
</form>
```

### Product Filter Checkboxes

```jinja
<form method="get" action="/products">
  <h3>Filter by Brand</h3>
  <div class="flex flex-col gap-3">
    {% for brand in brands %}
      {% with
        label=brand.name,
        id='brand-' ~ brand.id,
        name='brands[]',
        value=brand.id,
        checked=(brand.id in selected_brands)
      %}
        {% include 'components/ui/checkbox.jinja' %}
      {% endwith %}
    {% endfor %}
  </div>
</form>
```

### Account Preferences

```jinja
<form method="post" action="/account/preferences">
  <h3>Email Preferences</h3>
  <div class="flex flex-col gap-4">
    {% with
      label='Order updates',
      id='email-orders',
      name='email_preferences[]',
      value='orders',
      checked=('orders' in user.email_preferences)
    %}
      {% include 'components/ui/checkbox.jinja' %}
    {% endwith %}

    {% with
      label='Promotional offers',
      id='email-promos',
      name='email_preferences[]',
      value='promos',
      checked=('promos' in user.email_preferences)
    %}
      {% include 'components/ui/checkbox.jinja' %}
    {% endwith %}

    {% with
      label='Product recommendations',
      id='email-recommendations',
      name='email_preferences[]',
      value='recommendations',
      checked=('recommendations' in user.email_preferences)
    %}
      {% include 'components/ui/checkbox.jinja' %}
    {% endwith %}
  </div>

  {% with content='Save preferences', variant='filled', size='lg', type='submit' %}
    {% include 'components/ui/button.jinja' %}
  {% endwith %}
</form>
```

### Shipping Options

```jinja
<div class="flex flex-col gap-3">
  <h3>Additional Services</h3>

  {% with
    label='Gift wrapping (+$5.00)',
    id='gift-wrap',
    name='services[]',
    value='gift_wrap'
  %}
    {% include 'components/ui/checkbox.jinja' %}
  {% endwith %}

  {% with
    label='Express shipping (+$15.00)',
    id='express',
    name='services[]',
    value='express'
  %}
    {% include 'components/ui/checkbox.jinja' %}
  {% endwith %}

  {% with
    label='Insurance (+$3.00)',
    id='insurance',
    name='services[]',
    value='insurance'
  %}
    {% include 'components/ui/checkbox.jinja' %}
  {% endwith %}
</div>
```

### Newsletter Signup

```jinja
<form method="post" action="/newsletter/subscribe">
  <div class="flex flex-col gap-4">
    <input type="email" name="email" placeholder="Enter your email" required />

    {% with
      label='I agree to receive marketing communications',
      id='consent',
      name='consent',
      required=true
    %}
      {% include 'components/ui/checkbox.jinja' %}
    {% endwith %}

    {% with content='Subscribe', variant='filled', size='lg', type='submit' %}
      {% include 'components/ui/button.jinja' %}
    {% endwith %}
  </div>
</form>
```

### Product Comparison

```jinja
<div class="flex flex-col gap-3">
  <h3>Select products to compare</h3>
  {% for product in products %}
    <div class="flex items-center justify-between rounded border p-3">
      <div class="flex items-center gap-3">
        <img src="{{ product.image }}" alt="{{ product.name }}" class="h-12 w-12 rounded object-cover" />
        <div>
          <p class="font-medium">{{ product.name }}</p>
          <p class="text-secondary text-sm">{{ product.formatted_price }}</p>
        </div>
      </div>
      {% with
        label='',
        id='compare-' ~ product.id,
        name='compare[]',
        value=product.id,
        attrs='aria-label="Compare ' ~ product.name ~ '"'
      %}
        {% include 'components/ui/checkbox.jinja' %}
      {% endwith %}
    </div>
  {% endfor %}
</div>
```

## API Reference

### Parameters

| Parameter       | Type      | Default | Description                                  |
|----------------|-----------|---------|----------------------------------------------|
| `label`        | `string`  | -       | Text label displayed next to checkbox        |
| `id`           | `string`  | Required| Unique identifier for the checkbox           |
| `name`         | `string`  | Required| Form field name for submission               |
| `value`        | `string`  | `on`    | Value submitted when checked                 |
| `checked`      | `boolean` | `false` | Initial checked state                        |
| `disabled`     | `boolean` | `false` | Disables the checkbox                        |
| `required`     | `boolean` | `false` | Marks as required for validation             |
| `class`        | `string`  | -       | Additional CSS classes for the input         |
| `wrapper_class`| `string`  | -       | Additional CSS classes for the wrapper label |
| `attrs`        | `string`  | -       | Raw HTML attributes (data-*, aria-*, etc.)   |

## Accessibility

- Always provide a `label` or `aria-label` for screen readers
- Use semantic `<input type="checkbox">` for native browser support
- Checkboxes are keyboard accessible (Tab, Space)
- Disabled state prevents interaction
- Use `required` attribute for form validation
- Group related checkboxes with a heading or fieldset

## Form Integration

### Getting Checkbox Values

When a form is submitted, only checked checkboxes send their values:

```jinja
{# Single checkbox #}
<input type="checkbox" name="newsletter" value="yes" />
{# Submits: newsletter=yes (only if checked) #}

{# Multiple checkboxes with array notation #}
<input type="checkbox" name="interests[]" value="fashion" />
<input type="checkbox" name="interests[]" value="beauty" />
{# Submits: interests[]=fashion&interests[]=beauty (only checked ones) #}
```

## Customization

### Custom Label Styling

```jinja
<div class="flex items-center gap-2">
  {% with id='custom', name='custom', label='' %}
    {% include 'components/ui/checkbox.jinja' %}
  {% endwith %}
  <label for="custom" class="text-lg font-bold text-blue-600">
    Custom styled label
  </label>
</div>
```

## Source Code

[`components/ui/checkbox.jinja`](../../components/ui/checkbox.jinja)
