# Disclosure

A collapsible content component for showing and hiding information - ideal for accordions, FAQ sections, and expandable details.

## Overview

The Disclosure component provides a clean, accessible way to toggle content visibility. It uses pure CSS with checkbox/radio inputs and the Tailwind `peer` selector for smooth animations. Supports both multiple-open mode (checkboxes) and accordion mode (radios).

## Usage

```jinja
{%
  with
  id='my-disclosure',
  title='Click to expand',
  content='This is the hidden content that will be revealed.'
%}
  {% include 'components/ui/disclosure.jinja' %}
{% endwith %}
```

## Examples

### Basic Disclosure

Simple disclosure with title and content.

```jinja
{%
  with
  id='basic-disclosure',
  title='What is your return policy?',
  content='You can return items within 30 days of purchase for a full refund. Items must be in original condition with tags attached.'
%}
  {% include 'components/ui/disclosure.jinja' %}
{% endwith %}
```

### Initially Open

Disclosure that starts in the open state.

```jinja
{%
  with
  id='open-disclosure',
  title='Already expanded',
  content='This content is visible by default.',
  open=true
%}
  {% include 'components/ui/disclosure.jinja' %}
{% endwith %}
```

### With HTML Content

Disclosure containing rich HTML markup.

```jinja
{% set my_content %}
  <div class="space-y-3">
    <p class="font-medium">Shipping Information:</p>
    <ul class="list-inside list-disc space-y-1 text-sm">
      <li>Free shipping on orders over 200 SAR</li>
      <li>Standard delivery: 5-7 business days</li>
      <li>Express delivery: 2-3 business days</li>
    </ul>
    <p class="text-primary mt-3 text-sm font-semibold">Track your order after purchase</p>
  </div>
{% endset %}

{%
  with
  id='html-disclosure',
  title='Shipping & Delivery Options',
  content=my_content
%}
  {% include 'components/ui/disclosure.jinja' %}
{% endwith %}
```

### Multiple Open (Default)

Multiple disclosures can be open at the same time using checkboxes.

```jinja
<div class="space-y-2">
  {%
    with
    id='info-1',
    title='Shipping Information',
    content='Free shipping on orders over 200 SAR. Standard delivery takes 5-7 business days.',
    multi=true
  %}
    {% include 'components/ui/disclosure.jinja' %}
  {% endwith %}

  {%
    with
    id='info-2',
    title='Return Policy',
    content='You can return items within 30 days of purchase for a full refund.',
    multi=true
  %}
    {% include 'components/ui/disclosure.jinja' %}
  {% endwith %}

  {%
    with
    id='info-3',
    title='Payment Methods',
    content='We accept Visa, Mastercard, Mada, Apple Pay, and cash on delivery.',
    multi=true
  %}
    {% include 'components/ui/disclosure.jinja' %}
  {% endwith %}
</div>
```

### Accordion Mode (Only One Open)

Only one disclosure can be open at a time using radio buttons.

```jinja
<div class="space-y-2">
  {# Set shared accordion settings once #}
  {% set multi = false %}
  {% set group = 'faq-accordion' %}

  {%
    with
    id='faq-1',
    title='What is your return policy?',
    content='You can return items within 30 days of purchase for a full refund.',
    open=true
  %}
    {% include 'components/ui/disclosure.jinja' %}
  {% endwith %}

  {%
    with
    id='faq-2',
    title='Do you ship internationally?',
    content='Yes, we ship to over 100 countries worldwide.'
  %}
    {% include 'components/ui/disclosure.jinja' %}
  {% endwith %}

  {%
    with
    id='faq-3',
    title='How long does shipping take?',
    content='Standard shipping takes 5-7 business days.'
  %}
    {% include 'components/ui/disclosure.jinja' %}
  {% endwith %}
</div>
```

## Real-World Examples

### FAQ Section

```jinja
<section class="mx-auto max-w-3xl px-4 py-16">
  <h2 class="mb-8 text-3xl font-bold">{{ _("Frequently Asked Questions") }}</h2>

  <div class="space-y-2">
    {%
      set faqs = [
        {
          'question': _('What is your return policy?'),
          'answer': _('You can return items within 30 days of purchase for a full refund. Items must be in original condition with tags attached.')
        },
        {
          'question': _('Do you ship internationally?'),
          'answer': _('Yes, we ship to over 100 countries worldwide. International shipping rates vary by destination.')
        },
        {
          'question': _('How can I track my order?'),
          'answer': _('Once your order ships, you will receive a tracking number via email. Use this number on our tracking page.')
        },
        {
          'question': _('What payment methods do you accept?'),
          'answer': _('We accept Visa, Mastercard, Mada, Apple Pay, and cash on delivery.')
        }
      ]
    %}

    {% for faq in faqs %}
      {%
        with
        id='faq-' ~ loop.index,
        title=faq.question,
        content=faq.answer
      %}
        {% include 'components/ui/disclosure.jinja' %}
      {% endwith %}
    {% endfor %}
  </div>
</section>
```

### Product Details Accordion

