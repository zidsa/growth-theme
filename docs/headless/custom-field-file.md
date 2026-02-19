# Custom Field - File/Image Upload

Renders a file or image upload custom input field.
Outputs raw HTML with BEM classes for complete styling freedom.

## Platform Integration

### Required Selectors

| Selector | Element | Purpose |
|----------|---------|---------|
| `#product-custom-user-input-fields` | `<div>` | Container ID (on wrapper) |
| `#{custom_field.id}` | `<input type="file">` | Hidden file input |
| `#file-delete-{id}` | `<span>` | Delete button (shown when file selected) |
| `#file-preview-{id}` | `<span>` | Image preview container |
| `#file-name-{id}` | `<span>` | Filename display |
| `#file-upload-{id}` | `<button>` | Upload trigger button |

### Event Handlers

| Handler | Element | Trigger |
|---------|---------|---------|
| `productOptionInputFileChanged(event, type)` | `<input type="file">` | Change |
| `productOptionInputFileDelete(event, type)` | Delete button | Click |

### Data Flow

```
1. User clicks upload button
2. Hidden file input is triggered
3. User selects file
4. productOptionInputFileChanged(event, 'file'|'image') triggered
5. Platform reads file from input
6. Platform shows preview (for images) and filename
7. Platform hides upload button, shows delete button
8. On add-to-cart, platform uploads file and includes reference
```

### Required Attributes

| Element | Attribute | Purpose |
|---------|-----------|---------|
| File `<input>` | `id` | Custom field ID |
| File `<input>` | `data-type` | `FILE` or `IMAGE` |
| File `<input>` | `accept` | Allowed file types |
| File `<input>` | `onchange` | Must call `productOptionInputFileChanged(event, type)` |
| Delete `<span>` | `id` | `file-delete-{custom_field.id}` |
| Delete `<span>` | `data-input-id` | References file input ID |
| Delete `<span>` | `onclick` | Must call `productOptionInputFileDelete(event, type)` |
| Preview `<span>` | `id` | `file-preview-{custom_field.id}` |
| Name `<span>` | `id` | `file-name-{custom_field.id}` |
| Name `<span>` | `data-hint-text` | Hint text to restore on delete |
| Upload `<button>` | `id` | `file-upload-{custom_field.id}` |

## HTML Output

```html
<div id="product-custom-user-input-fields" class="custom-field custom-field--file custom-field--image">
  <label class="custom-field__label">
    Upload Photo
    <span class="custom-field__price">(+$5.00)</span>
    <span class="custom-field__required">*</span>
  </label>

  <!-- Hidden file input -->
  <input
    type="file"
    id="field-201"
    name="Upload Photo"
    data-type="IMAGE"
    title="Upload Photo"
    lang="en"
    accept="image/png, image/jpg, image/jpeg, image/gif"
    onchange="productOptionInputFileChanged(event, 'image')"
    style="display: none"
    class="file-upload__input"
    required
  />

  <!-- Custom upload UI -->
  <div class="file-upload">
    <!-- Delete button (hidden by default) -->
    <span
      id="file-delete-field-201"
      data-input-id="field-201"
      onclick="productOptionInputFileDelete(event, 'image')"
      style="display: none"
      class="file-upload__delete"
    >
      <svg class="file-upload__delete-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M18 6L6 18"></path>
        <path d="M6 6l12 12"></path>
      </svg>
    </span>

    <!-- Image preview (hidden by default) -->
    <span
      id="file-preview-field-201"
      style="display: none"
      class="file-upload__preview"
    >
      <img width="24px" height="24px" class="file-upload__preview-image" alt="Preview" />
    </span>

    <!-- Filename display -->
    <span
      id="file-name-field-201"
      data-hint-text="PNG, JPG up to 5MB"
      class="file-upload__name"
    >
      PNG, JPG up to 5MB
    </span>

    <!-- Upload button -->
    <button
      id="file-upload-field-201"
      type="button"
      onclick="document.getElementById('field-201').click()"
      class="file-upload__button"
    >
      Choose File
    </button>
  </div>
</div>
```

## BEM Classes

### Block

