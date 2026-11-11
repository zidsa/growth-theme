/**
 * URL-building properties of js/features/product-filter.js.
 *
 * Imports the REAL module file (no bundler, no copy) with the few globals it
 * touches at import time stubbed, then drives its URL logic through the same
 * entry points the filter UI calls.
 *
 * Run: node url_builder.mjs [--root DIR]
 * Prints one `PROP <id> PASS|FAIL` line per property.
 */

import { pathToFileURL } from "node:url";
import path from "node:path";

const args = process.argv.slice(2);
const rootIdx = args.indexOf("--root");
const ROOT = path.resolve(
  rootIdx >= 0 ? args[rootIdx + 1] : path.join(import.meta.dirname, "../../../..")
);

// ── the globals the module touches at import time ──────────────────────────
let href = "https://shop.test/products";
globalThis.window = {
  get location() {
    return {
      get href() {
        return href;
      },
      set href(v) {
        href = v;
      },
    };
  },
  addEventListener() {},
  dispatchEvent() {},
};
globalThis.document = {
  readyState: "complete",
  addEventListener() {},
  querySelector: () => null,
  createElement: () => ({ setAttribute() {}, appendChild() {}, style: {} }),
};
globalThis.history = {
  pushState(_state, _title, url) {
    href = new URL(url, href).toString();
  },
};
globalThis.CustomEvent = class {};

const mod = await import(
  pathToFileURL(path.join(ROOT, "assets/js/features/product-filter.js")).href
);
const ProductFilter = mod.default;

const failures = [];
const check = (id, cond, detail) => {
  if (!cond) failures.push({ id, detail });
};

function instance(url) {
  href = url;
  const pf = new ProductFilter();
  pf.fetchProducts = async () => {}; // rendering is covered elsewhere
  return pf;
}

/** Ordered [key, value] pairs of a URL's query. */
const pairs = (url) => [...new URL(url, "https://shop.test").searchParams.entries()];
const asSet = (url) => pairs(url).map(([k, v]) => `${k}=${v}`).sort();

// ── property 1: every query the collector hands back survives a rebuild ─────
// Keys are the ones the filter UI can produce (attribute slugs come from the
// merchant's attribute names, so they carry Arabic and brackets); values are
// whatever a shopper or the API can put in them.
const KEYS = [
  "attributes[ar-اللون-en-2][]",
  "attributes[ar-الماركة-en-brand][]",
  "availability",
  "from_price",
  "to_price",
  "q",
  "page",
  "page_size",
  "sort_by",
  "order",
];
const VALUES = [
  "",
  "0",
  "100",
  "ابيض",
  "a b",
  "x&y=z",
  "#frag",
  "100%",
  'say "hi"',
  "<script>",
  "a+b",
  "üñî",
  "1,000",
];

let seed = 20261111 >>> 0;
const rand = () => {
  seed = (seed * 1664525 + 1013904223) >>> 0;
  return seed / 2 ** 32;
};

let cases = 0;
for (let n = 0; n < 300; n++) {
  const params = new URLSearchParams();
  const count = 1 + Math.floor(rand() * 4);
  for (let i = 0; i < count; i++) {
    params.append(KEYS[Math.floor(rand() * KEYS.length)], VALUES[Math.floor(rand() * VALUES.length)]);
  }
  const before = new URL("https://shop.test/products?" + params.toString());
  const pf = instance(before.toString());
  const rebuilt = "https://shop.test" + pf.buildCleanUrl(before);
  cases++;
  check(
    "filter-url-roundtrip",
    JSON.stringify(pairs(before.toString())) === JSON.stringify(pairs(rebuilt)),
    `${before.search} rebuilt as ${new URL(rebuilt).search}`
  );
}
check("filter-url-roundtrip", cases === 300, `ran ${cases} cases, wanted 300`);

// ── property 2: removing one filter touches only that filter ────────────────
const base =
  "https://shop.test/brands/acme?q=lamps&page=3&page_size=12&sort_by=price&order=desc" +
  "&attributes[ar-اللون-en-2][]=ابيض&attributes[ar-اللون-en-2][]=أسود" +
  "&attributes[ar-الماركة-en-brand][]=جري&availability=in_stock&from_price=10&to_price=90";

const without = (pairsIn, drop) => pairsIn.filter(([k, v]) => !drop(k, v));

for (const [type, slug, value] of [
  ["sort", "", ""],
  ["attribute", "ar-اللون-en-2", "ابيض"],
  ["attribute", "ar-اللون-en-2", "أسود"],
  ["availability", "", "in_stock"],
  ["price", "", ""],
]) {
  const pf = instance(base);
  pf.removeFilter(type, slug, value);
  const drop =
    type === "sort"
      ? (k) => k === "sort_by" || k === "order"
      : type === "price"
        ? (k) => k === "from_price" || k === "to_price"
        : type === "availability"
          ? (k, v) => k === "availability" && v === value
          : (k, v) => k === `attributes[${slug}][]` && v === value;
  const want = asSet("https://shop.test/x?" + "");
  const expected = without(pairs(base), drop)
    .filter(([k]) => k !== "page")
    .map(([k, v]) => `${k}=${v}`)
    .sort();
  check(
    "filter-remove-semantics",
    JSON.stringify(asSet(href)) === JSON.stringify(expected),
    `removeFilter(${type}${slug ? ", " + slug : ""}${value ? ", " + value : ""}): got ${new URL(href).search}, want ${expected.join("&")}`
  );
  void want;
}

// a value that is not there changes nothing but paging
{
  const pf = instance(base);
  pf.removeFilter("attribute", "ar-اللون-en-2", "غير-موجود");
  const expected = pairs(base)
    .filter(([k]) => k !== "page")
    .map(([k, v]) => `${k}=${v}`)
    .sort();
  check(
    "filter-remove-semantics",
    JSON.stringify(asSet(href)) === JSON.stringify(expected),
    `removeFilter of an absent value changed the query: ${href}`
  );
}

// clearFilters keeps exactly the keys it is told to keep
{
  const pf = instance(base);
  await pf.clearFilters(["sort_by", "order", "page_size", "q"]);
  const kept = pairs(href).map(([k]) => k).sort();
  check(
    "filter-remove-semantics",
    JSON.stringify(kept) === JSON.stringify(["order", "page_size", "q", "sort_by"]),
    `clearFilters kept ${kept}`
  );
}

// ── report ──────────────────────────────────────────────────────────────────
for (const id of ["filter-url-roundtrip", "filter-remove-semantics"]) {
  const mine = failures.filter((f) => f.id === id);
  console.log(`PROP ${id} ${mine.length ? "FAIL" : "PASS"}`);
  for (const f of mine.slice(0, 5)) console.log(`  - ${f.detail}`);
}
process.exit(0);
