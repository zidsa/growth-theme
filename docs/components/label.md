# Label

A simple accessible label component for form controls.

## Overview

The Label component renders an accessible `<label>` element that can be associated with form controls. It supports required indicators and disabled styling via data attributes.

## Usage

```jinja
{% with for="email", content=_("Email address"), required=true %}
  {% include 'components/ui/label.jinja' %}
{% endwith %}
```

## Examples

### Basic

Simple label for a form field.

```jinja
{% with for="username", content=_("Username") %}
  {% include 'components/ui/label.jinja' %}
{% endwith %}
```

### Required Field

Label with required indicator (*).

```jinja
{% with for="email", content=_("Email"), required=true %}
  {% include 'components/ui/label.jinja' %}
{% endwith %}
```

### Disabled

Label with disabled styling (50% opacity).

```jinja
{% with for="field", content=_("Disabled Field"), disabled=true %}
  {% include 'components/ui/label.jinja' %}
{% endwith %}
```

### With Input

Combine with input component using a wrapper.

```jinja
<div class="grid w-full items-center gap-2">
  {% with for="email", content=_("Email"), required=true %}
    {% include 'components/ui/label.jinja' %}
  {% endwith %}
  {% with id="email", name="email", type="email", required=true, placeholder=_("Enter your email") %}
    {% include 'components/ui/input.jinja' %}
  {% endwith %}
</div>
```

## Real-World Examples

### Login Form

```jinja
<form method="post" action="/login" class="space-y-4">
  <div class="grid w-full items-center gap-2">
    {% with for="email", content=_("Email"), required=true %}
      {% include 'components/ui/label.jinja' %}
    {% endwith %}
    {% with id="email", name="email", type="email", required=true %}
      {% include 'components/ui/input.jinja' %}
    {% endwith %}
  </div>

  <div class="grid w-full items-center gap-2">
    {% with for="password", content=_("Password"), required=true %}
      {% include 'components/ui/label.jinja' %}
    {% endwith %}
    {% with id="password", name="password", type="password", required=true %}
      {% include 'components/ui/input.jinja' %}
    {% endwith %}
  </div>

  {% with content=_("Sign In"), variant="filled", type="submit" %}
    {% include 'components/ui/button.jinja' %}
  {% endwith %}
</form>
```

### File Upload

```jinja
<div class="grid w-full items-center gap-2">
  {% with for="avatar", content=_("Profile Picture") %}
    {% include 'components/ui/label.jinja' %}
  {% endwith %}
  {% with id="avatar", name="avatar", type="file" %}
    {% include 'components/ui/input.jinja' %}
  {% endwith %}
</div>
```

## API Reference

### Parameters

| Parameter  | Type      | Default | Description                                    |
|------------|-----------|---------|------------------------------------------------|
| `for`      | `string`  | -       | ID of the form element this label is for       |
| `content`  | `string`  | -       | Label text content                             |
| `required` | `boolean` | `false` | Shows required indicator (*)                   |
| `disabled` | `boolean` | `false` | Applies disabled styling (opacity)             |
| `class`    | `string`  | -       | Additional CSS classes                         |
| `attrs`    | `string`  | -       | Additional HTML attributes                     |

### Styling

The label uses these styles:
- Color: `text-secondary` (#545352)
- Font size: 16px
- Font variant: all-small-caps
- Disabled: 50% opacity via `data-[disabled=true]:opacity-50`

## Accessibility

- Uses semantic `<label>` element
- Associates with form control via `for` attribute
- Required indicator uses red asterisk for visual indication
- Disabled state is conveyed via `data-disabled` attribute

## Source Code

[`components/ui/label.jinja`](../../components/ui/label.jinja)