| Class | Element | Description |
|-------|---------|-------------|
| `.custom-field` | `<div>` | Main container |
| `.file-upload` | `<div>` | Upload UI container |

### Modifiers

| Class | Description |
|-------|-------------|
| `.custom-field--file` | File upload type |
| `.custom-field--image` | Image upload type |

### Elements

| Class | Element | Description |
|-------|---------|-------------|
| `.custom-field__label` | `<label>` | Field label |
| `.custom-field__price` | `<span>` | Additional price indicator |
| `.custom-field__required` | `<span>` | Required field marker |
| `.file-upload__input` | `<input>` | Hidden file input |
| `.file-upload__delete` | `<span>` | Delete button container |
| `.file-upload__delete-icon` | `<svg>` | Delete icon |
| `.file-upload__preview` | `<span>` | Image preview container |
| `.file-upload__preview-image` | `<img>` | Preview image |
| `.file-upload__name` | `<span>` | Filename/hint display |
| `.file-upload__button` | `<button>` | Upload trigger button |

## Styling Guide

All styles must be applied via CSS. No default styles are included.

### Basic Example

```css
/* Container */
.custom-field--file,
.custom-field--image {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Label */
.custom-field__label {
  font-weight: 500;
  color: var(--foreground);
}

/* Upload container */
.file-upload {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  background-color: var(--foreground);
}

/* Delete button */
.file-upload__delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: var(--destructive);
  color: white;
  cursor: pointer;
}

.file-upload__delete:hover {
  opacity: 0.8;
}

/* Preview */
.file-upload__preview {
  display: flex;
  align-items: center;
}

.file-upload__preview-image {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
}

/* Filename */
.file-upload__name {
  flex: 1;
  color: var(--secondary);
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Upload button */
.file-upload__button {
  padding: 0.5rem 1rem;
  border: 1px solid var(--primary);
  border-radius: var(--radius);
  background-color: transparent;
  color: var(--primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.file-upload__button:hover {
  background-color: var(--primary);
  color: var(--primary-foreground);
}
```

### Tailwind Example

```html
<style>
.custom-field--file, .custom-field--image { @apply flex flex-col gap-2; }
.custom-field__label { @apply text-sm font-medium text-foreground; }
.file-upload { @apply flex items-center gap-3 p-4 border-2 border-dashed border-border rounded bg-foreground/5; }
.file-upload__delete { @apply flex items-center justify-center w-6 h-6 rounded-full bg-destructive text-white cursor-pointer hover:opacity-80; }
.file-upload__preview-image { @apply w-10 h-10 object-cover rounded; }
.file-upload__name { @apply flex-1 text-sm text-secondary truncate; }
.file-upload__button { @apply px-4 py-2 border border-primary rounded bg-transparent text-primary text-sm cursor-pointer hover:bg-primary hover:text-primary-foreground transition-all; }
</style>
```

## Accepted File Types

### Image Type

```
image/png, image/jpg, image/jpeg, image/gif
```

### File Type

```
zip, image/png, image/jpg, image/jpeg, image/gif,
application/zip, application/x-zip, application/x-zip-compressed,
application/x-rar-compressed, application/octet-stream,
zz-application/zz-winassoc-psd, application/x-photoshop,
application/psd, application/photoshop, application/x-rar,
application/vnd.rar,
application/vnd.openxmlformats-officedocument.wordprocessingml.document,
application/vnd.ms-excel, text/plain, application/msword,
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,
text/csv, application/csv, application/vnd.ms-powerpoint,
application/pdf, application/rtf, application/txt, application/odf
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `custom_field` | object | Yes | Field object with `id`, `label`, `type`, `is_required`, `hint`, `price` |

### Custom Field Object

```javascript
{
  id: "field-201",
  label: "Upload Photo",
  type: "IMAGE",     // IMAGE | FILE
  is_required: true,
  hint: "PNG, JPG up to 5MB",
  price: 5.00,
  formatted_price: "$5.00"
}
```

## Usage

```jinja
{% with custom_field=field %}
  {% include 'components/products/headless/fields/custom-field-file.jinja' %}
{% endwith %}
```

## File Location

```
components/products/headless/fields/custom-field-file.jinja
```
