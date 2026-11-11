"""Apply one realistic edit per property to a scratch copy, to prove check.sh can flip.

Usage: python3 make_break.py <copy-root>
Every edit is the kind a person would actually make (a copy-paste slip, a dropped
guard, a "cleaner" one-liner). Nothing here touches the worktree.
"""

import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
edits = 0


def edit(rel, old, new, count=1):
    global edits
    p = ROOT / rel
    s = p.read_text()
    if old not in s:
        sys.exit(f"break: {rel}: pattern not found:\n{old}")
    p.write_text(s.replace(old, new, count))
    edits += 1


# cards-own-record: the logo guard becomes a truthiness check on the object,
# so a brand without a logo renders an <img> with an empty src
edit("components/brands/brand-card.jinja",
     "{% if brand.logo %}", "{% if brand %}")

# cards-escape: put the escaping back into the four card/hero components
edit("components/categories/category-card.jinja",
     'alt="{{ category.name }}"', 'alt="{{ category.name | e }}"')
edit("components/categories/category-card.jinja",
     "slug=category.slug)", "slug=category.slug | e)")
edit("components/categories/subcategory-card.jinja",
     'alt="{{ subcategory.name }}"', 'alt="{{ subcategory.name | e }}"')
edit("components/brands/brand-card.jinja",
     'alt="{{ brand.display_name or brand.name }}"',
     'alt="{{ (brand.display_name or brand.name) | e }}"')
edit("components/categories/category-hero.jinja",
     'alt="{{ title }}"', 'alt="{{ title | e }}"')
edit("components/brands/product-brand.jinja",
     'aria-label="{{ product.brand.display_name or product.brand.name }}"',
     'aria-label="{{ (product.brand.display_name or product.brand.name) | e }}"')
edit("components/brands/product-brand.jinja",
     'alt="{{ product.brand.display_name or product.brand.name }}"',
     'alt="{{ (product.brand.display_name or product.brand.name) | e }}"')

# hero-h1-image: drop the guard, so every hero prints an h1
edit("components/categories/category-hero.jinja",
     "{% if title %}\n        <h1", "<h1")
edit("components/categories/category-hero.jinja",
     "</h1>\n      {% endif %}", "</h1>")

# carousel-scope: one hardcoded id for the root, so two carousels collide
edit("components/categories/subcategories-carousel.jinja",
     '    data-subcategories-carousel="{{ carousel_id }}"',
     '    data-subcategories-carousel="subcategories-embla"')

# listing-grid: `if products.results` becomes a truthiness check on the object,
# so the empty state never renders
edit("templates/products.jinja", "{% if products.results %}", "{% if products %}")

# filter-recovery: the products header is no longer gated on results
for tpl in ("templates/brand.jinja", "templates/category.jinja"):
    edit(tpl,
         "{% if products and products.results %}\n          {% include 'components/products/products-header.jinja' %}\n        {% endif %}",
         "{% include 'components/products/products-header.jinja' %}")

# search-escape: escape quotes as well (the four-line fix for the finding)
edit("assets/js/features/search.js",
     """  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }""",
     """  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }""")

# price-slider-order: order the initial pair and stop treating 0 as "unset"
edit("assets/js/features/price-slider.js",
     """    const startMin = Math.min(Math.max(realMinValue || MIN, MIN), MAX);
    const startMax = Math.min(Math.max(realMaxValue || MAX, MIN), MAX);""",
     """    const lo = Math.min(realMinValue ?? MIN, realMaxValue ?? MAX);
    const hi = Math.max(realMinValue ?? MIN, realMaxValue ?? MAX);
    const startMin = Math.min(Math.max(lo, MIN), MAX);
    const startMax = Math.min(Math.max(hi, MIN), MAX);""")

# filter-form-url: an emptied price box clears the filter instead of being skipped
edit("assets/js/features/product-filter.js",
     """    for (let [key, value] of formData.entries()) {
      if (value === "" || value === null || key === "sort_option") continue;

      if (key === "from_price" || key === "to_price") {
        value = value.replace(/,/g, "");
      }
""",
     """    for (let [key, value] of formData.entries()) {
      if (key === "sort_option") continue;

      if (key === "from_price" || key === "to_price") {
        params[key] = value === "" ? null : value.replace(/,/g, "");
        continue;
      }
      if (value === "" || value === null) continue;
""")

# filter-url-roundtrip: build the query by hand ("encodeURIComponent is noisy")
edit("assets/js/features/product-filter.js",
     "params.push(`${key}=${encodeURIComponent(value)}`);",
     "params.push(`${key}=${value}`);")

# filter-remove-semantics: dropping one value drops the whole attribute
edit("assets/js/features/product-filter.js",
     """      const values = url.searchParams.getAll(key);
      url.searchParams.delete(key);
      values.forEach((v) => {
        if (v !== value) url.searchParams.append(key, v);
      });""",
     """      url.searchParams.delete(key);""")

print(f"applied {edits} edits to {ROOT}")