```jinja
<div class="space-y-3">
  {% set multi = false %}
  {% set group = 'product-details' %}

  {# Description #}
  {% set description_content %}
    <div class="prose prose-sm max-w-none">
      {{ product.description | safe }}
    </div>
  {% endset %}

  {%
    with
    id='product-description',
    title=_('Description'),
    content=description_content,
    open=true
  %}
    {% include 'components/ui/disclosure.jinja' %}
  {% endwith %}

  {# Specifications #}
  {% if product.metafields %}
    {% set specs_content %}
      <dl class="space-y-2">
        {% for field in product.metafields %}
          <div class="flex justify-between">
            <dt class="font-medium">{{ field.key }}</dt>
            <dd class="text-secondary">{{ field.value }}</dd>
          </div>
        {% endfor %}
      </dl>
    {% endset %}

    {%
      with
      id='product-specs',
      title=_('Specifications'),
      content=specs_content
    %}
      {% include 'components/ui/disclosure.jinja' %}
    {% endwith %}
  {% endif %}

  {# Shipping Info #}
  {% set shipping_content %}
    <div class="space-y-2 text-sm">
      <p>{{ _('Free shipping on orders over') }} {{ store.settings.checkout.free_shipping_minimum_amount }} {{ session.currency }}</p>
      <p class="text-secondary">{{ _('Estimated delivery: 5-7 business days') }}</p>
      <p class="text-secondary">{{ _('Express delivery available at checkout') }}</p>
    </div>
  {% endset %}

  {%
    with
    id='shipping-info',
    title=_('Shipping & Returns'),
    content=shipping_content
  %}
    {% include 'components/ui/disclosure.jinja' %}
  {% endwith %}
</div>
```

### Filter Panel

```jinja
<aside class="w-64 space-y-3">
  {% set filters_content %}
    <form class="space-y-3">
      <label class="flex items-center gap-2">
        <input type="checkbox" class="rounded" name="in_stock" />
        <span class="text-sm">{{ _("In Stock Only") }}</span>
      </label>
      <label class="flex items-center gap-2">
        <input type="checkbox" class="rounded" name="on_sale" />
        <span class="text-sm">{{ _("On Sale") }}</span>
      </label>
      <label class="flex items-center gap-2">
        <input type="checkbox" class="rounded" name="new_arrivals" />
        <span class="text-sm">{{ _("New Arrivals") }}</span>
      </label>
      <button type="submit" class="text-primary text-sm font-medium hover:underline">
        {{ _("Apply Filters") }}
      </button>
    </form>
  {% endset %}

  {%
    with
    id='product-filters',
    title=_('Filters'),
    content=filters_content,
    open=true
  %}
    {% include 'components/ui/disclosure.jinja' %}
  {% endwith %}

  {% set price_content %}
    <div class="space-y-3">
      <input type="range" min="0" max="1000" class="w-full" />
      <div class="flex justify-between text-sm">
        <span>0 SAR</span>
        <span>1000 SAR</span>
      </div>
    </div>
  {% endset %}

  {%
    with
    id='price-filter',
    title=_('Price Range'),
    content=price_content,
    open=true
  %}
    {% include 'components/ui/disclosure.jinja' %}
  {% endwith %}
</aside>
```

## API Reference

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` | `string` | Random | Unique identifier for the disclosure |
| `title` | `string` | Required | Button title text |
| `content` | `string/HTML` | Required | Content to show/hide (use `{% set %}` for HTML) |
| `open` | `boolean` | `false` | Whether disclosure is initially open |
| `multi` | `boolean` | `true` | Allow multiple disclosures open (checkbox) or only one (radio) |
| `group` | `string` | Required when `multi=false` | Group name for radio buttons to link disclosures |
| `class` | `string` | - | Additional CSS classes for container wrapper |
| `button_class` | `string` | - | Additional CSS classes for button/trigger |
| `content_class` | `string` | - | Additional CSS classes for content wrapper |

## Customization

### Custom Button Styling

Use `button_class` to customize the trigger button.

```jinja
{%
  with
  id='custom-button',
  title='Custom Styled Button',
  content='This disclosure has a custom styled button.',
  button_class='rounded-lg bg-blue-500 px-6 py-3 text-white hover:bg-blue-600'
%}
  {% include 'components/ui/disclosure.jinja' %}
{% endwith %}
```

### Custom Content Styling

Use `content_class` to style the content area.

```jinja
{%
  with
  id='custom-content',
  title='Custom Content Styling',
  content='This content has custom padding and background.',
  content_class='bg-gray-50 text-lg'
%}
  {% include 'components/ui/disclosure.jinja' %}
{% endwith %}
```

### Container Wrapper

Use `class` to style the entire disclosure wrapper.

```jinja
{%
  with
  id='custom-wrapper',
  title='Custom Wrapper',
  content='This entire disclosure has custom styling.',
  class='border-2 border-blue-300 rounded-lg shadow-md'
%}
  {% include 'components/ui/disclosure.jinja' %}
{% endwith %}
```

### Bordered Disclosure

```jinja
{%
  with
  id='bordered',
  title='Bordered Disclosure',
  content='This disclosure has a border around the entire component.',
  class='border border-gray-200 rounded-lg',
  button_class='rounded-t-lg bg-white px-4 py-3 hover:bg-gray-50',
  content_class='border-t border-gray-200 bg-white px-4 py-3'
%}
  {% include 'components/ui/disclosure.jinja' %}
{% endwith %}
```

### Colored Disclosure

```jinja
{%
  with
  id='colored',
  title='Success Message',
  content='Your order has been successfully placed! You will receive a confirmation email shortly.',
  button_class='rounded bg-green-100 px-4 py-2 text-green-900 hover:bg-green-200',
  content_class='bg-green-50 px-4 py-3 text-green-800'
%}
  {% include 'components/ui/disclosure.jinja' %}
{% endwith %}
```

## Source Code

[`components/ui/disclosure.jinja`](../../components/ui/disclosure.jinja)
